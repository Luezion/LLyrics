"""Galeria de estilos da comunidade do LLyrics (fica no próprio repositório do GitHub)."""
import json
import time
import urllib.error
import urllib.parse
import urllib.request

from version import UPDATE_REPO, __version__

GALLERY_URL = f"https://raw.githubusercontent.com/{UPDATE_REPO}/main/community/looks.json"
GALLERY_PAGE = f"https://github.com/{UPDATE_REPO}/tree/main/community"
NEW_LOOK_URL = f"https://github.com/{UPDATE_REPO}/issues/new"

_cache = {"at": 0.0, "looks": None}


def fetch_gallery(force=False):
    """Lista de estilos [{id, name, author, description, code, added}], mais novos primeiro.
    Lança OSError se não der para baixar."""
    if not force and _cache["looks"] is not None and time.time() - _cache["at"] < 600:
        return _cache["looks"]
    req = urllib.request.Request(f"{GALLERY_URL}?t={int(time.time() // 60)}",
                                 headers={"User-Agent": f"LLyrics/{__version__}"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError) as e:
        raise OSError(str(e)) from e
    looks = [x for x in data.get("looks", []) if isinstance(x, dict) and x.get("code")]
    looks.sort(key=lambda x: x.get("added", ""), reverse=True)
    _cache.update(at=time.time(), looks=looks)
    return looks


def submit_url(name, author, description, code):
    """Link que abre o formulário do GitHub já preenchido com o estilo."""
    params = {
        "template": "look.yml",
        "title": f"[Look] {name}".strip(),
        "name": name,
        "author": author,
        "description": description,
        "code": code,
    }
    return NEW_LOOK_URL + "?" + urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
