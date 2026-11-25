"""Importa "looks" do site da comunidade do mod (lyrics.remake.lol) pelo código STL-XXXXXX.

Só as opções que este app tem são aplicadas; o resto (coisas do mundo 3D do Minecraft) é ignorado.
"""
import json
import re
import urllib.error
import urllib.request

SITE = "https://lyrics.remake.lol"

_FONTS = {
    "DEFAULT": "pixelify", "MONTSERRAT": "montserrat", "POPPINS": "poppins", "BEBAS": "bebas",
    "RIGHTEOUS": "righteous", "PLAYFAIR": "playfair", "LOBSTER": "lobster", "PACIFICO": "pacifico",
    "PRESS_START": "press_start", "COMIC_RELIEF": "comic_relief", "EAGLE_LAKE": "eagle_lake",
}
_ANIMS = {"TYPEWRITER", "FADE", "POP", "DROP", "RISE", "WAVE", "WORDS", "WAVE_DOWN"}
_IDLES = {"NONE", "SHAKE", "WAVE", "BOUNCE", "PULSE", "FLOAT", "SWAY"}
_ACCENTS = {"CREAM", "HONEY", "BLUSH", "CORAL", "MINT", "ICE", "LAVENDER", "ORCHID", "SAGE", "SLATE"}


def _hex(n, default):
    try:
        return "#%06X" % (int(n) & 0xFFFFFF)
    except (TypeError, ValueError):
        return default


def parse_code(text):
    t = (text or "").strip()
    for pat in (r"/p/([A-Za-z0-9]{6})\b", r"STL-([A-Za-z0-9]{6})\b", r"^([A-Za-z0-9]{6})$"):
        m = re.search(pat, t, re.I)
        if m:
            return m.group(1).upper()
    return None


