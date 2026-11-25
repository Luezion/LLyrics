"""Janela de configurações (as mudanças aparecem no overlay na hora)."""
import threading

from PySide6.QtCore import QObject, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QGuiApplication
from PySide6.QtWidgets import (QCheckBox, QColorDialog, QComboBox, QFormLayout, QHBoxLayout,
                               QLabel, QLineEdit, QPushButton, QScrollArea, QSlider, QTabWidget, QVBoxLayout, QWidget)

import looks
from version import __version__
from config import (ACCENT_CHOICES, ANIMATIONS, COLOUR_MODES, EXITS, FONTS, IDLES, LAYOUTS, PARTY_EFFECTS,
                    POSITION_MODES, WIDGET_POSITIONS)

_RESET_EXTRAS = dict(layout="lines", idle="none", colour_mode="solid", sparkle=False, party=False,
                     exit_animation="auto", letter_spacing=1.0, line_spacing=4)

PRESETS = {
    "Shake (pilha, do site)": looks.SHAKE,
    "Void Echoes (do site)": looks.VOID_ECHOES,
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

STYLE = """
QWidget { background: #141419; color: #ECECF1; font-family: 'Segoe UI'; font-size: 13px; }
QTabWidget::pane { border: 1px solid #2A2A33; border-radius: 10px; top: -1px; }
QTabBar::tab { background: #1C1C23; padding: 8px 16px; border-top-left-radius: 8px;
               border-top-right-radius: 8px; margin-right: 2px; color: #A8A8B5; }
QTabBar::tab:selected { background: #26262F; color: white; }
QComboBox, QPushButton, QLineEdit { background: #22222A; border: 1px solid #33333D; border-radius: 7px; padding: 5px 10px; }
QPushButton:hover, QComboBox:hover { border-color: ACCENT; }
QCheckBox::indicator { width: 18px; height: 18px; border-radius: 5px; border: 1px solid #44444F; background: #22222A; }
QCheckBox::indicator:checked { background: ACCENT; border-color: ACCENT; }
QSlider::groove:horizontal { height: 4px; background: #33333D; border-radius: 2px; }
QSlider::sub-page:horizontal { background: ACCENT; border-radius: 2px; }
QSlider::handle:horizontal { background: white; width: 14px; height: 14px; margin: -5px 0; border-radius: 7px; }
QLabel#hint { color: #8E8E9C; font-size: 12px; }
QLabel#title { font-size: 18px; font-weight: 600; }
"""


class _Bridge(QObject):
    done = Signal(bool, str, object)


class SettingsWindow(QWidget):
    def __init__(self, ctl):
        super().__init__(None, Qt.Window)
        self.ctl = ctl
        self.cfg = ctl.cfg
        self.setWindowTitle("LLyrics — configurações")
        self.resize(520, 640)
        self.setStyleSheet(STYLE.replace("ACCENT", "#C4B3FF"))
        self.fields = {}
        self._save_timer = QTimer(self, singleShot=True, interval=400)
        self._save_timer.timeout.connect(self.cfg.save)
        ctl.config_changed_externally = self.refresh

        root = QVBoxLayout(self)
        root.setContentsMargins(18, 16, 18, 16)
        t = QLabel("LLyrics")
        t.setObjectName("title")
        root.addWidget(t)
        h = QLabel("Ctrl+Shift+L mostra/esconde  ·  Ctrl+Shift+K move as janelas  ·  Ctrl+Shift+O abre aqui")
        h.setObjectName("hint")
        h.setWordWrap(True)
        root.addWidget(h)

        tabs = QTabWidget()
        root.addWidget(tabs, 1)
        screens = [(i, f"Monitor {i + 1} ({s.size().width()}x{s.size().height()})")
                   for i, s in enumerate(QGuiApplication.screens())]

        tabs.addTab(self._page([
            ("show_lyrics", "Mostrar letras", "bool"),
            ("show_widget", "Mostrar widget do player", "bool"),
            ("hide_paused", "Ocultar quando pausado", "bool"),
            ("position_mode", "Posição da letra", ("choice", POSITION_MODES)),
            ("allow_center", "Pode aparecer no centro da tela", "bool"),
            ("center_zone", "Tamanho da área livre no centro", ("slider", 0.15, 0.7, 0.01, "")),
            ("sync_offset", "Ajuste de sincronia", ("slider", -3.0, 3.0, 0.05, "s")),
            ("screen_index", "Monitor", ("choice", screens)),
            ("fps", "Quadros por segundo", ("choice", [(30, "30"), (60, "60"), (120, "120"), (144, "144")])),
            ("auto_update", "Procurar atualizações sozinho", "bool"),
        ], "Aleatória: cada linha nova aparece num lugar diferente da tela.\n"
           "Desligue \"Pode aparecer no centro\" em jogos de tiro para a letra nunca cobrir a mira "
           "(a área livre aumenta ou diminui no controle acima).\n"
           "Ajuste de sincronia: aumente se as palavras chegam depois de você ouvir."), "Geral")

        tabs.addTab(self._page([
            ("layout", "Layout", ("choice", LAYOUTS)),
            ("animation", "Entrada", ("choice", ANIMATIONS)),
            ("exit_animation", "Saída", ("choice", EXITS)),
            ("typewriter_sync", "Digitar no ritmo da música", "bool"),
            ("typewriter_speed", "Velocidade da digitação", ("slider", 0.3, 3.0, 0.1, "x")),
            ("karaoke", "Destaque de karaokê", "bool"),
            ("countdown", "Contagem instrumental", "bool"),
            ("previous_line", "Linha anterior", "bool"),
            ("preview", "Prévia da próxima linha", "bool"),
            ("idle", "Movimento parado", ("choice", IDLES)),
            ("idle_speed", "Velocidade do movimento", ("slider", 0.1, 3.0, 0.05, "x")),
            ("idle_strength", "Força do movimento", ("slider", 0.1, 3.0, 0.05, "x")),
            ("sparkle", "Brilhinhos na letra", "bool"),
            ("sparkle_amount", "Quantidade de brilhinhos", ("slider", 0.5, 4.0, 0.25, "x")),
            ("party", "Modo festa (notas subindo)", "bool"),
            ("party_effects", "Efeitos da festa", ("choice", PARTY_EFFECTS)),
        ], "Pilha: as palavras aparecem uma de cada vez, as pequenas (de, que, the…) menores e as "
           "importantes maiores. Na pilha, linha anterior e prévia ficam desligadas."), "Animação")

        style_page = self._page([
            ("accent", "Cor de destaque", ("choice", ACCENT_CHOICES)),
            ("custom_colour", "Cor personalizada", "color"),
            ("colour_mode", "Modo de cor", ("choice", COLOUR_MODES)),
            ("second_colour", "Segunda cor (degradê)", "color"),
            ("third_colour", "Terceira cor (degradê de 3)", "color"),
            ("font", "Fonte", ("choice", [(k, n) for k, n, _ in FONTS])),
            ("bold", "Negrito", "bool"),
            ("uppercase", "Maiúsculas", "bool"),
            ("text_size", "Tamanho do texto", ("slider", 16, 120, 1, "px")),
            ("letter_spacing", "Espaço entre letras", ("slider", -3.0, 12.0, 0.5, "px")),
            ("line_spacing", "Espaço entre linhas", ("slider", 0, 40, 1, "px")),
            ("line_width", "Largura da linha", ("slider", 300, 1800, 10, "px")),
            ("outline", "Contorno", "bool"),
            ("outline_colour", "Cor do contorno", "color"),
            ("outline_thickness", "Espessura do contorno", ("slider", 0.3, 2.5, 0.05, "x")),
            ("drop_shadow", "Sombra", "bool"),
            ("glow", "Brilho", "bool"),
            ("background", "Fundo atrás do texto", "bool"),
            ("lyrics_opacity", "Opacidade da letra", ("slider", 0.15, 1.0, 0.05, "")),
        ])
        preset_row = QHBoxLayout()
        preset = QComboBox()
        preset.addItem("Estilos prontos…")
        for name in PRESETS:
            preset.addItem(name)
        preset.activated.connect(lambda i: self._apply_preset(preset.itemText(i)) if i > 0 else None)
        preset_row.addWidget(preset)
        style_page.inner_layout.insertLayout(0, preset_row)
        imp_row = QHBoxLayout()
        self.code_edit = QLineEdit()
        self.code_edit.setPlaceholderText("Código do site do mod (ex.: STL-JMQZYC)")
        self.code_btn = QPushButton("Importar")
        self.code_btn.clicked.connect(self._import_code)
        self.code_edit.returnPressed.connect(self._import_code)
        imp_row.addWidget(self.code_edit, 1)
        imp_row.addWidget(self.code_btn)
        style_page.inner_layout.insertLayout(1, imp_row)
        self.import_msg = QLabel("")
        self.import_msg.setObjectName("hint")
        self.import_msg.setWordWrap(True)
        style_page.inner_layout.insertWidget(2, self.import_msg)
        self._bridge = _Bridge()
        self._bridge.done.connect(self._import_done)
        tabs.addTab(style_page, "Estilo")

        tabs.addTab(self._page([
            ("widget_position", "Posição", ("choice", WIDGET_POSITIONS)),
            ("widget_scale", "Tamanho do widget", ("slider", 0.6, 2.0, 0.05, "x")),
            ("widget_opacity", "Opacidade do widget", ("slider", 0.2, 1.0, 0.05, "")),
        ], "Dica: use Ctrl+Shift+K para arrastar a letra e o widget para onde quiser."), "Widget")

        btns = QHBoxLayout()
        upd = QPushButton(f"Atualizações (v{__version__})")
        upd.clicked.connect(lambda: getattr(ctl, "updater", None) and ctl.updater.check(manual=True))
        btns.addWidget(upd)
        move = QPushButton("Mover janelas")
        move.clicked.connect(ctl.toggle_edit)
        reset = QPushButton("Restaurar padrão")
        reset.clicked.connect(self._reset)
        close = QPushButton("Fechar")
        close.clicked.connect(self.close)
        btns.addWidget(move)
        btns.addWidget(reset)
        btns.addStretch(1)
        btns.addWidget(close)
        root.addLayout(btns)

    # ------------------------------------------------------------ construção
    def _page(self, items, hint=None):
        inner = QWidget()
        v = QVBoxLayout(inner)
        page = QScrollArea()
        page.setWidgetResizable(True)
        page.setFrameShape(QScrollArea.NoFrame)
        page.setWidget(inner)
        page.inner_layout = v
        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft)
        form.setVerticalSpacing(9)
        for key, label, kind in items:
            form.addRow(label, self._field(key, kind))
        v.addLayout(form)
        if hint:
            lb = QLabel(hint)
            lb.setObjectName("hint")
            lb.setWordWrap(True)
            v.addWidget(lb)
        v.addStretch(1)
        return page

    def _field(self, key, kind):
        cfg = self.cfg
        if kind == "bool":
            w = QCheckBox()
            w.setChecked(bool(cfg[key]))
            w.toggled.connect(lambda v, k=key: self._set(k, bool(v)))
            self.fields[key] = ("bool", w)
            return w
        if kind == "color":
            w = QPushButton()
            w.clicked.connect(lambda _=False, k=key: self._pick_color(k))
            self.fields[key] = ("color", w)
            self._paint_color_btn(w, cfg[key])
            return w
        if kind[0] == "choice":
            w = QComboBox()
            values = [v for v, _ in kind[1]]
            for v, name in kind[1]:
                w.addItem(name, v)
            if cfg[key] in values:
                w.setCurrentIndex(values.index(cfg[key]))
            w.currentIndexChanged.connect(lambda i, k=key, cb=w: self._set(k, cb.itemData(i)))
            self.fields[key] = ("choice", w)
            return w
        _, lo, hi, step, unit = kind
        box = QWidget()
        h = QHBoxLayout(box)
        h.setContentsMargins(0, 0, 0, 0)
        s = QSlider(Qt.Horizontal)
        s.setRange(0, int(round((hi - lo) / step)))
        lab = QLabel()
        lab.setMinimumWidth(58)
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

    # ------------------------------------------------------------ ações
    def _set(self, key, value):
        self.cfg[key] = value
        self.ctl.apply_config()
        self._save_timer.start()

    def _pick_color(self, key):
        c = QColorDialog.getColor(QColor(self.cfg[key]), self, "Escolha a cor")
        if c.isValid():
            self._paint_color_btn(self.fields[key][1], c.name())
            if key == "custom_colour":
                self.cfg["accent"] = "custom"
                self.refresh()
            self._set(key, c.name())

    @staticmethod
    def _paint_color_btn(btn, hexcol):
        btn.setText(hexcol.upper())
        txt = "#000" if QColor(hexcol).lightness() > 140 else "#fff"
        btn.setStyleSheet(f"background:{hexcol}; color:{txt}; border-radius:7px; padding:5px 10px;")

    def _apply_preset(self, name):
        self.cfg.update(_RESET_EXTRAS)
        self.cfg.update(PRESETS[name])
        self.refresh()
        self.ctl.apply_config()
        self.cfg.save()

    def _import_code(self):
        code = self.code_edit.text()
        self.code_btn.setEnabled(False)
        self.import_msg.setText("Buscando o look…")

        def work():
            try:
                name, author, settings = looks.fetch_look(code)
                self._bridge.done.emit(True, f"{name}" + (f" de {author}" if author else ""), settings)
            except ValueError as e:
                self._bridge.done.emit(False, str(e), {})

        threading.Thread(target=work, daemon=True).start()

    def _import_done(self, ok, msg, settings):
        self.code_btn.setEnabled(True)
        if not ok:
            self.import_msg.setText(msg)
            return
        self.cfg.update(_RESET_EXTRAS)
        self.cfg.update(settings)
        self.refresh()
        self.ctl.apply_config()
        self.cfg.save()
        self.import_msg.setText(f"Look aplicado: {msg}. (Coisas só do Minecraft, como 3D e PvP, ficam de fora.)")

    def _reset(self):
        keep = {k: self.cfg[k] for k in ("lyrics_x", "lyrics_y", "screen_index")}
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
                self._paint_color_btn(w, self.cfg[key])
            elif kind == "choice":
                i = w.findData(self.cfg[key])
                if i >= 0:
                    w.setCurrentIndex(i)
            else:
                _, sl, lo, step, show = f
                sl.setValue(int(round((float(self.cfg[key]) - lo) / step)))
                show(sl.value())
            w.blockSignals(False)

    def showEvent(self, e):
        super().showEvent(e)
        self.ctl.demo = True

    def closeEvent(self, e):
        self.ctl.demo = False
        if self.ctl.edit:
            self.ctl.set_edit(False)
        self.cfg.save()
        super().closeEvent(e)
