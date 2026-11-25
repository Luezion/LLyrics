"""LLyrics — overlay de letras sincronizadas para jogar (Windows).

Atalhos:
  Ctrl+Shift+L  mostra/esconde o overlay
  Ctrl+Shift+K  modo mover (arraste a letra e o widget)
  Ctrl+Shift+O  abre as configurações
"""
import os
import sys

from PySide6.QtCore import QLockFile, QRectF, Qt, QTimer
from PySide6.QtGui import QAction, QColor, QFont, QIcon, QLinearGradient, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon

import render
import winutil
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

    lock = QLockFile(os.path.join(data_dir(), "app.lock"))
    if not lock.tryLock(100):
        QMessageBox.information(None, "LLyrics",
                                "O app já está aberto. Procure o ícone ♪ perto do relógio.")
        return 0

    render.load_fonts()
    cfg = Config()
    if cfg.get("autostart"):
        winutil.set_autostart(True)  # mantém o caminho certo se a pasta mudou
    ctl = Controller(cfg)
    settings = SettingsWindow(ctl)
    icon = make_icon()
    app.setWindowIcon(icon)
    settings.setWindowIcon(icon)

    def open_settings():
        settings.show()
        settings.raise_()
        settings.activateWindow()

    # bandeja
    tray = QSystemTrayIcon(icon)
    tray.setToolTip(f"LLyrics {__version__}")
    menu = QMenu()
    act_toggle = QAction("Mostrar/esconder  (Ctrl+Shift+L)")
    act_toggle.triggered.connect(ctl.toggle_hidden)
    act_move = QAction("Mover janelas  (Ctrl+Shift+K)")
    act_move.triggered.connect(ctl.toggle_edit)
    act_settings = QAction("Configurações…  (Ctrl+Shift+O)")
    act_settings.triggered.connect(open_settings)
    act_update = QAction("Procurar atualizações")
    act_quit = QAction("Sair")
    act_quit.triggered.connect(app.quit)
    for a in (act_toggle, act_move, act_settings, act_update):
        menu.addAction(a)
    menu.addSeparator()
    menu.addAction(act_quit)
    tray.setContextMenu(menu)
    tray.activated.connect(lambda r: open_settings() if r in (QSystemTrayIcon.Trigger,
                                                               QSystemTrayIcon.DoubleClick) else None)
    tray.show()

    # atualizações automáticas
    def quit_now():
        QTimer.singleShot(0, app.quit)
        QTimer.singleShot(4000, lambda: os._exit(0))  # garantia, se algo travar no fechamento

    act_quit.triggered.disconnect()
    act_quit.triggered.connect(quit_now)
    updater = Updater(cfg, quit_now, lambda msg: tray.showMessage("LLyrics", msg, icon, 5000))
    ctl.updater = updater
    act_update.triggered.connect(lambda: updater.check(manual=True))
    QTimer.singleShot(5000, updater.check)
    update_timer = QTimer()
    update_timer.timeout.connect(updater.check)
    update_timer.start(6 * 60 * 60 * 1000)

    # atalhos globais
    hk = winutil.HotkeyFilter()
    app.installNativeEventFilter(hk)
    mods = winutil.MOD_CONTROL | winutil.MOD_SHIFT
    hk.register(mods, ord("L"), ctl.toggle_hidden)
    hk.register(mods, ord("K"), ctl.toggle_edit)
    hk.register(mods, ord("O"), open_settings)

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
        tray.showMessage("LLyrics", "Toque uma música e a letra aparece. O app fica aqui na bandeja.",
                         icon, 6000)

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
