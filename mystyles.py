"""Estilos salvos pelo usuário, guardados só no PC dele (%APPDATA%\\LLyrics\\my_styles.json)."""
import datetime as dt
import json
import os
import uuid

import lookcode
from config import data_dir

FILE = os.path.join(data_dir(), "my_styles.json")


def load():
    try:
        with open(FILE, encoding="utf-8") as f:
            items = json.load(f).get("styles", [])
    except (OSError, ValueError):
        return []
    out = []
    for it in items:
        if isinstance(it, dict) and it.get("name") and isinstance(it.get("style"), dict):
            it["style"] = lookcode.clean(it["style"])
            out.append(it)
    return out


def _write(items):
    tmp = FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump({"version": 1, "styles": items}, f, indent=2, ensure_ascii=False)
    os.replace(tmp, FILE)


def save(name, style):
    """Salva (ou substitui, se já existir um com o mesmo nome). Devolve True se substituiu."""
    items = load()
    now = dt.datetime.now().isoformat(timespec="seconds")
    for it in items:
        if it["name"].strip().lower() == name.strip().lower():
            it.update(style=lookcode.clean(style), updated=now)
            _write(items)
            return True
    items.insert(0, {"id": uuid.uuid4().hex[:12], "name": name.strip()[:60], "style": lookcode.clean(style),
                     "created": now, "updated": now})
    _write(items)
    return False


def update(style_id, style):
    items = load()
    for it in items:
        if it["id"] == style_id:
            it.update(style=lookcode.clean(style), updated=dt.datetime.now().isoformat(timespec="seconds"))
    _write(items)


def rename(style_id, name):
    items = load()
    for it in items:
        if it["id"] == style_id:
            it["name"] = name.strip()[:60]
    _write(items)


def delete(style_id):
    _write([it for it in load() if it["id"] != style_id])
