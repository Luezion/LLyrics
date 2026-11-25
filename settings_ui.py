"""Janela de configurações do LLyrics (as mudanças aparecem no overlay na hora)."""
import threading

from PySide6.QtCore import (Property, QEasingCurve, QObject, QPointF, QPropertyAnimation, QRectF, QSize, Qt, QTimer,
                            Signal)
from PySide6.QtGui import QColor, QFont, QGuiApplication, QLinearGradient, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (QAbstractButton, QColorDialog, QComboBox, QFrame, QGridLayout, QHBoxLayout,
                               QLabel, QLineEdit, QListWidget, QListWidgetItem, QPushButton, QScrollArea,
                               QSizePolicy, QSlider, QStackedWidget, QVBoxLayout, QWidget)

import looks
import render
from config import (ACCENT_CHOICES, ANIMATIONS, COLOUR_MODES, EXITS, FONTS, IDLES, LAYOUTS, PARTY_EFFECTS,
                    POSITION_MODES, WIDGET_POSITIONS)
from version import UPDATE_REPO, __version__

MOD_SITE = "https://lyrics.remake.lol/"
MOD_AUTHOR = "FireStund"

_RESET_EXTRAS = dict(layout="lines", idle="none", colour_mode="solid", sparkle=False, party=False,
                     exit_animation="auto", letter_spacing=1.0, line_spacing=4)

PRESETS = {
    "Shake": looks.SHAKE,
    "Void Echoes": looks.VOID_ECHOES,
    "Neon karaokê": dict(font="bebas", uppercase=True, animation="typewriter", karaoke=True, glow=True,
                         outline=True, drop_shadow=True, background=False, accent="album", letter_spacing=1.5),
    "Minimalista": dict(font="poppins", uppercase=False, bold=True, animation="fade", karaoke=False, glow=False,
                        outline=False, drop_shadow=True, background=True, accent="cream", letter_spacing=0),
    "Retrô pixel": dict(font="press_start", uppercase=True, bold=False, animation="wave", karaoke=True,
                        glow=False, outline=True, drop_shadow=True, background=False, accent="rainbow",
                        letter_spacing=0, text_size=30),
    "Elegante": dict(font="playfair", uppercase=False, bold=True, animation="rise", karaoke=False, glow=True,
                     outline=False, drop_shadow=True, background=False, accent="honey", letter_spacing=0.5),
    "Divertido": dict(font="pacifico", uppercase=False, bold=False, animation="pop", karaoke=True, glow=True,
                      outline=True, drop_shadow=False, background=False, accent="orchid", letter_spacing=0),
}

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


