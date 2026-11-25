"""Busca de letras sincronizadas no lrclib.net e leitura do formato LRC."""
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request

from config import data_dir

API = "https://lrclib.net/api"
USER_AGENT = "LLyrics/1.0 (overlay de letras para desktop)"

_TS = re.compile(r"\[(\d+):(\d+(?:[.:]\d+)?)\]")
_OFFSET = re.compile(r"\[offset:\s*([+-]?\d+)\]", re.I)


class Line:
    __slots__ = ("time", "text", "end")

    def __init__(self, time, text):
        self.time = time
        self.text = text
        self.end = None  # preenchido por parse_lrc

    def __repr__(self):
        return f"Line({self.time:.2f}-{self.end}, {self.text!r})"


def parse_lrc(lrc):
    """Devolve só as linhas com texto. Linhas vazias do LRC (trechos instrumentais)
    servem para marcar onde a linha anterior termina."""
    offset = 0.0
    m = _OFFSET.search(lrc)
    if m:
        offset = int(m.group(1)) / 1000.0
    stamps = []
    for raw in lrc.splitlines():
        times = _TS.findall(raw)
        if not times:
            continue
        text = _TS.sub("", raw).strip()
        for mm, ss in times:
            t = int(mm) * 60 + float(ss.replace(":", "."))
            stamps.append((t - offset, text))
    stamps.sort(key=lambda s: s[0])
    lines = []
    for i, (t, text) in enumerate(stamps):
        if not text or text in ("♪", "♫", "..."):
            continue
        ln = Line(max(0.0, t), text)
        ln.end = stamps[i + 1][0] if i + 1 < len(stamps) else None
        lines.append(ln)
    return lines


_JUNK = re.compile(
    r"\s*[\(\[][^)\]]*(official|video|lyric|letra|audio|áudio|visualizer|remaster|"
    r"hd|hq|4k|mv|clipe|ao vivo|live)[^)\]]*[\)\]]",
    re.I,
)
_FEAT = re.compile(r"\s*[\(\[]?\s*(feat\.?|ft\.?|featuring|part\.?)\s[^)\]]*[\)\]]?", re.I)


def clean_title(title):
    t = _JUNK.sub("", title)
    t = re.sub(r"\s+-\s+(\d{4}\s+)?remaster(ed)?.*$", "", t, flags=re.I)
    t = _FEAT.sub("", t)
    return t.strip(" -|")


def clean_artist(artist):
    a = re.sub(r"\s*-\s*topic$", "", artist, flags=re.I)
    a = re.sub(r"vevo$", "", a, flags=re.I)
    a = re.split(r",|&| x | e | feat\.? | ft\.? ", a, maxsplit=1)[0]
    return a.strip()


def candidates(title, artist):
    """Combinações de (título, artista) para tentar, da mais provável à menos."""
    out = []
    ct, ca = clean_title(title), clean_artist(artist or "")
    out.append((ct, ca))
    if " - " in ct:  # títulos do YouTube: "Artista - Música"
        left, right = ct.split(" - ", 1)
        out.append((clean_title(right), clean_artist(left)))
    if (title, artist) not in out:
        out.append((title, artist or ""))
    seen, uniq = set(), []
    for c in out:
        if c[0] and c not in seen:
            seen.add(c)
            uniq.append(c)
    return uniq


class LrclibBusy(Exception):
    pass


def _get(path, params):
    url = f"{API}/{path}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise LrclibBusy(str(e))
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as e:
        raise LrclibBusy(str(e))


def _cache_file(key):
    d = os.path.join(data_dir(), "cache")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, hashlib.sha1(key.encode("utf-8")).hexdigest() + ".json")


def fetch(title, artist, album="", duration=0.0):
    """Devolve (linhas, texto_status). linhas == [] quando não há letra sincronizada.
    Lança LrclibBusy quando o site não responde."""
    key = f"{title}\u0000{artist}\u0000{int(duration)}"
    cf = _cache_file(key)
    try:
        with open(cf, "r", encoding="utf-8") as f:
            cached = json.load(f)
        if cached.get("synced") or time.time() - cached.get("ts", 0) < 2 * 86400:
            return parse_lrc(cached.get("synced") or ""), cached.get("instrumental", False)
    except (OSError, ValueError):
        pass

    synced, instrumental = None, False
    for t, a in candidates(title, artist):
        params = {"track_name": t, "artist_name": a}
        if album:
            params["album_name"] = album
        if duration > 0:
            params["duration"] = int(round(duration))
        res = _get("get", params)
        if res and res.get("syncedLyrics"):
            synced = res["syncedLyrics"]
            break
        if res and res.get("instrumental"):
            instrumental = True
            break
        # Busca mais solta, escolhendo a duração mais próxima
        res = _get("search", {"track_name": t, "artist_name": a}) if a else _get("search", {"q": t})
        best, best_diff = None, 1e9
        for item in res or []:
            if not item.get("syncedLyrics"):
                continue
            diff = abs((item.get("duration") or 0) - duration) if duration > 0 else 0
            if diff < best_diff:
                best, best_diff = item, diff
        if best and (duration <= 0 or best_diff <= 8):
            synced = best["syncedLyrics"]
            break

    try:
        with open(cf, "w", encoding="utf-8") as f:
            json.dump({"synced": synced, "instrumental": instrumental, "ts": time.time()}, f, ensure_ascii=False)
    except OSError:
        pass
    return (parse_lrc(synced) if synced else []), instrumental
