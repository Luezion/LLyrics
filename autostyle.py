"""Estilo automático: cria um visual próprio para a música que está tocando.

Pistas usadas (tudo local, sem IA paga):
- ritmo da letra (palavras por segundo, tamanho das linhas, pausas)
- palavras da letra (amor, tristeza, festa, peso, fé) em inglês, espanhol e português
- gênero do artista no MusicBrainz (banco aberto e gratuito), guardado no PC
- cores da capa do álbum

O resultado é sempre o mesmo para a mesma música.
"""
import hashlib
import json
import os
import random
import re
import time
import unicodedata
import urllib.parse
import urllib.request

from config import data_dir
from version import UPDATE_REPO, __version__

# ------------------------------------------------------------------ palavras
_LEX = {
    "love": """love lover loving kiss kisses baby babe darling heart hearts honey sweetheart forever hold
               amor amo amar ama beijo beijos coracao paixao querida querido namorada namorado carinho abraco
               apaixonado linda lindo te quiero corazon besos beso enamorado cariño mi vida amarte""",
    "sad": """cry crying tears tear alone lonely goodbye pain broken hurt miss missing lost cold empty sorrow
              die dying grave rain sad
              chorar choro lagrima lagrimas sozinho sozinha adeus dor saudade triste perdido vazio frio
              solidao partiu machuca sofrer
              llorar lloro lagrima solo sola adios dolor triste perdido vacio frio extraño sufrir""",
    "party": """dance dancing party night tonight club drink drinks shake move floor weekend wild fun jump
                lights dj bass loud
                danca dancar festa balada noite hoje bebida beber rebola rebolar pista sextou paredao
                fiesta bailar baila noche perreo discoteca trago gozar""",
    "heavy": """fight fire hate war burn rage scream blood devil hell kill enemy break chaos riot storm
                guerra fogo odio raiva luta lutar grito sangue inferno demonio quebrar caos briga
                fuego odio rabia pelea guerra grito sangre infierno diablo romper caos""",
    "faith": """god lord heaven light sky angel pray grace hope soul spirit
                deus senhor ceu luz anjo orar fe esperanca alma espirito gloria
                dios señor cielo luz angel orar fe esperanza alma espiritu""",
}


def _norm(word):
    w = unicodedata.normalize("NFD", word.lower())
    return "".join(c for c in w if unicodedata.category(c) != "Mn")


LEXICON = {k: {_norm(w) for w in v.split()} for k, v in _LEX.items()}


def lyric_mood(lines):
    words = [_norm(w) for ln in lines for w in re.findall(r"[\w']+", ln.text)]
    n = max(1, len(words))
    scores = {k: sum(1 for w in words if w in lex) / n for k, lex in LEXICON.items()}
    best = max(scores, key=scores.get) if words else None
    if best and scores[best] < 0.012:
        best = None
    return best, scores


