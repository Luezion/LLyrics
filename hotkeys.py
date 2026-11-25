"""Atalhos globais: texto ("Ctrl+Shift+L") <-> códigos do Windows, e captura pela tela de configurações."""
from PySide6.QtCore import Qt

import winutil

MODS = [("Ctrl", winutil.MOD_CONTROL), ("Alt", winutil.MOD_ALT), ("Shift", winutil.MOD_SHIFT), ("Win", 0x8)]

# Nome exibido -> código virtual do Windows (VK)
_NAMED = {
    "Space": 0x20, "PageUp": 0x21, "PageDown": 0x22, "End": 0x23, "Home": 0x24,
    "Left": 0x25, "Up": 0x26, "Right": 0x27, "Down": 0x28, "Insert": 0x2D, "Delete": 0x2E,
    "Pause": 0x13, "ScrollLock": 0x91, "Num0": 0x60, "Num1": 0x61, "Num2": 0x62, "Num3": 0x63,
    "Num4": 0x64, "Num5": 0x65, "Num6": 0x66, "Num7": 0x67, "Num8": 0x68, "Num9": 0x69,
    "Num*": 0x6A, "NumPlus": 0x6B, "Num-": 0x6D, "Num/": 0x6F, ";": 0xBA, "=": 0xBB, ",": 0xBC,
    "-": 0xBD, ".": 0xBE, "/": 0xBF, "`": 0xC0, "[": 0xDB, "\\": 0xDC, "]": 0xDD, "'": 0xDE,
}
_QT_NAMED = {
    Qt.Key_Space: "Space", Qt.Key_PageUp: "PageUp", Qt.Key_PageDown: "PageDown", Qt.Key_End: "End",
    Qt.Key_Home: "Home", Qt.Key_Left: "Left", Qt.Key_Up: "Up", Qt.Key_Right: "Right", Qt.Key_Down: "Down",
    Qt.Key_Insert: "Insert", Qt.Key_Delete: "Delete", Qt.Key_Pause: "Pause", Qt.Key_ScrollLock: "ScrollLock",
    Qt.Key_Semicolon: ";", Qt.Key_Equal: "=", Qt.Key_Comma: ",", Qt.Key_Minus: "-", Qt.Key_Period: ".",
    Qt.Key_Slash: "/", Qt.Key_QuoteLeft: "`", Qt.Key_BracketLeft: "[", Qt.Key_Backslash: "\\",
    Qt.Key_BracketRight: "]", Qt.Key_Apostrophe: "'",
}
_MODIFIER_KEYS = {Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta, Qt.Key_AltGr, Qt.Key_Super_L,
                  Qt.Key_Super_R}


def key_vk(name):
    if len(name) == 1 and (name.isalpha() or name.isdigit()):
        return ord(name.upper())
    if name.upper().startswith("F") and name[1:].isdigit() and 1 <= int(name[1:]) <= 24:
        return 0x70 + int(name[1:]) - 1
    return _NAMED.get(name)


def parse(text):
    """'Ctrl+Shift+L' -> (mods, vk) ou None."""
    if not text:
        return None
    parts = text.split("+")
    mods = 0
    key = None
    for part in parts:
        hit = [m for n, m in MODS if n.lower() == part.lower()]
        if hit:
            mods |= hit[0]
        else:
            key = part
    vk = key_vk(key) if key else None
    return (mods, vk) if vk else None


def is_function_key(name):
    return name.upper().startswith("F") and name[1:].isdigit()


def from_event(event):
    """Texto do atalho a partir de um QKeyEvent. Devolve (texto, erro): erro = 'need_mod' ou None.
    Devolve (None, None) se só um modificador foi apertado."""
    key = event.key()
    if key in _MODIFIER_KEYS or key == Qt.Key_unknown:
        return None, None
    mods = event.modifiers()
    names = []
    if mods & Qt.ControlModifier:
        names.append("Ctrl")
    if mods & Qt.AltModifier:
        names.append("Alt")
    if mods & Qt.ShiftModifier:
        names.append("Shift")
    if mods & Qt.MetaModifier:
        names.append("Win")
    keypad = bool(mods & Qt.KeypadModifier)
    if Qt.Key_F1 <= key <= Qt.Key_F24:
        name = f"F{key - Qt.Key_F1 + 1}"
    elif Qt.Key_A <= key <= Qt.Key_Z:
        name = chr(key)
    elif Qt.Key_0 <= key <= Qt.Key_9:
        name = f"Num{chr(key)}" if keypad else chr(key)
    elif keypad and key in (Qt.Key_Asterisk, Qt.Key_Plus, Qt.Key_Minus, Qt.Key_Slash):
        name = "Num" + {Qt.Key_Asterisk: "*", Qt.Key_Plus: "Plus", Qt.Key_Minus: "-", Qt.Key_Slash: "/"}[key]
    else:
        name = _QT_NAMED.get(key)
    if not name:
        return None, None
    if not names and not is_function_key(name):
        return None, "need_mod"
    return "+".join(names + [name]), None
