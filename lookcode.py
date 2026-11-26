"""Códigos de estilo do LLyrics ("LLY1-...").

Um código guarda só as opções de aparência (cores, fonte, animações, efeitos), nunca
posição na tela, atalhos, idioma ou outras coisas pessoais. Não depende do Qt, então
também roda no GitHub Actions para validar os estilos enviados para a comunidade.
"""
import base64
import json
import re
import zlib

from config import (ACCENT_CHOICES, ANIMATIONS, COLOUR_MODES, DEFAULTS, EXITS, FONTS, IDLES, LAYOUTS,
                    PARTY_EFFECTS)

PREFIX = "LLY1-"

STYLE_KEYS = [
    "layout", "animation", "exit_animation", "typewriter_sync", "typewriter_speed", "karaoke", "countdown",
    "preview", "previous_line", "idle", "idle_speed", "idle_strength", "sparkle", "sparkle_amount", "party",
    "party_effects", "accent", "colour_mode", "custom_colour", "second_colour", "third_colour", "font", "bold",
    "uppercase", "text_size", "letter_spacing", "line_spacing", "line_width", "outline", "outline_colour",
    "outline_thickness", "drop_shadow", "glow", "background", "lyrics_opacity",
]

_CHOICES = {
    "layout": LAYOUTS, "animation": ANIMATIONS, "exit_animation": EXITS, "idle": IDLES,
    "party_effects": PARTY_EFFECTS, "accent": ACCENT_CHOICES, "colour_mode": COLOUR_MODES,
    "font": [(k, n) for k, n, _ in FONTS],
}
_RANGES = {
    "typewriter_speed": (0.2, 5), "idle_speed": (0.05, 5), "idle_strength": (0.05, 5),
    "sparkle_amount": (0.5, 4), "text_size": (12, 160), "letter_spacing": (-5, 20), "line_spacing": (0, 60),
    "line_width": (200, 2400), "outline_thickness": (0.1, 4), "lyrics_opacity": (0.1, 1),
}
_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


def style_of(cfg):
    return {k: cfg[k] for k in STYLE_KEYS if k in cfg}


def clean(data):
    """Só deixa passar chaves conhecidas com valores válidos."""
    out = {}
    if not isinstance(data, dict):
        return out
    for k, v in data.items():
        if k not in STYLE_KEYS:
            continue
        default = DEFAULTS[k]
        if k in _CHOICES:
            if v in [c for c, _ in _CHOICES[k]]:
                out[k] = v
        elif k.endswith("_colour"):
            if isinstance(v, str) and _HEX.match(v):
                out[k] = v.upper()
        elif isinstance(default, bool):
            if isinstance(v, bool):
                out[k] = v
        elif isinstance(default, (int, float)) and isinstance(v, (int, float)) and not isinstance(v, bool):
            lo, hi = _RANGES.get(k, (-1e9, 1e9))
            v = max(lo, min(hi, v))
            out[k] = int(round(v)) if isinstance(default, int) else float(v)
    return out


def encode(style):
    raw = json.dumps(clean(style), separators=(",", ":"), sort_keys=True).encode("utf-8")
    return PREFIX + base64.urlsafe_b64encode(zlib.compress(raw, 9)).decode("ascii").rstrip("=")


def find_code(text):
    m = re.search(r"LLY1-[A-Za-z0-9_\-]+", text or "")
    return m.group(0) if m else None


def decode(code):
    """Devolve o dicionário de estilo ou lança ValueError."""
    code = find_code(code)
    if not code:
        raise ValueError("not an LLyrics code")
    body = code[len(PREFIX):]
    try:
        raw = zlib.decompress(base64.urlsafe_b64decode(body + "=" * (-len(body) % 4)))
        data = json.loads(raw.decode("utf-8"))
    except (ValueError, zlib.error) as e:
        raise ValueError("broken LLyrics code") from e
    style = clean(data)
    if not style:
        raise ValueError("empty LLyrics code")
    return style