def lyric_energy(lines):
    """0 (lenta) a 1 (agitada), pelo ritmo das palavras."""
    rates = []
    for i, ln in enumerate(lines):
        nxt = lines[i + 1].time if i + 1 < len(lines) else None
        end = ln.end if ln.end is not None else nxt
        if end is None:
            continue
        dur = max(0.6, min(12.0, end - ln.time))
        rates.append(len(ln.text.split()) / dur)
    if not rates:
        return 0.5
    rates.sort()
    med = rates[len(rates) // 2]
    return max(0.0, min(1.0, (med - 1.1) / 2.4))


# ------------------------------------------------------------------ gênero (MusicBrainz)
_FAMILIES = [
    ("rock", "metal rock punk grunge hardcore emo alternative indie metalcore screamo post-hardcore nu"),
    ("rap", "hip hop hip-hop rap trap drill grime boom bap funk carioca phonk"),
    ("electronic", "electronic edm house techno trance dubstep drum and bass dance electro synthwave "
                   "eurodance hardstyle electropop"),
    ("latin", "reggaeton latin latino urbano salsa bachata cumbia dembow"),
    ("brazil", "sertanejo pagode samba forro forró mpb bossa nova axe axé arrocha brega piseiro"),
    ("rnb", "r&b rnb soul neo soul funk"),
    ("acoustic", "folk acoustic country singer-songwriter gospel worship christian"),
    ("classic", "jazz classical blues orchestral opera swing"),
    ("pop", "pop k-pop kpop j-pop synthpop dance-pop teen pop"),
]

_GENRE_CACHE = os.path.join(data_dir(), "genres.json")
_last_request = [0.0]


def _load_cache():
    try:
        with open(_GENRE_CACHE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def family_from_tags(tags):
    text = " " + " ".join(t.lower() for t in tags) + " "
    best, best_score = None, 0
    for fam, words in _FAMILIES:
        score = sum(text.count(" " + w + " ") + text.count(" " + w + "-") for w in words.split())
        score += sum(1 for w in words.split() if w in text) * 0.1
        if score > best_score:
            best, best_score = fam, score
    return best


def artist_family(artist):
    """Família de gênero do artista ('rock', 'rap'…) ou None. Usa cache; no máximo 1 pedido/seg."""
    key = _norm(artist or "").strip()
    if not key:
        return None
    cache = _load_cache()
    if key in cache:
        return cache[key] or None
    wait = 1.1 - (time.time() - _last_request[0])
    if wait > 0:
        time.sleep(wait)
    _last_request[0] = time.time()
    q = urllib.parse.quote(f'artist:"{artist}"')
    url = f"https://musicbrainz.org/ws/2/artist/?query={q}&fmt=json&limit=1"
    req = urllib.request.Request(url, headers={
        "User-Agent": f"LLyrics/{__version__} ( https://github.com/{UPDATE_REPO} )",
        "Accept": "application/json"})
    fam = None
    try:
        with urllib.request.urlopen(req, timeout=8) as r:
            data = json.loads(r.read().decode("utf-8"))
        artists = data.get("artists") or []
        if artists and int(artists[0].get("score", 0)) >= 85:
            tags = [t.get("name", "") for t in (artists[0].get("tags") or [])]
            tags += [g.get("name", "") for g in (artists[0].get("genres") or [])]
            fam = family_from_tags(tags)
    except (OSError, ValueError):
        return None  # sem internet: não guarda, tenta de novo outra hora
    cache[key] = fam or ""
    try:
        with open(_GENRE_CACHE, "w", encoding="utf-8") as f:
            json.dump(cache, f, ensure_ascii=False)
    except OSError:
        pass
    return fam


# ------------------------------------------------------------------ cores da capa
def cover_palette(image_bytes):
    """Até 3 cores marcantes da capa (já clareadas para ler bem) e se a capa é escura."""
    if not image_bytes:
        return [], False
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QColor, QImage
    img = QImage()
    if not img.loadFromData(image_bytes):
        return [], False
    img = img.scaled(40, 40, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    bins = [[0.0, 0.0, 0.0, 0.0] for _ in range(18)]
    light = 0.0
    for y in range(img.height()):
        for x in range(img.width()):
            c = img.pixelColor(x, y)
            light += c.valueF()
            h, s, v = c.hsvHueF(), c.hsvSaturationF(), c.valueF()
            if h < 0 or s < 0.25 or v < 0.25:
                continue
            w = s * s * v
            b = bins[int(h * 18) % 18]
            b[0] += w
            b[1] += c.redF() * w
            b[2] += c.greenF() * w
            b[3] += c.blueF() * w
    dark = light / (img.width() * img.height()) < 0.35
    picks = []
    for b in sorted(range(18), key=lambda i: bins[i][0], reverse=True):
        if bins[b][0] < 1.2 or len(picks) == 3:
            break
        if any(min(abs(b - p), 18 - abs(b - p)) < 2 for p in picks):
            continue
        picks.append(b)
    out = []
    for b in picks:
        w, r, g, bl = bins[b]
        col = QColor.fromRgbF(r / w, g / w, bl / w)
        col = QColor.fromHsvF(col.hsvHueF(), min(col.hsvSaturationF(), 0.75), max(col.valueF(), 0.92))
        out.append(col.name().upper())
    return out, dark


# ------------------------------------------------------------------ o estilo
# Em vez de montar peça por peça, o gerador escolhe uma "receita" de visual completa
# (pensada como um look de verdade) e pinta com as cores da capa.

_BASE = {
    "uppercase": False, "bold": True, "outline": False, "outline_thickness": 1.0, "drop_shadow": True,
    "glow": False, "background": False, "karaoke": False, "countdown": True, "preview": False,
    "previous_line": False, "sparkle": False, "sparkle_amount": 1.0, "party": False, "party_effects": "both",
    "idle": "none", "idle_speed": 1.0, "idle_strength": 1.0, "exit_animation": "auto", "typewriter_sync": True,
    "typewriter_speed": 1.25, "letter_spacing": 0.5, "line_spacing": 4, "line_width": 900, "lyrics_opacity": 1.0,
}

# fam: gêneros que combinam; mood: climas; energy: low/mid/high; colour: tratamento de cor
RECIPES = [
    dict(name="shake", fam="rap latin pop electronic brazil", mood="party heavy", energy="high mid",
         colour="vivid", dark=None, style=dict(
             font="pixelify", layout="stack", animation="fade", idle="shake", idle_strength=0.5,
             idle_speed=0.25, uppercase=True, sparkle=True, sparkle_amount=0.5, party=True, text_size=40,
             letter_spacing=0)),
    dict(name="void", fam="electronic pop rnb", mood="sad faith love", energy="low mid", colour="mono_deep",
         dark=True, style=dict(
             font="pixelify", layout="words_tilted", animation="typewriter", exit_animation="drift",
             idle="float", idle_strength=0.25, idle_speed=0.75, outline=True, glow=True, karaoke=True,
             sparkle=True, party=True, text_size=44, letter_spacing=1)),
    dict(name="neon", fam="electronic pop latin", mood="party love", energy="mid high", colour="neon",
         dark=True, style=dict(
             font="righteous", layout="lines", animation="typewriter", idle="pulse", idle_strength=0.35,
             idle_speed=0.6, glow=True, karaoke=True, uppercase=True, letter_spacing=2.5, text_size=46,
             sparkle=True, sparkle_amount=0.75)),
    dict(name="arena", fam="rock", mood="heavy party", energy="high mid", colour="hot",
         dark=None, style=dict(
             font="bebas", layout="words_tilted", animation="drop", idle="shake", idle_strength=0.6,
             idle_speed=0.35, outline=True, outline_thickness=1.4, uppercase=True, karaoke=True,
             letter_spacing=1.5, text_size=54, exit_animation="fade")),
    dict(name="street", fam="rap latin brazil", mood="party heavy", energy="high mid", colour="vivid3",
         dark=None, style=dict(
             font="bebas", layout="stack", animation="pop", idle="bounce", idle_strength=0.35, idle_speed=0.8,
             outline=True, outline_thickness=1.2, uppercase=True, karaoke=True, text_size=42, letter_spacing=1)),
    dict(name="velvet", fam="rnb classic acoustic pop", mood="love sad", energy="low mid", colour="warm_soft",
         dark=None, style=dict(
             font="playfair", layout="words", animation="rise", exit_animation="fade", idle="float",
             idle_strength=0.3, idle_speed=0.5, glow=True, text_size=46, letter_spacing=0.5)),
    dict(name="letter", fam="pop brazil latin rnb acoustic", mood="love", energy="low mid", colour="love",
         dark=None, style=dict(
             font="pacifico", layout="lines", animation="words", exit_animation="drift", idle="float",
             idle_strength=0.35, idle_speed=0.6, glow=True, sparkle=True, sparkle_amount=1.5, text_size=44,
             bold=False, letter_spacing=0)),
    dict(name="rain", fam="acoustic brazil pop rnb rock classic", mood="sad", energy="low mid",
         colour="cool", dark=None, style=dict(
             font="montserrat", layout="lines", animation="fade", exit_animation="drift", idle="float",
             idle_strength=0.2, idle_speed=0.4, glow=True, bold=False, text_size=42, letter_spacing=1.5,
             countdown=True)),
    dict(name="arcade", fam="electronic pop", mood="party", energy="high", colour="rainbow",
         dark=None, style=dict(
             font="press_start", layout="lines", animation="wave", idle="bounce", idle_strength=0.3,
             idle_speed=0.7, outline=True, uppercase=True, party=True, sparkle=True, text_size=28,
             letter_spacing=0, line_spacing=10)),
    dict(name="sunset", fam="pop brazil latin rock", mood="party love", energy="mid", colour="sunset",
         dark=None, style=dict(
             font="righteous", layout="words_tilted", animation="typewriter", idle="sway", idle_strength=0.4,
             idle_speed=0.5, outline=True, glow=True, uppercase=True, karaoke=True, text_size=46,
             letter_spacing=1)),
    dict(name="campfire", fam="acoustic brazil classic", mood="love faith sad", energy="low mid",
         colour="honey", dark=None, style=dict(
             font="lobster", layout="lines", animation="typewriter", exit_animation="fade", idle="float",
             idle_strength=0.25, idle_speed=0.5, glow=True, text_size=46, bold=False, letter_spacing=0.5)),
    dict(name="halo", fam="acoustic classic pop rnb", mood="faith", energy="low mid", colour="gold",
         dark=None, style=dict(
             font="playfair", layout="words", animation="rise", exit_animation="fade", idle="float",
             idle_strength=0.3, idle_speed=0.5, glow=True, sparkle=True, sparkle_amount=2.0, text_size=46)),
    dict(name="comic", fam="pop latin brazil", mood="party love", energy="high mid", colour="vivid3",
         dark=False, style=dict(
             font="comic_relief", layout="stack", animation="pop", idle="bounce", idle_strength=0.4,
             idle_speed=0.9, outline=True, outline_thickness=1.5, uppercase=True, sparkle=True,
             text_size=40, letter_spacing=0.5)),
    dict(name="chrome", fam="rock electronic rap", mood="heavy sad", energy="mid low", colour="ice",
         dark=True, style=dict(
             font="montserrat", layout="words", animation="drop", exit_animation="drift", idle="float",
             idle_strength=0.2, idle_speed=0.4, outline=True, glow=True, uppercase=True, letter_spacing=3,
             text_size=44)),
]

# Paletas prontas, usadas quando a capa não tem cores fortes
_FALLBACK = {
    "vivid": ["#FF426C", "#FF8A2B", "#FFD166"], "vivid3": ["#FF5E9A", "#FFC94D", "#5EE6C8"],
    "neon": ["#FF4FD8", "#7A5CFF", "#38E1FF"], "hot": ["#FF5A36", "#FFB547", "#FFE08A"],
    "mono_deep": ["#BC1CFA", "#E2B8FF", "#7B2CFF"], "warm_soft": ["#F7C59F", "#F2879B", "#FFF1D0"],
    "love": ["#FF8FB1", "#C4B3FF", "#FFD1DC"], "cool": ["#A9E4FF", "#C4B3FF", "#8FC9F2"],
    "rainbow": ["#FF7F6E", "#FFC857", "#8DF2C4"], "sunset": ["#FF7F6E", "#FFC857", "#E38CF2"],
    "honey": ["#FFC857", "#FFF1D0", "#F7A35C"], "gold": ["#FFE3A3", "#FFFFFF", "#FFC857"],
    "ice": ["#DDF3FF", "#A9E4FF", "#C4B3FF"],
}


def _hsv(hexcol):
    from PySide6.QtGui import QColor
    c = QColor(hexcol)
    return max(0.0, c.hsvHueF()), c.hsvSaturationF(), c.valueF()


def _hex(h, s, v):
    from PySide6.QtGui import QColor
    return QColor.fromHsvF(h % 1.0, max(0.0, min(1.0, s)), max(0.0, min(1.0, v))).name().upper()


def _paint(treatment, palette, rnd):
    """Cores (principal, segunda, terceira, contorno) em harmonia, a partir da capa."""
    pal = list(palette) or list(_FALLBACK[treatment])
    h0, s0, v0 = _hsv(pal[0])
    if len(pal) < 2:  # inventa vizinhas harmônicas da cor da capa
        pal += [_hex(h0 + 0.09, s0 * 0.9, 1.0), _hex(h0 - 0.08, s0, 0.95)]
    if len(pal) < 3:
        pal.append(_hex(_hsv(pal[1])[0] + 0.08, 0.6, 1.0))
    hs = [_hsv(c) for c in pal]

    if treatment in ("vivid", "vivid3"):
        cols = [_hex(h, max(s, 0.65), 1.0) for h, s, v in hs]
    elif treatment == "neon":
        cols = [_hex(h, 0.85, 1.0) for h, s, v in hs]
    elif treatment == "hot":  # vermelho/laranja/amarelo; usa a capa se ela já for quente
        warm = palette and (h0 < 0.15 or h0 > 0.92)
        cols = ([_hex(h0, 0.8, 1.0), _hex(h0 + 0.06, 0.75, 1.0), _hex(h0 + 0.12, 0.5, 1.0)] if warm
                else list(_FALLBACK["hot"]))
    elif treatment == "mono_deep":  # uma cor só, profunda, com variações
        cols = [_hex(h0, max(s0, 0.85), 0.98), _hex(h0, 0.35, 1.0), _hex(h0 + 0.04, 0.9, 0.8)]
    elif treatment == "warm_soft":
        cols = [_hex(h, min(s, 0.45), 1.0) for h, s, v in hs]
    elif treatment == "love":
        cols = [_hex(0.95 if not palette else h, 0.45, 1.0) for h, s, v in hs[:1]] + ["#C4B3FF", "#FFD1DC"]
    elif treatment == "cool":
        cols = [_hex(0.55 + (h - 0.55) * 0.3, min(s, 0.35), 1.0) for h, s, v in hs]
    elif treatment in ("rainbow",):
        cols = [_hex(h, 0.7, 1.0) for h, s, v in hs]
    elif treatment == "sunset":
        cols = ["#FF7F6E", "#FFC857", _hex(h0, 0.55, 1.0)] if palette else list(_FALLBACK["sunset"])
    elif treatment == "honey":
        cols = list(_FALLBACK["honey"])
    elif treatment == "gold":
        cols = list(_FALLBACK["gold"])
    else:  # ice
        cols = [_hex(0.55, 0.15, 1.0), _hex(h0, 0.3, 1.0), "#FFFFFF"]
    outline = _hex(h0, 0.6, 0.13)  # contorno escuro da mesma cor: fica bem mais bonito que preto
    return cols, outline


def generate(title, artist, lines, cover_bytes=None, family=None):
    """Devolve (estilo, resumo). resumo = dict(family, mood, energy, cover, look)."""
    seed = hashlib.sha1(f"{_norm(artist)}|{_norm(title)}".encode("utf-8")).hexdigest()
    rnd = random.Random(seed)
    energy = lyric_energy(lines) if lines else 0.5
    mood, _ = lyric_mood(lines) if lines else (None, {})
    palette, dark_cover = cover_palette(cover_bytes)
    elevel = "high" if energy > 0.6 else "low" if energy < 0.3 else "mid"
    fam = family or "pop"

    scored = []
    for r in RECIPES:
        score = 0.0
        score += 2.0 if fam in r["fam"].split() else 0.0
        score += 2.2 if mood and mood in r["mood"].split() else (0.3 if not mood else -0.6)
        score += 1.2 if elevel in r["energy"].split() else -0.8
        if r["dark"] is not None:
            score += 0.5 if r["dark"] == dark_cover else -0.3
        score += rnd.random() * 1.1  # variedade: músicas parecidas não ficam todas iguais
        scored.append((score, r))
    scored.sort(key=lambda x: x[0], reverse=True)
    recipe = scored[0][1]

    st = dict(_BASE)
    st.update(recipe["style"])
    cols, outline = _paint(recipe["colour"], palette, rnd)
    if recipe["colour"] == "rainbow":
        st.update(accent="custom", custom_colour=cols[0], colour_mode="rainbow_flow")
    elif recipe["colour"] in ("vivid3", "sunset", "neon") or (len(palette) >= 3 and rnd.random() < 0.5):
        st.update(accent="custom", custom_colour=cols[0], second_colour=cols[1], third_colour=cols[2],
                  colour_mode="gradient3")
    else:
        st.update(accent="custom", custom_colour=cols[0], second_colour=cols[1], third_colour=cols[2],
                  colour_mode="gradient")
    st["outline_colour"] = outline

    # ajustes finos pela música
    if st["idle"] == "shake":
        st["idle_strength"] = round(min(0.9, st["idle_strength"] * (0.7 + energy * 0.6)), 2)
    if elevel == "high" and not st["party"] and recipe["name"] in ("neon", "street", "sunset", "comic"):
        st["party"] = rnd.random() < 0.5
    if mood == "sad":
        st["party"] = False

    summary = {"family": family, "mood": mood, "cover": bool(palette), "energy": elevel,
               "look": recipe["name"]}
    return st, summary
