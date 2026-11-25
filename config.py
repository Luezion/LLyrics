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

# Listas de escolhas: (valor, chave de tradução em i18n.py)
ACCENT_CHOICES = [(k, f"accent.{k}") for k in (
    "album", "cream", "honey", "blush", "coral", "mint", "ice", "lavender", "orchid", "sage", "slate",
    "rainbow", "custom")]

ANIMATIONS = [(k, f"anim.{k}") for k in ("typewriter", "drop", "rise", "words", "fade", "pop", "wave", "wave_down")]

# (chave, nome exibido ou chave de tradução, arquivos) — arquivos ficam na pasta fonts/
FONTS = [
    ("pixelify", "font.pixelify", ["PixelifySans.ttf"]),
    ("bebas", "Bebas Neue", ["BebasNeue-Regular.ttf"]),
    ("poppins", "Poppins", ["Poppins-Regular.ttf", "Poppins-Bold.ttf"]),
    ("montserrat", "Montserrat", ["Montserrat.ttf"]),
    ("righteous", "Righteous", ["Righteous-Regular.ttf"]),
    ("pacifico", "Pacifico", ["Pacifico-Regular.ttf"]),
    ("lobster", "Lobster", ["Lobster-Regular.ttf"]),
    ("playfair", "Playfair Display", ["PlayfairDisplay.ttf"]),
    ("eagle_lake", "Eagle Lake", ["EagleLake-Regular.ttf"]),
    ("comic_relief", "Comic Relief", ["ComicRelief-Regular.ttf", "ComicRelief-Bold.ttf"]),
    ("press_start", "Press Start 2P", ["PressStart2P-Regular.ttf"]),
    ("system", "font.system", []),
]

LAYOUTS = [(k, f"layout.{k}") for k in ("lines", "stack", "words", "words_tilted")]
EXITS = [(k, f"exit.{k}") for k in ("auto", "fade", "drift")]
COLOUR_MODES = [(k, f"colour.{k}") for k in ("solid", "gradient", "gradient3", "rainbow_flow")]
IDLES = [(k, f"idle.{k}") for k in ("none", "shake", "wave", "bounce", "pulse", "float", "sway")]
PARTY_EFFECTS = [(k, f"party.{k}") for k in ("both", "notes", "sparkles")]
POSITION_MODES = [(k, f"posmode.{k}") for k in ("fixed", "random")]
WIDGET_POSITIONS = [(k, f"wpos.{k}") for k in ("top_left", "top_right", "bottom_left", "bottom_right", "custom")]

HOTKEY_DEFAULTS = {
    "hotkey_toggle": "Ctrl+Shift+L",
    "hotkey_move": "Ctrl+Shift+K",
    "hotkey_settings": "Ctrl+Shift+O",
}

DEFAULTS = {
    "language": "en",
    **HOTKEY_DEFAULTS,
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
    "autostart": False,
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
