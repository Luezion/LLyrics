"""Configurações do overlay: valores padrão, paletas e salvar/carregar em JSON."""
import json
import os
import sys

APP_NAME = "LLyrics"
OLD_APP_NAME = "LyricsOverlay"


def data_dir():
    base = os.environ.get("APPDATA") or os.path.join(os.path.expanduser("~"), ".config")
    path = os.path.join(base, APP_NAME)
    old = os.path.join(base, OLD_APP_NAME)
    if not os.path.exists(path) and os.path.isdir(old):
        try:  # leva as configurações do nome antigo do app
            import shutil
            shutil.copytree(old, path)
        except OSError:
            pass
    os.makedirs(path, exist_ok=True)
    return path


def resource_path(*parts):
    """Caminho de arquivos que vão junto com o app (funciona no .exe do PyInstaller)."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *parts)


CONFIG_FILE = os.path.join(data_dir(), "config.json")

# Paleta de cores de destaque (nomes iguais aos do mod, valores próprios)
ACCENTS = {
    "cream": "#FFF1D0",
    "honey": "#FFC857",
    "blush": "#FFB3C8",
    "coral": "#FF7F6E",
    "mint": "#8DF2C4",
    "ice": "#A9E4FF",
    "lavender": "#C4B3FF",
    "orchid": "#E38CF2",
    "sage": "#B8D4A6",
    "slate": "#A3B1C9",
}
RAINBOW = ["#FF7F6E", "#FFC857", "#FFF1D0", "#8DF2C4", "#A9E4FF", "#C4B3FF", "#E38CF2", "#FFB3C8"]

ACCENT_CHOICES = [
    ("album", "Álbum (cor da capa)"),
    ("cream", "Creme"), ("honey", "Mel"), ("blush", "Rosado"), ("coral", "Coral"),
    ("mint", "Menta"), ("ice", "Gelo"), ("lavender", "Lavanda"), ("orchid", "Orquídea"),
    ("sage", "Sálvia"), ("slate", "Ardósia"),
    ("rainbow", "Arco-íris"), ("custom", "Personalizada"),
]

ANIMATIONS = [
    ("typewriter", "Máquina de escrever"),
    ("drop", "Queda"),
    ("rise", "Subida"),
    ("words", "Palavras"),
    ("fade", "Esmaecer"),
    ("pop", "Pop"),
    ("wave", "Onda"),
    ("wave_down", "Onda para baixo"),
]

# (chave, nome exibido, arquivos) — arquivos ficam na pasta fonts/
FONTS = [
    ("pixelify", "Pixelify Sans (estilo Minecraft)", ["PixelifySans.ttf"]),
    ("bebas", "Bebas Neue", ["BebasNeue-Regular.ttf"]),
    ("poppins", "Poppins", ["Poppins-Regular.ttf", "Poppins-Bold.ttf"]),
    ("montserrat", "Montserrat", ["Montserrat.ttf"]),
    ("righteous", "Righteous", ["Righteous-Regular.ttf"]),
    ("pacifico", "Pacifico", ["Pacifico-Regular.ttf"]),
    ("lobster", "Lobster", ["Lobster-Regular.ttf"]),
    ("playfair", "Playfair Display", ["PlayfairDisplay.ttf"]),
    ("eagle_lake", "Eagle Lake", ["EagleLake-Regular.ttf"]),
    ("comic_relief", "Comic Relief", ["ComicRelief-Regular.ttf", "ComicRelief-Bold.ttf"]),
    ("press_start", "Press Start 2P (pixel)", ["PressStart2P-Regular.ttf"]),
    ("system", "Segoe UI (sistema)", []),
]

LAYOUTS = [
    ("lines", "Linhas (normal)"),
    ("stack", "Pilha (palavras grandes e pequenas)"),
    ("words", "Primeira palavra em destaque"),
    ("words_tilted", "Primeira palavra em destaque + palavras inclinadas"),
]

EXITS = [
    ("auto", "Igual à entrada"),
    ("fade", "Esmaecer"),
    ("drift", "Levada pelo vento"),
]

COLOUR_MODES = [
    ("solid", "Uma cor"),
    ("gradient", "Degradê (duas cores)"),
    ("gradient3", "Degradê (três cores)"),
    ("rainbow_flow", "Arco-íris correndo"),
]

IDLES = [
    ("none", "Nenhum"),
    ("shake", "Tremer"),
    ("wave", "Onda"),
    ("bounce", "Pulinho"),
    ("pulse", "Pulsar"),
    ("float", "Flutuar"),
    ("sway", "Balançar"),
]

PARTY_EFFECTS = [
    ("both", "Notas e brilhos"),
    ("notes", "Só notas"),
    ("sparkles", "Só brilhos"),
]

POSITION_MODES = [
    ("fixed", "Fixa (onde eu arrastar)"),
    ("random", "Aleatória a cada linha"),
]

WIDGET_POSITIONS = [
    ("top_left", "Superior esquerdo"),
    ("top_right", "Superior direito"),
    ("bottom_left", "Inferior esquerdo"),
    ("bottom_right", "Inferior direito"),
    ("custom", "Onde eu arrastar"),
]

DEFAULTS = {
    # Geral
    "show_lyrics": True,
    "hide_paused": True,
    "sync_offset": 0.0,          # segundos (+ adianta a letra)
    "fps": 60,
    # Letras / animação
    "animation": "typewriter",
    "exit_animation": "auto",
    "typewriter_sync": True,
    "typewriter_speed": 1.0,
    "karaoke": True,
    "countdown": True,
    "preview": False,
    "previous_line": True,
    # Layout e movimento
    "layout": "lines",
    "idle": "none",
    "idle_speed": 1.0,
    "idle_strength": 1.0,
    "sparkle": False,
    "sparkle_amount": 1.0,
    "party": False,
    "party_effects": "both",
    # Estilo do texto
    "accent": "album",
    "colour_mode": "solid",
    "second_colour": "#DB9BE0",
    "third_colour": "#8FC9F2",
    "custom_colour": "#FF5C8A",
    "font": "bebas",
    "bold": False,
    "uppercase": True,
    "text_size": 46,             # px
    "letter_spacing": 1.0,       # px
    "line_spacing": 4,           # px
    "line_width": 900,           # px antes de quebrar
    "outline": True,
    "outline_colour": "#000000",
    "outline_thickness": 1.0,
    "drop_shadow": True,
    "glow": True,
    "background": False,
    "lyrics_opacity": 1.0,
    "position_mode": "fixed",    # fixed | random
    "allow_center": True,        # a letra pode aparecer no meio da tela?
    "center_zone": 0.35,         # tamanho da área livre no centro (fração da altura da tela)
    "lyrics_x": 0.5,             # centro da letra (fração da tela)
    "lyrics_y": 0.78,
    # Widget
    "show_widget": True,
    "widget_position": "top_right",
    "widget_x": 0.8,
    "widget_y": 0.05,
    "widget_scale": 1.0,
    "widget_opacity": 0.9,
    # Monitor
    "screen_index": 0,
    # Atualizações
    "auto_update": True,
    "skip_version": "",
}


class Config(dict):
    def __init__(self):
        super().__init__(DEFAULTS)
        self.load()

    def load(self):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            for k, v in data.items():
                if k in DEFAULTS:
                    self[k] = v
        except (OSError, ValueError):
            pass

    def save(self):
        try:
            tmp = CONFIG_FILE + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(dict(self), f, indent=2, ensure_ascii=False)
            os.replace(tmp, CONFIG_FILE)
        except OSError:
            pass

    def reset(self):
        self.clear()
        self.update(DEFAULTS)