class _Bridge(QObject):
    done = Signal(bool, str, object)


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
        self.setWindowTitle("LLyrics — configurações")
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
                      f"<span style='color:{MUTED}; font-size:11px;'>versão {__version__}</span>")
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
        keys = QLabel(f"<span style='color:{MUTED}; font-size:11px; line-height:150%;'>"
                      "Ctrl+Shift+L &nbsp;mostrar/esconder<br>Ctrl+Shift+K &nbsp;mover<br>"
                      "Ctrl+Shift+O &nbsp;configurações</span>")
        keys.setStyleSheet("border: none;")
        sv.addWidget(keys)
        body.addWidget(side)

        self.stack = QStackedWidget()
        body.addWidget(self.stack, 1)

        self._build_pages()
        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.nav.setCurrentRow(0)

        # rodapé
        footer = QWidget()
        footer.setObjectName("footer")
        fh = QHBoxLayout(footer)
        fh.setContentsMargins(16, 10, 16, 10)
        move = QPushButton("Mover janelas")
        move.clicked.connect(ctl.toggle_edit)
        reset = QPushButton("Restaurar padrão")
        reset.clicked.connect(self._reset)
        done = QPushButton("Pronto")
        done.setObjectName("primary")
        done.clicked.connect(self.close)
        fh.addWidget(move)
        fh.addWidget(reset)
        fh.addStretch(1)
        tip = QLabel("As mudanças aparecem na hora")
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

    def _row(self, key, label, kind, caption=None):
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(0, 2, 0, 2)
        h.setSpacing(16)
        lv = QVBoxLayout()
        lv.setSpacing(1)
        lb = QLabel(label)
        lb.setObjectName("rowLabel")
        lv.addWidget(lb)
        if caption:
            c = QLabel(caption)
            c.setObjectName("caption")
            c.setWordWrap(True)
            lv.addWidget(c)
        h.addLayout(lv, 1)
        ctrl = self._field(key, kind)
        h.addWidget(ctrl, 0, Qt.AlignRight | Qt.AlignVCenter)
        self.rows[key] = w
        return w

    def _build_pages(self):
        screens = [(i, f"Monitor {i + 1} ({s.size().width()}x{s.size().height()})")
                   for i, s in enumerate(QGuiApplication.screens())]

        v = self._page("◎", "Geral", "O que aparece na tela, onde e quando.")
        self._card(v, "Exibição", [
            ("show_lyrics", "Mostrar letras", "bool"),
            ("show_widget", "Mostrar widget do player", "bool", "Capa, título, artista e barra de progresso."),
            ("hide_paused", "Ocultar quando pausado", "bool"),
        ])
        self._card(v, "Posição", [
            ("position_mode", "Posição da letra", ("choice", POSITION_MODES),
             "Aleatória: cada linha nova aparece num lugar diferente."),
            ("allow_center", "Pode aparecer no centro da tela", "bool",
             "Desligue em jogos de tiro para a letra nunca cobrir a mira."),
            ("center_zone", "Tamanho da área livre no centro", ("slider", 0.15, 0.7, 0.01, "")),
            ("screen_index", "Monitor", ("choice", screens)),
        ])
        self._card(v, "Sincronia e desempenho", [
            ("sync_offset", "Ajuste de sincronia", ("slider", -3.0, 3.0, 0.05, "s"),
             "Aumente se as palavras chegam depois de você ouvir."),
            ("fps", "Quadros por segundo", ("choice", [(30, "30"), (60, "60"), (120, "120"), (144, "144")])),
        ])
        self._card(v, "App", [
            ("autostart", "Abrir junto com o Windows", "bool"),
            ("auto_update", "Procurar atualizações sozinho", "bool"),
        ])
        v.addStretch(1)

        v = self._page("✦", "Animação", "Como as linhas entram, ficam e saem.")
        self._card(v, "Layout e movimento", [
            ("layout", "Layout", ("choice", LAYOUTS),
             "Pilha: palavras importantes grandes e as pequenas menores, uma de cada vez."),
            ("animation", "Entrada", ("choice", ANIMATIONS)),
            ("exit_animation", "Saída", ("choice", EXITS)),
            ("typewriter_sync", "Digitar no ritmo da música", "bool"),
            ("typewriter_speed", "Velocidade da digitação", ("slider", 0.3, 3.0, 0.1, "x")),
        ])
        self._card(v, "Extras da letra", [
            ("karaoke", "Destaque de karaokê", "bool", "A linha acende conforme é cantada."),
            ("countdown", "Contagem instrumental", "bool", "Pontinhos enchendo nas pausas longas."),
            ("previous_line", "Linha anterior", "bool"),
            ("preview", "Prévia da próxima linha", "bool"),
        ])
        self._card(v, "Efeitos", [
            ("idle", "Movimento parado", ("choice", IDLES)),
            ("idle_speed", "Velocidade do movimento", ("slider", 0.1, 3.0, 0.05, "x")),
            ("idle_strength", "Força do movimento", ("slider", 0.1, 3.0, 0.05, "x")),
            ("sparkle", "Brilhinhos na letra", "bool"),
            ("sparkle_amount", "Quantidade de brilhinhos", ("slider", 0.5, 4.0, 0.25, "x")),
            ("party", "Modo festa", "bool", "Notas musicais subindo ao fundo."),
            ("party_effects", "Efeitos da festa", ("choice", PARTY_EFFECTS)),
        ])
        v.addStretch(1)

        v = self._page("◐", "Estilo", "Cores, fonte e acabamento da letra.")
        cv = self._card(v, "Estilos prontos")
        grid = QGridLayout()
        grid.setSpacing(8)
        for i, name in enumerate(PRESETS):
            b = QPushButton(name)
            b.setObjectName("chip")
            b.setCursor(Qt.PointingHandCursor)
            b.clicked.connect(lambda _=False, n=name: self._apply_preset(n))
            grid.addWidget(b, i // 4, i % 4)
        cv.addLayout(grid)

        cv = self._card(v, "Looks da comunidade")
        imp = QHBoxLayout()
        self.code_edit = QLineEdit()
        self.code_edit.setPlaceholderText("Cole o código ou o link de um look (ex.: STL-JMQZYC)")
        self.code_btn = QPushButton("Importar")
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
        credit = QLabel(
            f"<span style='color:{MUTED}; font-size:11px;'>Encontre looks em "
            f"<a href='{MOD_SITE}' style='color:{ACC}; text-decoration:none;'>lyrics.remake.lol</a>"
            f", a galeria do mod <b>Show the Lyrics</b>, criado por <b>{MOD_AUTHOR}</b>.</span>")
        credit.setOpenExternalLinks(True)
        credit.setWordWrap(True)
        cv.addWidget(credit)

        self._card(v, "Cor", [
            ("accent", "Cor de destaque", ("choice", ACCENT_CHOICES), "Álbum usa a cor da capa da música."),
            ("custom_colour", "Cor personalizada", "color"),
            ("colour_mode", "Modo de cor", ("choice", COLOUR_MODES)),
            ("second_colour", "Segunda cor", "color"),
            ("third_colour", "Terceira cor", "color"),
        ])
        self._card(v, "Fonte", [
            ("font", "Fonte", ("choice", [(k, n) for k, n, _ in FONTS])),
            ("bold", "Negrito", "bool"),
            ("uppercase", "Maiúsculas", "bool"),
            ("text_size", "Tamanho do texto", ("slider", 16, 120, 1, "px")),
            ("letter_spacing", "Espaço entre letras", ("slider", -3.0, 12.0, 0.5, "px")),
            ("line_spacing", "Espaço entre linhas", ("slider", 0, 40, 1, "px")),
            ("line_width", "Largura da linha", ("slider", 300, 1800, 10, "px")),
        ])
        self._card(v, "Acabamento", [
            ("outline", "Contorno", "bool"),
            ("outline_colour", "Cor do contorno", "color"),
            ("outline_thickness", "Espessura do contorno", ("slider", 0.3, 2.5, 0.05, "x")),
            ("drop_shadow", "Sombra", "bool"),
            ("glow", "Brilho", "bool"),
            ("background", "Fundo atrás do texto", "bool"),
            ("lyrics_opacity", "Opacidade da letra", ("slider", 0.15, 1.0, 0.05, "")),
        ])
        v.addStretch(1)

        v = self._page("▣", "Widget", "O cartão \"tocando agora\".")
        self._card(v, "Widget do player", [
            ("widget_position", "Posição", ("choice", WIDGET_POSITIONS),
             "Use Ctrl+Shift+K para arrastar para onde quiser."),
            ("widget_scale", "Tamanho", ("slider", 0.6, 2.0, 0.05, "x")),
            ("widget_opacity", "Opacidade", ("slider", 0.2, 1.0, 0.05, "")),
        ])
        v.addStretch(1)

        v = self._page("♡", "Sobre", "Versão, atualizações e créditos.")
        cv = self._card(v, "LLyrics")
        info = QHBoxLayout()
        logo = QLabel()
        logo.setPixmap(_icon_pixmap(56))
        info.addWidget(logo)
        txt = QLabel(f"<span style='font-size:16px; font-weight:700;'>LLyrics {__version__}</span><br>"
                     f"<span style='color:{MUTED};'>Letras sincronizadas por cima dos seus jogos.</span><br>"
                     f"<a href='https://github.com/{UPDATE_REPO}' style='color:{ACC}; text-decoration:none;'>"
                     f"github.com/{UPDATE_REPO}</a>")
        txt.setOpenExternalLinks(True)
        info.addWidget(txt, 1)
        upd = QPushButton("Procurar atualizações")
        upd.setObjectName("primary")
        upd.setCursor(Qt.PointingHandCursor)
        upd.clicked.connect(lambda: getattr(self.ctl, "updater", None) and self.ctl.updater.check(manual=True))
        info.addWidget(upd)
        cv.addLayout(info)

        cv = self._card(v, "Créditos")
        credits = QLabel(
            f"<p style='line-height:150%;'>Inspirado no mod de Minecraft <b>Show the Lyrics</b>, "
            f"criado por <b>{MOD_AUTHOR}</b>. Os estilos \"Shake\" e \"Void Echoes\" vêm da galeria da "
            f"comunidade do mod: <a href='{MOD_SITE}' style='color:{ACC}; text-decoration:none;'>"
            f"lyrics.remake.lol</a> (looks de Sodd71 e Trickbound).<br>"
            f"O código do LLyrics foi escrito do zero; nenhum código do mod foi usado.</p>"
            f"<p style='line-height:150%;'>Letras: <a href='https://lrclib.net' style='color:{ACC}; "
            f"text-decoration:none;'>lrclib.net</a><br>"
            f"Fontes: Google Fonts, licença SIL Open Font License</p>")
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
    def _set(self, key, value):
        self.cfg[key] = value
        if key == "autostart":
            import winutil
            winutil.set_autostart(bool(value))
        self.ctl.apply_config()
        self._update_visibility()
        self._save_timer.start()

    def _pick_color(self, key):
        c = QColorDialog.getColor(QColor(self.cfg[key]), self, "Escolha a cor")
        if c.isValid():
            self.fields[key][1].set_color(c.name())
            if key == "custom_colour":
                self.cfg["accent"] = "custom"
                self.refresh()
            self._set(key, c.name())

    def _apply_preset(self, name):
        self.cfg.update(_RESET_EXTRAS)
        self.cfg.update(PRESETS[name])
        self.refresh()
        self.ctl.apply_config()
        self.cfg.save()

    def _import_code(self):
        code = self.code_edit.text()
        self.code_btn.setEnabled(False)
        self._msg("Buscando o look…")

        def work():
            try:
                name, author, settings = looks.fetch_look(code)
                self._bridge.done.emit(True, f"\"{name}\"" + (f" de {author}" if author else ""), settings)
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
        self._msg(f"✓ Look {msg} aplicado. Coisas só do Minecraft (3D, PvP) ficam de fora.")

    def _reset(self):
        keep = {k: self.cfg[k] for k in ("lyrics_x", "lyrics_y", "screen_index", "autostart", "auto_update")}
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
        self.ctl.demo = False
        if self.ctl.edit:
            self.ctl.set_edit(False)
        self.cfg.save()
        super().closeEvent(e)
