"""Janela de configurações do LLyrics (as mudanças aparecem no overlay na hora)."""
import html
import threading

from PySide6.QtCore import (Property, QEasingCurve, QObject, QPointF, QPropertyAnimation, QRectF, QSize, Qt, QTimer,
                            QUrl,
                            Signal)
from PySide6.QtGui import (QColor, QDesktopServices, QFont, QGuiApplication, QLinearGradient, QPainter, QPen,
                           QPixmap)
from PySide6.QtWidgets import (QAbstractButton, QColorDialog, QComboBox, QFrame, QGridLayout, QHBoxLayout,
                               QLabel, QLineEdit, QListWidget, QListWidgetItem, QPushButton, QScrollArea,
                               QSizePolicy, QSlider, QStackedWidget, QVBoxLayout, QWidget)

import community
import hotkeys
import i18n
import lookcode
import looks
import render
from config import (ACCENT_CHOICES, ANIMATIONS, COLOUR_MODES, EXITS, FONTS, HOTKEY_DEFAULTS, IDLES, LAYOUTS,
                    PARTY_EFFECTS, POSITION_MODES, WIDGET_POSITIONS)
from i18n import tr
from version import UPDATE_REPO, __version__

MOD_SITE = "https://lyrics.remake.lol/"
MOD_AUTHOR = "FireStund"

_RESET_EXTRAS = dict(layout="lines", idle="none", colour_mode="solid", sparkle=False, party=False,
                     exit_animation="auto", letter_spacing=1.0, line_spacing=4)

PRESETS = [
    ("Shake", looks.SHAKE),
    ("Void Echoes", looks.VOID_ECHOES),
    ("preset.neon", dict(font="bebas", uppercase=True, animation="typewriter", karaoke=True, glow=True,
                         outline=True, drop_shadow=True, background=False, accent="album", letter_spacing=1.5)),
    ("preset.minimal", dict(font="poppins", uppercase=False, bold=True, animation="fade", karaoke=False,
                            glow=False, outline=False, drop_shadow=True, background=True, accent="cream",
                            letter_spacing=0)),
    ("preset.retro", dict(font="press_start", uppercase=True, bold=False, animation="wave", karaoke=True,
                          glow=False, outline=True, drop_shadow=True, background=False, accent="rainbow",
                          letter_spacing=0, text_size=30)),
    ("preset.elegant", dict(font="playfair", uppercase=False, bold=True, animation="rise", karaoke=False,
                            glow=True, outline=False, drop_shadow=True, background=False, accent="honey",
                            letter_spacing=0.5)),
    ("preset.fun", dict(font="pacifico", uppercase=False, bold=False, animation="pop", karaoke=True, glow=True,
                        outline=True, drop_shadow=False, background=False, accent="orchid", letter_spacing=0)),
]

# Cores do tema
BG = "#0F0F14"
PANEL = "#16161D"
CARD = "#1B1B24"
LINE = "#2A2A36"
TEXT = "#EDEDF3"
MUTED = "#8C8CA0"
ACC = "#C4B3FF"
ACC2 = "#E38CF2"

STYLE = f"""
* {{ font-family: 'Segoe UI'; font-size: 13px; color: {TEXT}; }}
#root {{ background: {BG}; }}
#side {{ background: {PANEL}; border-right: 1px solid {LINE}; }}
#side QLabel {{ background: transparent; }}
#sidebar {{ background: transparent; border: none; outline: none; padding: 0; }}
#sidebar::item {{ padding: 10px 12px; margin: 2px 0; border-radius: 9px; color: {MUTED}; }}
#sidebar::item:hover {{ background: #20202A; color: {TEXT}; }}
#sidebar::item:selected {{ background: #262033; color: {TEXT}; border-left: 3px solid {ACC}; }}
QScrollArea, #page {{ background: {BG}; border: none; }}
QScrollBar:vertical {{ background: transparent; width: 8px; margin: 4px; }}
QScrollBar::handle:vertical {{ background: #2E2E3B; border-radius: 4px; min-height: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
#card {{ background: {CARD}; border: 1px solid {LINE}; border-radius: 14px; }}
#lookCard {{ background: #20202A; border: 1px solid {LINE}; border-radius: 12px; }}
#lookCard QLabel {{ background: transparent; }}
#cardTitle {{ font-size: 12px; font-weight: 700; color: {ACC}; letter-spacing: 1px; }}
#rowLabel {{ font-size: 13px; }}
#caption {{ font-size: 11px; color: {MUTED}; }}
#pageTitle {{ font-size: 22px; font-weight: 700; }}
#pageSub {{ color: {MUTED}; }}
#pill {{ background: #262633; border-radius: 9px; padding: 2px 8px; color: {TEXT}; font-size: 12px; }}
QComboBox, QLineEdit {{ background: #22222D; border: 1px solid #32323F; border-radius: 9px; padding: 6px 10px;
                        min-height: 18px; }}
QComboBox:hover, QLineEdit:hover, QLineEdit:focus {{ border-color: {ACC}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{ background: #1E1E28; border: 1px solid {LINE}; selection-background-color: #34294A;
                               outline: none; padding: 4px; }}
QPushButton {{ background: #22222D; border: 1px solid #32323F; border-radius: 9px; padding: 7px 14px; }}
QPushButton:hover {{ border-color: {ACC}; background: #272734; }}
QPushButton#primary {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {ACC}, stop:1 {ACC2});
                       color: #141419; border: none; font-weight: 700; }}
QPushButton#primary:hover {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #D3C6FF, stop:1 #EDA6F7); }}
QPushButton#chip {{ border-radius: 15px; padding: 6px 14px; background: #22222D; }}
QPushButton#chip:hover {{ background: #2C2540; border-color: {ACC}; }}
QSlider::groove:horizontal {{ height: 4px; background: #30303D; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {ACC}, stop:1 {ACC2});
                                border-radius: 2px; }}
QSlider::handle:horizontal {{ background: white; width: 14px; height: 14px; margin: -5px 0; border-radius: 7px; }}
#footer {{ background: {PANEL}; border-top: 1px solid {LINE}; }}
#chipKey {{ background: #22222D; border: 1px solid #32323F; border-radius: 6px; padding: 1px 6px;
            font-size: 11px; color: {MUTED}; }}
a {{ color: {ACC}; }}
"""