def fetch_look(code):
    """Devolve (nome, autor, configurações já convertidas). Lança ValueError com mensagem amigável."""
    cid = parse_code(code)
    if not cid:
        raise ValueError("Código inválido. Ele é parecido com STL-JMQZYC.")
    req = urllib.request.Request(f"{SITE}/api/community/presets/{cid}",
                                 headers={"User-Agent": "LLyrics/1.0", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise ValueError("Não achei esse código no site.") from e
        raise ValueError(f"O site respondeu com erro ({e.code}). Tente de novo depois.") from e
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
        raise ValueError("Não consegui falar com o site. Confira sua internet.") from e
    return data.get("name") or cid, data.get("author") or "", convert(data.get("settings") or {})


def convert(s):
    out = {}
    accent = (s.get("accentColor") or "").upper()
    mode = (s.get("colorMode") or "SOLID").upper()
    if accent == "CUSTOM":
        out["accent"] = "custom"
        out["custom_colour"] = _hex(s.get("lyricsColorHex"), "#CDFFFA")
    elif accent == "ALBUM" or mode == "ALBUM":
        out["accent"] = "album"
    elif accent == "RAINBOW" or mode == "RAINBOW_LINES":
        out["accent"] = "rainbow"
    elif accent in _ACCENTS:
        out["accent"] = accent.lower()
    out["colour_mode"] = {"GRADIENT": "gradient", "RAINBOW_FLOW": "rainbow_flow"}.get(mode, "solid")
    if "secondColorHex" in s:
        out["second_colour"] = _hex(s.get("secondColorHex"), "#DB9BE0")

    anim = (s.get("appearAnimation") or "").upper()
    if anim in _ANIMS:
        out["animation"] = anim.lower()
    idle = (s.get("idleAnimation") or "NONE").upper()
    out["idle"] = idle.lower() if idle in _IDLES else "none"
    for src, dst in (("idleSpeed", "idle_speed"), ("idleStrength", "idle_strength")):
        if isinstance(s.get(src), (int, float)):
            out[dst] = float(s[src])
    layout = (s.get("layoutMode") or "LINES").upper()
    out["layout"] = {"STACK": "stack", "SCATTER": "stack", "WORDS": "words",
                     "WORDS_TILTED": "words_tilted"}.get(layout, "lines")
    leave = (s.get("disappearAnimation") or "").upper()
    out["exit_animation"] = {"DRIFT": "drift", "FADE": "fade"}.get(leave, "auto")

    font = (s.get("lyricsFont") or "DEFAULT").upper()
    out["font"] = _FONTS.get(font, "pixelify")
    for src, dst in (("boldActiveLyric", "bold"), ("lyricsUppercase", "uppercase"),
                     ("lyricsDropShadow", "drop_shadow"), ("activeLineHighlight", "karaoke"),
                     ("typewriterSync", "typewriter_sync"), ("showPreviousLine", "previous_line"),
                     ("textSparkle", "sparkle"), ("partyMode", "party")):
        if isinstance(s.get(src), bool):
            out[dst] = s[src]
    if isinstance(s.get("typewriterSpeed"), (int, float)):
        out["typewriter_speed"] = float(s["typewriterSpeed"])
    if isinstance(s.get("sparkleAmount"), (int, float)):
        out["sparkle_amount"] = float(s["sparkleAmount"])
    pe = (s.get("partyEffects") or "BOTH").upper()
    out["party_effects"] = {"NOTES": "notes", "SPARKLES": "sparkles"}.get(pe, "both")

    out["outline"] = bool(s.get("lyricsGlowEffect"))  # no mod, "contorno" usa esta chave
    if "lyricsOutlineColorHex" in s:
        out["outline_colour"] = _hex(s.get("lyricsOutlineColorHex"), "#000000")
    if isinstance(s.get("outlineThickness"), (int, float)):
        out["outline_thickness"] = float(s["outlineThickness"])
    out["glow"] = (s.get("glowMode") or "OFF").upper() != "OFF"
    if out["outline"]:
        out["drop_shadow"] = False  # no mod, contorno e sombra não andam juntos
    out["background"] = float(s.get("lyricsBgAlpha") or 0) > 0.01
    if isinstance(s.get("letterSpacing"), (int, float)):
        out["letter_spacing"] = float(s["letterSpacing"]) * 2
    if isinstance(s.get("lyricsFontScale"), (int, float)):
        k = max(0.8, min(1.4, float(s["lyricsFontScale"]) / 1.25))
        out["text_size"] = int(round(40 * k))
    return out


# O look "Shake" (STL-JMQZYC), já convertido, para funcionar sem internet.
SHAKE = convert({
    "accentColor": "CUSTOM", "activeLineHighlight": False, "appearAnimation": "FADE", "boldActiveLyric": True,
    "colorMode": "GRADIENT", "glowMode": "OFF", "idleAnimation": "SHAKE", "idleSpeed": 0.25, "idleStrength": 0.5,
    "layoutMode": "STACK", "letterSpacing": 0.0, "lyricsBgAlpha": 0.0, "lyricsColorHex": 16728428,
    "lyricsDropShadow": True, "lyricsFont": "DEFAULT", "lyricsFontScale": 2.0, "lyricsGlowEffect": False,
    "lyricsOutlineColorHex": 14392288, "lyricsUppercase": True, "outlineThickness": 1.0, "partyEffects": "BOTH",
    "partyMode": True, "secondColorHex": 16730923, "showPreviousLine": False, "sparkleAmount": 0.5,
    "textSparkle": True, "typewriterSpeed": 1.25, "typewriterSync": True,
})


# O look "Void Echoes" (STL-TQ4D7K), de Trickbound.
VOID_ECHOES = convert({
    "accentColor": "CUSTOM", "activeLineHighlight": True, "appearAnimation": "TYPEWRITER", "boldActiveLyric": True,
    "colorFlowSpeed": 1, "colorMode": "SOLID", "disappearAnimation": "DRIFT", "glowColor": "MATCH",
    "glowMode": "SOFT", "idleAnimation": "FLOAT", "idleSpeed": 0.75, "idleStrength": 0.25,
    "layoutMode": "WORDS_TILTED", "letterSpacing": 0.5, "lineSpacing": 0.5, "lyricsBgAlpha": 0,
    "lyricsColorHex": 12327930, "lyricsDropShadow": False, "lyricsFont": "DEFAULT", "lyricsFontScale": 1.5,
    "lyricsGlowEffect": True, "lyricsOutlineColorHex": 1052692, "lyricsUppercase": False, "outlineThickness": 1,
    "partyEffects": "BOTH", "partyMode": True, "secondColorHex": 14879223, "textSparkle": True,
    "typewriterSpeed": 1.25, "typewriterSync": True,
})
