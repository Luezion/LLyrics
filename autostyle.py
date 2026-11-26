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
_COOL = ["#A9E4FF", "#C4B3FF", "#A3B1C9", "#8FC9F2"]
_WARM = ["#FF7F6E", "#FFC857", "#FFB3C8", "#FFF1D0"]


def generate(title, artist, lines, cover_bytes=None, family=None):
    """Devolve (estilo, resumo). resumo = dict(family, mood, energy) para mostrar ao usuário."""
    seed = hashlib.sha1(f"{_norm(artist)}|{_norm(title)}".encode("utf-8")).hexdigest()
    rnd = random.Random(seed)
    energy = lyric_energy(lines) if lines else 0.5
    mood, _ = lyric_mood(lines) if lines else (None, {})
    palette, dark_cover = cover_palette(cover_bytes)
    fam = family or "pop"

    def pick(*opts):
        return rnd.choice(opts)

    st = {
        "uppercase": False, "bold": True, "outline": False, "drop_shadow": True, "glow": False,
        "background": False, "karaoke": False, "countdown": True, "preview": False, "previous_line": False,
        "sparkle": False, "sparkle_amount": 1.0, "party": False, "party_effects": "both", "idle": "none",
        "idle_speed": 1.0, "idle_strength": 1.0, "exit_animation": "auto", "typewriter_sync": True,
        "letter_spacing": 0.5, "line_spacing": 4, "outline_thickness": 1.0, "outline_colour": "#141414",
        "lyrics_opacity": 1.0,
    }

    # fonte e layout pelo gênero
    if fam == "rock":
        st.update(font=pick("bebas", "righteous", "bebas"), uppercase=True, outline=True,
                  layout=pick("lines", "words_tilted"), animation=pick("drop", "typewriter"))
    elif fam == "rap":
        st.update(font=pick("bebas", "montserrat", "pixelify"), uppercase=True, outline=True, karaoke=True,
                  layout="stack", animation="typewriter")
    elif fam == "electronic":
        st.update(font=pick("righteous", "press_start", "pixelify", "montserrat"), uppercase=True, glow=True,
                  layout=pick("lines", "words"), animation=pick("wave", "pop"))
    elif fam == "latin":
        st.update(font=pick("righteous", "poppins", "bebas"), uppercase=pick(True, False), karaoke=True,
                  layout=pick("stack", "words_tilted"), animation="pop")
    elif fam == "brazil":
        st.update(font=pick("poppins", "lobster", "montserrat"), karaoke=True,
                  layout=pick("lines", "words"), animation=pick("typewriter", "rise"))
    elif fam == "rnb":
        st.update(font=pick("playfair", "poppins", "lobster"), glow=True, layout="lines",
                  animation=pick("rise", "fade"), exit_animation="fade")
    elif fam == "acoustic":
        st.update(font=pick("playfair", "eagle_lake", "poppins"), layout="lines", animation="typewriter")
    elif fam == "classic":
        st.update(font=pick("playfair", "eagle_lake"), layout="lines", animation="fade", exit_animation="fade",
                  bold=False)
    else:  # pop
        st.update(font=pick("poppins", "montserrat", "bebas"), karaoke=True,
                  layout=pick("lines", "words", "words_tilted"), animation=pick("typewriter", "pop", "words"))

    # clima da letra
    if mood == "love":
        st.update(sparkle=True, idle="float", idle_strength=0.4, glow=True, exit_animation="drift",
                  font=pick(st["font"], "pacifico", "lobster") if fam not in ("rock", "rap") else st["font"])
    elif mood == "sad":
        st.update(animation="fade", exit_animation=pick("drift", "fade"), idle="float", idle_strength=0.25,
                  idle_speed=0.6, party=False, sparkle=False, uppercase=False)
    elif mood == "party":
        st.update(party=True, idle="shake" if fam in ("rock", "rap") else pick("bounce", "pulse"), sparkle=True)
    elif mood == "heavy":
        st.update(idle="shake", idle_strength=0.4 + energy * 0.6, idle_speed=0.3 + energy * 0.4,
                  uppercase=True, outline=True, outline_thickness=1.3)
    elif mood == "faith":
        st.update(glow=True, sparkle=True, idle="float", idle_strength=0.3, exit_animation="fade")

    # ritmo
    if energy > 0.7 and st["idle"] == "none":
        st["idle"] = "shake" if fam in ("rock", "rap") else pick("bounce", "pulse")
        st["idle_strength"] = 0.5
    if energy > 0.75 and fam in ("electronic", "latin", "pop") and mood != "sad":
        st["party"] = True
    if energy < 0.25 and st["animation"] in ("pop", "drop", "wave"):
        st["animation"] = "fade"
    st["text_size"] = 40 if st["layout"] == "stack" else (40 if st["font"] == "press_start" else 46)
    if st["font"] == "press_start":
        st["text_size"] = 30
        st["letter_spacing"] = 0

    # cores
    if fam == "electronic" and mood in (None, "party") and rnd.random() < 0.5:
        st.update(accent="custom", custom_colour=(palette[0] if palette else "#C4B3FF"), colour_mode="rainbow_flow")
    elif len(palette) >= 3 and energy > 0.45:
        st.update(accent="custom", custom_colour=palette[0], second_colour=palette[1], third_colour=palette[2],
                  colour_mode="gradient3")
    elif len(palette) >= 2:
        st.update(accent="custom", custom_colour=palette[0], second_colour=palette[1], colour_mode="gradient")
    elif palette:
        st.update(accent="album", colour_mode="solid")
    else:
        base = _COOL if mood in ("sad", "faith") else _WARM
        st.update(accent="custom", custom_colour=rnd.choice(base), colour_mode="solid")
    if mood == "sad" and st["colour_mode"] == "solid" and st["accent"] != "custom":
        st.update(accent="custom", custom_colour=rnd.choice(_COOL))
    if dark_cover and not st["outline"]:
        st["glow"] = True

    summary = {"family": family, "mood": mood, "cover": bool(palette),
               "energy": "high" if energy > 0.6 else "low" if energy < 0.3 else "mid"}
    return st, summary