# ----------------------------------------------------------------- componentes
class Toggle(QAbstractButton):
    """Interruptor liga/desliga."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self._pos = 0.0
        self._anim = QPropertyAnimation(self, b"knob", self)
        self._anim.setDuration(140)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self.toggled.connect(self._animate)

    def sizeHint(self):
        return QSize(42, 24)

    def _get_pos(self):
        return self._pos

    def _set_pos(self, v):
        self._pos = v
        self.update()

    knob = Property(float, _get_pos, _set_pos)

    def _animate(self, on):
        self._anim.stop()
        self._anim.setStartValue(self._pos)
        self._anim.setEndValue(1.0 if on else 0.0)
        self._anim.start()

    def setChecked(self, on):
        super().setChecked(on)
        self._anim.stop()
        self._pos = 1.0 if on else 0.0
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(1, 2, 40, 20)
        if self._pos > 0:
            g = QLinearGradient(r.topLeft(), r.topRight())
            on1, on2 = QColor(ACC), QColor(ACC2)
            off = QColor("#33333F")
            k = self._pos
            g.setColorAt(0, QColor.fromRgbF(*(off.getRgbF()[j] + (on1.getRgbF()[j] - off.getRgbF()[j]) * k
                                              for j in range(3))))
            g.setColorAt(1, QColor.fromRgbF(*(off.getRgbF()[j] + (on2.getRgbF()[j] - off.getRgbF()[j]) * k
                                              for j in range(3))))
            p.setBrush(g)
        else:
            p.setBrush(QColor("#33333F"))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(r, 10, 10)
        x = 3 + self._pos * 20
        p.setBrush(QColor("#FFFFFF"))
        p.drawEllipse(QRectF(x, 5, 14, 14))
        p.end()


class ColorButton(QPushButton):
    def __init__(self):
        super().__init__()
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(86, 30)
        self.hexcol = "#FFFFFF"

    def set_color(self, h):
        self.hexcol = h
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        r = QRectF(self.rect()).adjusted(1, 1, -1, -1)
        p.setPen(QPen(QColor(ACC) if self.underMouse() else QColor("#32323F"), 1))
        p.setBrush(QColor("#22222D"))
        p.drawRoundedRect(r, 9, 9)
        p.setPen(QPen(QColor(255, 255, 255, 60), 1))
        p.setBrush(QColor(self.hexcol))
        p.drawRoundedRect(QRectF(6, 6, 18, 18), 6, 6)
        f = QFont(self.font())
        f.setPixelSize(12)
        p.setFont(f)
        p.setPen(QColor(TEXT))
        p.drawText(QRectF(30, 0, r.width() - 30, r.height() + 2), Qt.AlignVCenter, self.hexcol.upper())
        p.end()


def _esc(text):
    return html.escape(str(text))[:300]


def style_preview(style, w, h):
    """Desenha uma frase de exemplo com o estilo (para os cartões da galeria)."""
    from config import DEFAULTS
    import lyrics as lyr
    cfg = dict(DEFAULTS)
    cfg.update(style)
    cfg.update(countdown=False, preview=False, previous_line=False, party=False, lyrics_opacity=1.0)
    k = 30.0 / max(1.0, float(cfg["text_size"]))
    cfg["text_size"] = 30
    cfg["letter_spacing"] = float(cfg["letter_spacing"]) * k
    cfg["line_spacing"] = float(cfg["line_spacing"]) * k
    cfg["line_width"] = 4000  # uma linha só; depois a imagem é reduzida para caber
    sample = tr("gallery.sample")
    st = render.TextStyle(cfg)
    text_w = st.fm.horizontalAdvance(st.prep(sample)) * (1.5 if cfg["layout"] != "lines" else 1.0)
    cw = int(max(w * 1.25, text_w + 70))
    ch = int(cw * h / w)
    canvas = QPixmap(cw, ch)
    canvas.fill(Qt.transparent)
    cp = QPainter(canvas)
    lines = lyr.parse_lrc(f"[00:00.00]{sample}\n[00:30.00]x")
    wins = render.line_windows(lines, cfg)
    render.draw_lyrics(cp, cw, ch, cfg, lines, wins, 9.0, None, now=9.0,
                       stack_box=(cw * 0.6, ch * 0.9) if cfg["layout"] == "stack" else None)
    cp.end()
    pm = QPixmap(w, h)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setRenderHint(QPainter.SmoothPixmapTransform)
    g = QLinearGradient(0, 0, w, h)
    g.setColorAt(0, QColor("#1D2350"))
    g.setColorAt(1, QColor("#2B3A2A"))
    p.setBrush(g)
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(QRectF(0, 0, w, h), 10, 10)
    p.drawPixmap(QRectF(0, 0, w, h), canvas, QRectF(canvas.rect()))
    p.end()
    return pm


class HotkeyButton(QPushButton):
    """Clique e aperte as teclas do novo atalho."""
    captured = Signal(str)
    message = Signal(str)

    def __init__(self, ctl):
        super().__init__()
        self.ctl = ctl
        self.value = ""
        self.capturing = False
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumWidth(200)
        self.clicked.connect(self.start)

    def set_value(self, text):
        self.value = text
        if not self.capturing:
            self.setText(text)

    def start(self):
        if self.capturing:
            return
        self.capturing = True
        self.setText(tr("keys.press"))
        self.setStyleSheet(f"border-color: {ACC}; color: {ACC};")
        if getattr(self.ctl, "suspend_hotkeys", None):
            self.ctl.suspend_hotkeys()  # senão o Windows "come" o atalho antigo antes daqui
        self.grabKeyboard()

    def stop(self):
        if not self.capturing:
            return
        self.capturing = False
        self.releaseKeyboard()
        self.setStyleSheet("")
        self.setText(self.value)
        if getattr(self.ctl, "register_hotkeys", None):
            self.ctl.register_hotkeys()

    def keyPressEvent(self, e):
        if not self.capturing:
            return super().keyPressEvent(e)
        if e.key() == Qt.Key_Escape:
            self.stop()
            return
        text, err = hotkeys.from_event(e)
        if err:
            self.message.emit(tr("keys.need_mod"))
            return
        if text:
            self.capturing = False
            self.releaseKeyboard()
            self.setStyleSheet("")
            self.captured.emit(text)

    def focusOutEvent(self, e):
        self.stop()
        super().focusOutEvent(e)


class _Bridge(QObject):
    done = Signal(bool, str, object)
    gallery = Signal(object, str)


def _icon_pixmap(size=40):
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    g = QLinearGradient(0, 0, size, size)
    g.setColorAt(0, QColor(ACC))
    g.setColorAt(1, QColor(ACC2))
    p.setBrush(g)
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(QRectF(0, 0, size, size), size * 0.28, size * 0.28)
    f = QFont("Segoe UI Symbol")
    f.setPixelSize(int(size * 0.6))
    p.setFont(f)
    p.setPen(QColor("#141419"))
    p.drawText(pm.rect(), Qt.AlignCenter, "♪")
    p.end()
    return pm


def _arrow_css():
    """Setinha das caixas de seleção (o tema escuro esconde a padrão)."""
    import os
    from config import data_dir
    path = os.path.join(data_dir(), "seta.png")
    if not os.path.exists(path):
        pm = QPixmap(20, 20)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(QPen(QColor(MUTED), 2.2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        p.drawPolyline([QPointF(6, 8), QPointF(10, 12), QPointF(14, 8)])
        p.end()
        pm.save(path)
    url = path.replace("\\", "/")
    return f"\nQComboBox::down-arrow {{ image: url('{url}'); width: 14px; height: 14px; margin-right: 8px; }}\n"


# ----------------------------------------------------------------- janela
class SettingsWindow(QWidget):
    def __init__(self, ctl):
        super().__init__(None, Qt.Window)
        self.ctl = ctl
        self.cfg = ctl.cfg
        self.setObjectName("root")
        self.setWindowTitle(tr("set.title"))
        self.resize(860, 680)
        self.setMinimumSize(720, 520)
        self.setStyleSheet(STYLE + _arrow_css())
        self.fields = {}
        self.rows = {}           # chave -> widget da linha (para esconder/mostrar)
        self._save_timer = QTimer(self, singleShot=True, interval=400)
        self._save_timer.timeout.connect(self.cfg.save)
        ctl.config_changed_externally = self.refresh
        self._bridge = _Bridge()
        self._bridge.done.connect(self._import_done)
        self._bridge.gallery.connect(self._gallery_done)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        body = QHBoxLayout()
        body.setSpacing(0)
        root.addLayout(body, 1)

        # barra lateral
        side = QWidget()
        side.setFixedWidth(200)
        side.setObjectName("side")
        sv = QVBoxLayout(side)
        sv.setContentsMargins(14, 18, 10, 14)
        brand = QHBoxLayout()
        logo = QLabel()
        logo.setPixmap(_icon_pixmap(36))
        logo.setStyleSheet("border: none;")
        brand.addWidget(logo)
        name = QLabel(f"<span style='font-size:18px; font-weight:800;'>LLyrics</span><br>"
                      f"<span style='color:{MUTED}; font-size:11px;'>{tr('set.version', v=__version__)}</span>")
        name.setStyleSheet("border: none;")
        f = name.font()
        f.setFamily(render.family("poppins"))
        name.setFont(f)
        brand.addWidget(name, 1)
        sv.addLayout(brand)
        sv.addSpacing(14)
        self.nav = QListWidget()
        self.nav.setObjectName("sidebar")
        self.nav.setFrameShape(QFrame.NoFrame)
        sv.addWidget(self.nav, 1)
        self.side_keys = QLabel()
        keys = self.side_keys
        self._update_side_keys()
        sv.addWidget(keys)
        body.addWidget(side)

        self.stack = QStackedWidget()
        body.addWidget(self.stack, 1)

        self._build_pages()
        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.nav.currentRowChanged.connect(self._page_changed)
        self.nav.setCurrentRow(0)

        # rodapé
        footer = QWidget()
        footer.setObjectName("footer")
        fh = QHBoxLayout(footer)
        fh.setContentsMargins(16, 10, 16, 10)
        move = QPushButton(tr("btn.move"))
        move.clicked.connect(ctl.toggle_edit)
        reset = QPushButton(tr("btn.reset"))
        reset.clicked.connect(self._reset)
        done = QPushButton(tr("btn.done"))
        done.setObjectName("primary")
        done.clicked.connect(self.close)
        fh.addWidget(move)
        fh.addWidget(reset)
        fh.addStretch(1)
        tip = QLabel(tr("footer.tip"))
        tip.setObjectName("caption")
        fh.addWidget(tip)
        fh.addSpacing(10)
        fh.addWidget(done)
        root.addWidget(footer)
        self._update_visibility()

    # ------------------------------------------------------------ páginas
    def _page(self, icon, title, subtitle):
        self.nav.addItem(QListWidgetItem(f"{icon}   {title}"))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        inner = QWidget()
        inner.setObjectName("page")
        v = QVBoxLayout(inner)
        v.setContentsMargins(26, 22, 26, 22)
        v.setSpacing(14)
        t = QLabel(title)
        t.setObjectName("pageTitle")
        f = t.font()
        f.setFamily(render.family("poppins"))
        t.setFont(f)
        v.addWidget(t)
        s = QLabel(subtitle)
        s.setObjectName("pageSub")
        s.setWordWrap(True)
        v.addWidget(s)
        v.addSpacing(4)
        scroll.setWidget(inner)
        self.stack.addWidget(scroll)
        return v

    def _card(self, layout, title, rows=None):
        card = QFrame()
        card.setObjectName("card")
        cv = QVBoxLayout(card)
        cv.setContentsMargins(18, 14, 18, 14)
        cv.setSpacing(10)
        t = QLabel(title.upper())
        t.setObjectName("cardTitle")
        cv.addWidget(t)
        for row in rows or []:
            cv.addWidget(self._row(*row))
        layout.addWidget(card)
        return cv

    def _row(self, key, kind):
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 2, 0, 2)
        h.setSpacing(16)
        lv = QVBoxLayout()
        lv.setSpacing(1)
        lb = QLabel(tr(f"opt.{key}"))
        lb.setObjectName("rowLabel")
        lv.addWidget(lb)
        if f"cap.{key}" in i18n.S:
            c = QLabel(tr(f"cap.{key}", key=self.cfg.get("hotkey_move", "")))
            c.setObjectName("caption")
            c.setWordWrap(True)
            lv.addWidget(c)
        h.addLayout(lv, 1)
        ctrl = self._field(key, kind)
        h.addWidget(ctrl, 0, Qt.AlignRight | Qt.AlignVCenter)
        self.rows[key] = w
        return w

    def _build_pages(self):
        screens = [(i, tr("monitor.name", n=i + 1, w=s.size().width(), h=s.size().height()))
                   for i, s in enumerate(QGuiApplication.screens())]
        C = i18n.choices

        v = self._page("◎", tr("page.general"), tr("page.general.sub"))
        self._card(v, tr("card.language"), [("language", ("choice", i18n.LANGUAGES))])
        self._card(v, tr("card.display"), [("show_lyrics", "bool"), ("show_widget", "bool"),
                                           ("hide_paused", "bool")])
        self._card(v, tr("card.position"), [
            ("position_mode", ("choice", C(POSITION_MODES))),
            ("allow_center", "bool"),
            ("center_zone", ("slider", 0.15, 0.7, 0.01, "")),
            ("screen_index", ("choice", screens)),
        ])
        self._card(v, tr("card.sync"), [
            ("sync_offset", ("slider", -3.0, 3.0, 0.05, "s")),
            ("fps", ("choice", [(30, "30"), (60, "60"), (120, "120"), (144, "144")])),
        ])
        self._card(v, tr("card.app"), [("autostart", "bool"), ("auto_update", "bool")])
        v.addStretch(1)

        v = self._page("✦", tr("page.animation"), tr("page.animation.sub"))
        self._card(v, tr("card.layout"), [
            ("layout", ("choice", C(LAYOUTS))),
            ("animation", ("choice", C(ANIMATIONS))),
            ("exit_animation", ("choice", C(EXITS))),
            ("typewriter_sync", "bool"),
            ("typewriter_speed", ("slider", 0.3, 3.0, 0.1, "x")),
        ])
        self._card(v, tr("card.extras"), [("karaoke", "bool"), ("countdown", "bool"), ("previous_line", "bool"),
                                          ("preview", "bool")])
        self._card(v, tr("card.effects"), [
            ("idle", ("choice", C(IDLES))),
            ("idle_speed", ("slider", 0.1, 3.0, 0.05, "x")),
            ("idle_strength", ("slider", 0.1, 3.0, 0.05, "x")),
            ("sparkle", "bool"),
            ("sparkle_amount", ("slider", 0.5, 4.0, 0.25, "x")),
            ("party", "bool"),
            ("party_effects", ("choice", C(PARTY_EFFECTS))),
        ])
        v.addStretch(1)

        v = self._page("◐", tr("page.style"), tr("page.style.sub"))
        cv = self._card(v, tr("card.presets"))
        grid = QGridLayout()
        grid.setSpacing(8)
        for i, (name, _settings) in enumerate(PRESETS):
            b = QPushButton(tr(name) if name in i18n.S else name)
            b.setObjectName("chip")
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, n=i: self._apply_preset(n))
            grid.addWidget(b, i // 4, i % 4)
        cv.addLayout(grid)

        cv = self._card(v, tr("card.community"))
        imp = QHBoxLayout()
        self.code_edit = QLineEdit()
        self.code_edit.setPlaceholderText(tr("import.placeholder"))
        self.code_btn = QPushButton(tr("btn.import"))
        self.code_btn.setObjectName("primary")
        self.code_btn.setCursor(Qt.PointingHandCursor)
        self.code_btn.clicked.connect(self._import_code)
        self.code_edit.returnPressed.connect(self._import_code)
        imp.addWidget(self.code_edit, 1)
        imp.addWidget(self.code_btn)
        cv.addLayout(imp)
        self.import_msg = QLabel("")
        self.import_msg.setObjectName("caption")
        self.import_msg.setWordWrap(True)
        self.import_msg.setVisible(False)
        cv.addWidget(self.import_msg)
        site = f"<a href='{MOD_SITE}' style='color:{ACC}; text-decoration:none;'>lyrics.remake.lol</a>"
        credit = QLabel(f"<span style='color:{MUTED}; font-size:11px;'>"
                        f"{tr('community.credit', site=site, author=MOD_AUTHOR)}</span>")
        credit.setOpenExternalLinks(True)
        credit.setWordWrap(True)
        cv.addWidget(credit)

        self._card(v, tr("card.colour"), [
            ("accent", ("choice", C(ACCENT_CHOICES))),
            ("custom_colour", "color"),
            ("colour_mode", ("choice", C(COLOUR_MODES))),
            ("second_colour", "color"),
            ("third_colour", "color"),
        ])
        self._card(v, tr("card.font"), [
            ("font", ("choice", C([(k, n) for k, n, _ in FONTS]))),
            ("bold", "bool"),
            ("uppercase", "bool"),
            ("text_size", ("slider", 16, 120, 1, "px")),
            ("letter_spacing", ("slider", -3.0, 12.0, 0.5, "px")),
            ("line_spacing", ("slider", 0, 40, 1, "px")),
            ("line_width", ("slider", 300, 1800, 10, "px")),
        ])
        self._card(v, tr("card.finish"), [
            ("outline", "bool"),
            ("outline_colour", "color"),
            ("outline_thickness", ("slider", 0.3, 2.5, 0.05, "x")),
            ("drop_shadow", "bool"),
            ("glow", "bool"),
            ("background", "bool"),
            ("lyrics_opacity", ("slider", 0.15, 1.0, 0.05, "")),
        ])
        v.addStretch(1)

        v = self._page("☆", tr("page.community"), tr("page.community.sub"))
        cv = self._card(v, tr("card.share"))
        cap = QLabel(tr("share.caption"))
        cap.setObjectName("caption")
        cap.setWordWrap(True)
        cv.addWidget(cap)
        self.share_name = QLineEdit()
        self.share_name.setPlaceholderText(tr("share.name_ph"))
        self.share_author = QLineEdit()
        self.share_author.setPlaceholderText(tr("share.author_ph"))
        self.share_author.setText(self.cfg.get("share_author", ""))
        row = QHBoxLayout()
        row.addWidget(self.share_name, 1)
        row.addWidget(self.share_author, 1)
        cv.addLayout(row)
        self.share_desc = QLineEdit()
        self.share_desc.setPlaceholderText(tr("share.desc_ph"))
        cv.addWidget(self.share_desc)
        row = QHBoxLayout()
        self.share_msg = QLabel("")
        self.share_msg.setObjectName("caption")
        self.share_msg.setWordWrap(True)
        row.addWidget(self.share_msg, 1)
        copy_btn = QPushButton(tr("share.copy"))
        copy_btn.setCursor(Qt.PointingHandCursor)
        copy_btn.clicked.connect(self._copy_style_code)
        pub_btn = QPushButton(tr("share.publish"))
        pub_btn.setObjectName("primary")
        pub_btn.setCursor(Qt.PointingHandCursor)
        pub_btn.clicked.connect(self._publish_style)
        row.addWidget(copy_btn)
        row.addWidget(pub_btn)
        cv.addLayout(row)

        cv = self._card(v, tr("card.gallery"))
        row = QHBoxLayout()
        self.gallery_search = QLineEdit()
        self.gallery_search.setPlaceholderText(tr("gallery.search"))
        self.gallery_search.textChanged.connect(self._filter_gallery)
        refresh = QPushButton(tr("gallery.refresh"))
        refresh.setCursor(Qt.PointingHandCursor)
        refresh.clicked.connect(lambda: self._load_gallery(force=True))
        row.addWidget(self.gallery_search, 1)
        row.addWidget(refresh)
        cv.addLayout(row)
        self.gallery_msg = QLabel(tr("gallery.loading"))
        self.gallery_msg.setObjectName("caption")
        self.gallery_msg.setWordWrap(True)
        cv.addWidget(self.gallery_msg)
        self.gallery_box = QVBoxLayout()
        self.gallery_box.setSpacing(10)
        cv.addLayout(self.gallery_box)
        self.gallery_cards = []
        note = QLabel(f"<span style='color:{MUTED}; font-size:11px;'>{tr('gallery.mod_note')}</span>")
        note.setWordWrap(True)
        cv.addWidget(note)
        v.addStretch(1)
        self._gallery_loaded = False

        v = self._page("▣", tr("page.widget"), tr("page.widget.sub"))
        self._card(v, tr("card.widget"), [
            ("widget_position", ("choice", C(WIDGET_POSITIONS))),
            ("widget_scale", ("slider", 0.6, 2.0, 0.05, "x")),
            ("widget_opacity", ("slider", 0.2, 1.0, 0.05, "")),
        ])
        v.addStretch(1)

        v = self._page("⌨", tr("page.keys"), tr("page.keys.sub"))
        cv = self._card(v, tr("card.shortcuts"), [(k, "hotkey") for k in HOTKEY_DEFAULTS])
        self.keys_msg = QLabel(tr("keys.caption"))
        self.keys_msg.setObjectName("caption")
        self.keys_msg.setWordWrap(True)
        cv.addWidget(self.keys_msg)
        rk = QHBoxLayout()
        rk.addStretch(1)
        rbtn = QPushButton(tr("keys.reset"))
        rbtn.setCursor(Qt.PointingHandCursor)
        rbtn.clicked.connect(self._reset_hotkeys)
        rk.addWidget(rbtn)
        cv.addLayout(rk)
        v.addStretch(1)

        v = self._page("♡", tr("page.about"), tr("page.about.sub"))
        cv = self._card(v, "LLyrics")
        info = QHBoxLayout()
        logo = QLabel()
        logo.setPixmap(_icon_pixmap(56))
        info.addWidget(logo)
        txt = QLabel(f"<span style='font-size:16px; font-weight:700;'>LLyrics {__version__}</span><br>"
                     f"<span style='color:{MUTED};'>{tr('app.tagline')}</span><br>"
                     f"<a href='https://github.com/{UPDATE_REPO}' style='color:{ACC}; text-decoration:none;'>"
                     f"github.com/{UPDATE_REPO}</a>")
        txt.setOpenExternalLinks(True)
        info.addWidget(txt, 1)
        upd = QPushButton(tr("btn.check_updates"))
        upd.setObjectName("primary")
        upd.setCursor(Qt.PointingHandCursor)
        upd.clicked.connect(lambda: getattr(self.ctl, "updater", None) and self.ctl.updater.check(manual=True))
        info.addWidget(upd)
        cv.addLayout(info)

        cv = self._card(v, tr("card.credits"))
        site = f"<a href='{MOD_SITE}' style='color:{ACC}; text-decoration:none;'>lyrics.remake.lol</a>"
        credits = QLabel(
            f"<p style='line-height:150%;'>{tr('credits.main', author=MOD_AUTHOR, site=site)}</p>"
            f"<p style='line-height:150%;'>{tr('credits.lyrics')} <a href='https://lrclib.net' "
            f"style='color:{ACC}; text-decoration:none;'>lrclib.net</a><br>{tr('credits.fonts')}</p>")
        credits.setOpenExternalLinks(True)
        credits.setWordWrap(True)
        cv.addWidget(credits)
        v.addStretch(1)

    # ------------------------------------------------------------ campos
    def _field(self, key, kind):
        cfg = self.cfg
        if kind == "bool":
            w = Toggle()
            w.setChecked(bool(cfg[key]))
            w.toggled.connect(lambda v, k=key: self._set(k, bool(v)))
            self.fields[key] = ("bool", w)
            return w
        if kind == "hotkey":
            w = HotkeyButton(self.ctl)
            w.set_value(cfg[key])
            w.captured.connect(lambda text, k=key: self._hotkey_captured(k, text))
            w.message.connect(lambda m: self.keys_msg.setText(m))
            self.fields[key] = ("hotkey", w)
            return w
        if kind == "color":
            w = ColorButton()
            w.set_color(cfg[key])
            w.clicked.connect(lambda _=False, k=key: self._pick_color(k))
            self.fields[key] = ("color", w)
            return w
        if kind[0] == "choice":
            w = QComboBox()
            w.setMinimumWidth(240)
            w.setCursor(Qt.PointingHandCursor)
            for v, name in kind[1]:
                w.addItem(name, v)
            i = w.findData(cfg[key])
            if i >= 0:
                w.setCurrentIndex(i)
            w.currentIndexChanged.connect(lambda i, k=key, cb=w: self._set(k, cb.itemData(i)))
            self.fields[key] = ("choice", w)
            return w
        _, lo, hi, step, unit = kind
        box = QWidget()
        box.setFixedWidth(280)
        h = QHBoxLayout(box)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(10)
        s = QSlider(Qt.Horizontal)
        s.setRange(0, int(round((hi - lo) / step)))
        s.setCursor(Qt.PointingHandCursor)
        lab = QLabel()
        lab.setObjectName("pill")
        lab.setAlignment(Qt.AlignCenter)
        lab.setFixedWidth(64)
        is_int = isinstance(step, int)

        def to_val(i):
            v = lo + i * step
            return int(v) if is_int else round(v, 3)

        def show(i):
            v = to_val(i)
            lab.setText((f"{v}" if is_int else f"{v:.2f}") + (f" {unit}" if unit else ""))

        s.setValue(int(round((float(cfg[key]) - lo) / step)))
        show(s.value())
        s.valueChanged.connect(lambda i, k=key: (show(i), self._set(k, to_val(i))))
        h.addWidget(s, 1)
        h.addWidget(lab)
        self.fields[key] = ("slider", s, lo, step, show)
        return box

    def _update_side_keys(self):
        c = self.cfg
        self.side_keys.setText(
            f"<span style='color:{MUTED}; font-size:11px;'>"
            f"{c['hotkey_toggle']} &nbsp;{tr('side.toggle')}<br>{c['hotkey_move']} &nbsp;{tr('side.move')}<br>"
            f"{c['hotkey_settings']} &nbsp;{tr('side.settings')}</span>")

    def _page_changed(self, row):
        if self.nav.item(row) and tr("page.community") in self.nav.item(row).text() and not self._gallery_loaded:
            self._gallery_loaded = True
            self._load_gallery()

    # ------------------------------------------------------------ comunidade
    def _copy_style_code(self):
        QGuiApplication.clipboard().setText(lookcode.encode(lookcode.style_of(self.cfg)))
        self.share_msg.setText(tr("share.copied"))

    def _publish_style(self):
        name = self.share_name.text().strip()
        if not name:
            self.share_msg.setText(tr("share.need_name"))
            self.share_name.setFocus()
            return
        author = self.share_author.text().strip()
        self.cfg["share_author"] = author
        self.cfg.save()
        code = lookcode.encode(lookcode.style_of(self.cfg))
        QDesktopServices.openUrl(QUrl(community.submit_url(name, author, self.share_desc.text().strip(), code)))
        self.share_msg.setText(tr("share.opened"))

    def _load_gallery(self, force=False):
        self.gallery_msg.setText(tr("gallery.loading"))
        self.gallery_msg.setVisible(True)

        def work():
            try:
                self._bridge.gallery.emit(community.fetch_gallery(force), "")
            except OSError as e:
                self._bridge.gallery.emit(None, str(e))

        threading.Thread(target=work, daemon=True).start()

    def _gallery_done(self, looks, err):
        for card in self.gallery_cards:
            card.setParent(None)
            card.deleteLater()
        self.gallery_cards = []
        if looks is None:
            self.gallery_msg.setText(tr("gallery.error", e=err))
            return
        if not looks:
            self.gallery_msg.setText(tr("gallery.empty"))
            return
        self.gallery_msg.setVisible(False)
        for look in looks:
            try:
                style = lookcode.decode(look["code"])
            except ValueError:
                continue
            card = self._gallery_card(look, style)
            self.gallery_box.addWidget(card)
            self.gallery_cards.append(card)
        self._filter_gallery(self.gallery_search.text())

    def _gallery_card(self, look, style):
        card = QFrame()
        card.setObjectName("lookCard")
        card.search_text = " ".join(str(look.get(k, "")) for k in ("name", "author", "description")).lower()
        h = QHBoxLayout(card)
        h.setContentsMargins(10, 10, 12, 10)
        h.setSpacing(14)
        pic = QLabel()
        pic.setPixmap(style_preview(style, 260, 84))
        h.addWidget(pic)
        info = QVBoxLayout()
        info.setSpacing(2)
        title = QLabel(f"<b>{_esc(look.get('name', '?'))}</b>")
        info.addWidget(title)
        if look.get("author"):
            by = QLabel(tr("gallery.by", author=str(look["author"])[:40]))
            by.setTextFormat(Qt.PlainText)
            by.setObjectName("caption")
            info.addWidget(by)
        if look.get("description"):
            d = QLabel(str(look["description"])[:200])
            d.setTextFormat(Qt.PlainText)
            d.setObjectName("caption")
            d.setWordWrap(True)
            info.addWidget(d)
        info.addStretch(1)
        btns = QHBoxLayout()
        apply_btn = QPushButton(tr("gallery.apply"))
        apply_btn.setObjectName("primary")
        apply_btn.setCursor(Qt.PointingHandCursor)
        apply_btn.clicked.connect(lambda _=False, s=style, n=look.get("name", ""): self._apply_style(s, n))
        copy_btn = QPushButton(tr("share.copy"))
        copy_btn.setCursor(Qt.PointingHandCursor)
        copy_btn.clicked.connect(lambda _=False, c=look["code"]: QGuiApplication.clipboard().setText(c))
        btns.addWidget(apply_btn)
        btns.addWidget(copy_btn)
        btns.addStretch(1)
        info.addLayout(btns)
        h.addLayout(info, 1)
        return card

    def _filter_gallery(self, text):
        q = (text or "").strip().lower()
        shown = 0
        for card in self.gallery_cards:
            ok = not q or q in card.search_text
            card.setVisible(ok)
            shown += ok
        if self.gallery_cards:
            self.gallery_msg.setText(tr("gallery.none_found"))
            self.gallery_msg.setVisible(shown == 0)

    def _apply_style(self, style, name):
        self.cfg.update(_RESET_EXTRAS)
        self.cfg.update(style)
        self.refresh()
        self.ctl.apply_config()
        self.cfg.save()
        self.gallery_msg.setText(tr("gallery.applied", name=name))
        self.gallery_msg.setVisible(True)

    # Linhas que só fazem sentido com outra opção ligada
    def _update_visibility(self):
        c = self.cfg
        rules = {
            "center_zone": not c["allow_center"],
            "typewriter_sync": c["animation"] == "typewriter",
            "typewriter_speed": c["animation"] == "typewriter" and not c["typewriter_sync"],
            "previous_line": c["layout"] != "stack",
            "preview": c["layout"] != "stack",
            "idle_speed": c["idle"] != "none",
            "idle_strength": c["idle"] != "none",
            "sparkle_amount": c["sparkle"],
            "party_effects": c["party"],
            "custom_colour": c["accent"] == "custom",
            "second_colour": c["colour_mode"] in ("gradient", "gradient3"),
            "third_colour": c["colour_mode"] == "gradient3",
            "outline_colour": c["outline"],
            "outline_thickness": c["outline"],
        }
        for key, show in rules.items():
            if key in self.rows:
                self.rows[key].setVisible(bool(show))

    # ------------------------------------------------------------ ações
    def _hotkey_captured(self, key, text):
        btn = self.fields[key][1]
        others = [k for k in HOTKEY_DEFAULTS if k != key]
        if any(self.cfg[k].lower() == text.lower() for k in others):
            self.keys_msg.setText(tr("keys.duplicate"))
        else:
            old = self.cfg[key]
            self.cfg[key] = text
            failed = self.ctl.register_hotkeys() if getattr(self.ctl, "register_hotkeys", None) else []
            if key in failed:
                self.cfg[key] = old
                self.keys_msg.setText(tr("keys.in_use", keys=text))
            else:
                self.keys_msg.setText(tr("keys.saved"))
                self.cfg.save()
        if getattr(self.ctl, "register_hotkeys", None):
            self.ctl.register_hotkeys()
        btn.set_value(self.cfg[key])
        self._update_side_keys()

    def _reset_hotkeys(self):
        self.cfg.update(HOTKEY_DEFAULTS)
        failed = self.ctl.register_hotkeys() if getattr(self.ctl, "register_hotkeys", None) else []
        self.keys_msg.setText(tr("keys.in_use", keys=", ".join(self.cfg[k] for k in failed)) if failed
                              else tr("keys.saved"))
        self.cfg.save()
        self.refresh()
        self._update_side_keys()

    def _set(self, key, value):
        self.cfg[key] = value
        if key == "language":
            self.cfg.save()
            if getattr(self.ctl, "language_changed", None):
                self.ctl.language_changed()
            return
        if key == "autostart":
            import winutil
            winutil.set_autostart(bool(value))
        self.ctl.apply_config()
        self._update_visibility()
        self._save_timer.start()

    def _pick_color(self, key):
        c = QColorDialog.getColor(QColor(self.cfg[key]), self, tr("color.pick"))
        if c.isValid():
            self.fields[key][1].set_color(c.name())
            if key == "custom_colour":
                self.cfg["accent"] = "custom"
                self.refresh()
            self._set(key, c.name())

    def _apply_preset(self, index):
        self.cfg.update(_RESET_EXTRAS)
        self.cfg.update(PRESETS[index][1])
        self.refresh()
        self.ctl.apply_config()
        self.cfg.save()

    def _import_code(self):
        code = self.code_edit.text()
        if lookcode.find_code(code):
            try:
                style = lookcode.decode(code)
            except ValueError:
                self._msg(tr("import.bad_llyrics"))
                return
            self.cfg.update(_RESET_EXTRAS)
            self.cfg.update(style)
            self.refresh()
            self.ctl.apply_config()
            self.cfg.save()
            self._msg(tr("import.llyrics_applied"))
            return
        self.code_btn.setEnabled(False)
        self._msg(tr("import.searching"))

        def work():
            try:
                name, author, settings = looks.fetch_look(code)
                self._bridge.done.emit(True, f"\"{name}\"" + (tr("import.by", author=author) if author else ""), settings)
            except ValueError as e:
                self._bridge.done.emit(False, str(e), {})

        threading.Thread(target=work, daemon=True).start()

    def _msg(self, text):
        self.import_msg.setText(text)
        self.import_msg.setVisible(bool(text))

    def _import_done(self, ok, msg, settings):
        self.code_btn.setEnabled(True)
        if not ok:
            self._msg(msg)
            return
        self.cfg.update(_RESET_EXTRAS)
        self.cfg.update(settings)
        self.refresh()
        self.ctl.apply_config()
        self.cfg.save()
        self._msg(tr("import.applied", name=msg))

    def _reset(self):
        keep = {k: self.cfg[k] for k in ("lyrics_x", "lyrics_y", "screen_index", "autostart", "auto_update",
                                         "language", *HOTKEY_DEFAULTS)}
        self.cfg.reset()
        self.cfg.update(keep)
        self.refresh()
        self.ctl.apply_config()
        self.cfg.save()

    def refresh(self):
        for key, f in self.fields.items():
            kind, w = f[0], f[1]
            w.blockSignals(True)
            if kind == "bool":
                w.setChecked(bool(self.cfg[key]))
            elif kind == "color":
                w.set_color(self.cfg[key])
            elif kind == "hotkey":
                w.set_value(self.cfg[key])
            elif kind == "choice":
                i = w.findData(self.cfg[key])
                if i >= 0:
                    w.setCurrentIndex(i)
            else:
                _, sl, lo, step, show = f
                sl.setValue(int(round((float(self.cfg[key]) - lo) / step)))
                show(sl.value())
            w.blockSignals(False)
        self._update_visibility()

    def showEvent(self, e):
        super().showEvent(e)
        self.ctl.demo = True

    def closeEvent(self, e):
        for f in self.fields.values():
            if f[0] == "hotkey":
                f[1].stop()
        self.ctl.demo = False
        if self.ctl.edit:
            self.ctl.set_edit(False)
        self.cfg.save()
        super().closeEvent(e)
