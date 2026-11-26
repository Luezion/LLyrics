"""LLyrics — overlay de letras sincronizadas para jogar (Windows).

Atalhos padrão (dá para trocar nas configurações):
  Ctrl+Shift+L  mostra/esconde o overlay
  Ctrl+Shift+K  modo mover (arraste a letra e o widget)
  Ctrl+Shift+O  abre as configurações
"""
import os
import sys

from PySide6.QtCore import QLockFile, QRectF, Qt, QTimer
from PySide6.QtGui import QAction, QColor, QFont, QIcon, QLinearGradient, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon

import hotkeys
import i18n
import render
import winutil
from i18n import tr
from config import CONFIG_FILE, Config, data_dir, resource_path
from overlay import Controller
from settings_ui import SettingsWindow
from updater import Updater
from version import __version__


def make_icon():
    path = resource_path("icon.png")
    if os.path.exists(path):
        return QIcon(path)
    pm = QPixmap(64, 64)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    g = QLinearGradient(0, 0, 64, 64)
    g.setColorAt(0, QColor("#C4B3FF"))
    g.setColorAt(1, QColor("#E38CF2"))
    p.setBrush(g)
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(QRectF(2, 2, 60, 60), 16, 16)
    f = QFont("Segoe UI Symbol")
    f.setPixelSize(40)
    p.setFont(f)
    p.setPen(QColor("#141419"))
    p.drawText(pm.rect(), Qt.AlignCenter, "♪")
    p.end()
    return QIcon(pm)


def main():
    if sys.platform == "win32":
        try:  # nitidez em telas com escala
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:  # noqa: BLE001
            pass
    first_run = not os.path.exists(CONFIG_FILE)
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("LLyrics")
    cfg = Config()
    i18n.set_lang(cfg.get("language", "en"))

    lock = QLockFile(os.path.join(data_dir(), "app.lock"))
    if not lock.tryLock(100):
        QMessageBox.information(None, "LLyrics", tr("msg.already_running"))
        return 0

    render.load_fonts()
    if cfg.get("autostart"):
        winutil.set_autostart(True)  # mantém o caminho certo se a pasta mudou
    ctl = Controller(cfg)
    icon = make_icon()
    app.setWindowIcon(icon)
    state = {"settings": None}

    def open_settings(page=None):
        win = state["settings"]
        if win is None:
            win = state["settings"] = SettingsWindow(ctl)
            win.setWindowIcon(icon)
        if page is not None:
            win.nav.setCurrentRow(page)
        win.show()
        win.raise_()
        win.activateWindow()

    # bandeja
    tray = QSystemTrayIcon(icon)
    tray.setToolTip(f"LLyrics {__version__}")
    menu = QMenu()
    act_toggle = QAction()
    act_toggle.triggered.connect(ctl.toggle_hidden)
    act_move = QAction()
    act_move.triggered.connect(ctl.toggle_edit)
    act_settings = QAction()
    act_settings.triggered.connect(lambda: open_settings())
    act_update = QAction()
    act_autostyle = QAction()
    act_autostyle.triggered.connect(lambda: ctl.generate_style(permanent=True))
    act_quit = QAction()
    for a in (act_toggle, act_move, act_settings, act_autostyle, act_update):
        menu.addAction(a)
    menu.addSeparator()
    menu.addAction(act_quit)
    tray.setContextMenu(menu)
    tray.activated.connect(lambda r: open_settings() if r in (QSystemTrayIcon.Trigger,
                                                               QSystemTrayIcon.DoubleClick) else None)

    def update_texts():
        act_toggle.setText(f"{tr('tray.toggle')}  ({cfg['hotkey_toggle']})")
        act_move.setText(f"{tr('tray.move')}  ({cfg['hotkey_move']})")
        act_settings.setText(f"{tr('tray.settings')}  ({cfg['hotkey_settings']})")
        act_update.setText(tr("tray.update"))
        act_autostyle.setText(tr("tray.autostyle"))
        act_quit.setText(tr("tray.quit"))

    update_texts()
    tray.show()

    def notify(msg, ms=5000):
        tray.showMessage("LLyrics", msg, icon, ms)

    # atualizações automáticas
    def quit_now():
        QTimer.singleShot(0, app.quit)
        QTimer.singleShot(4000, lambda: os._exit(0))  # garantia, se algo travar no fechamento

    act_quit.triggered.connect(quit_now)
    updater = Updater(cfg, quit_now, notify)
    ctl.updater = updater
    act_update.triggered.connect(lambda: updater.check(manual=True))
    QTimer.singleShot(5000, updater.check)
    update_timer = QTimer()
    update_timer.timeout.connect(updater.check)
    update_timer.start(6 * 60 * 60 * 1000)

    # atalhos globais (configuráveis)
    hk = winutil.HotkeyFilter()
    app.installNativeEventFilter(hk)
    actions = (("hotkey_toggle", ctl.toggle_hidden), ("hotkey_move", ctl.toggle_edit),
               ("hotkey_settings", lambda: open_settings()))

    def register_hotkeys():
        hk.unregister_all()
        failed = []
        for key, cb in actions:
            parsed = hotkeys.parse(cfg.get(key, ""))
            if not parsed or not hk.register(parsed[0], parsed[1], cb):
                failed.append(key)
        update_texts()
        return failed

    ctl.register_hotkeys = register_hotkeys

    def style_generated(summary, permanent):
        win = state["settings"]
        if win is not None:
            win.style_generated(summary, permanent)
        if summary is None:
            notify(tr("autostyle.need_song"), 3000)
        elif permanent and (win is None or not win.isVisible()):
            notify(tr("autostyle.done", summary=i18n.style_summary(summary)), 4000)

    ctl.on_style_generated = style_generated
    ctl.suspend_hotkeys = hk.unregister_all
    failed = register_hotkeys()
    if failed and sys.platform == "win32":
        notify(tr("msg.hotkey_failed", keys=", ".join(cfg[k] for k in failed)))

    # trocar o idioma: refaz a janela de configurações e os textos
    def language_changed():
        i18n.set_lang(cfg.get("language", "en"))
        update_texts()
        ctl.apply_config()
        old = state["settings"]
        if old is not None:
            page = old.nav.currentRow()
            geo = old.geometry()
            was_visible = old.isVisible()
            old.closing_for_rebuild = True
            old.close()
            old.deleteLater()
            state["settings"] = None
            if was_visible:
                open_settings(page)
                state["settings"].setGeometry(geo)

    ctl.language_changed = lambda: QTimer.singleShot(0, language_changed)

    # leitura do player
    watcher = None
    if sys.platform == "win32":
        from media import MediaWatcher
        watcher = MediaWatcher(ctl.on_media_thread)
        watcher.start()
    else:
        print("Aviso: a leitura do player só funciona no Windows. Abrindo em modo prévia.")
        ctl.demo = True

    if first_run:
        open_settings()
        notify(tr("msg.first_run"), 6000)

    def cleanup():
        hk.unregister_all()
        if watcher:
            watcher.stop()
        cfg.save()
        ctl.shutdown()
        tray.hide()

    app.aboutToQuit.connect(cleanup)
    code = app.exec()
    lock.unlock()
    # sai na hora: a thread que lê o player (WinRT) às vezes segura o processo aberto,
    # e o atualizador precisa que o app feche de verdade para trocar os arquivos
    sys.stdout and sys.stdout.flush()
    os._exit(code)


if __name__ == "__main__":
    sys.exit(main())
