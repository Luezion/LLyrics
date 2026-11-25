"""Truques do Windows: janela que deixa o clique passar, sempre por cima, e atalhos globais.

Nada aqui mexe no processo do jogo: são só estilos de janela e RegisterHotKey,
o mesmo que apps como Discord e OBS usam.
"""
import ctypes
import sys

from PySide6.QtCore import QAbstractNativeEventFilter

IS_WIN = sys.platform == "win32"

GWL_EXSTYLE = -20
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOOLWINDOW = 0x00000080
WS_EX_LAYERED = 0x00080000
WS_EX_NOACTIVATE = 0x08000000
WS_EX_APPWINDOW = 0x00040000
HWND_TOPMOST = -1
SWP_FLAGS = 0x0001 | 0x0002 | 0x0010 | 0x0200  # NOSIZE | NOMOVE | NOACTIVATE | NOOWNERZORDER
WM_HOTKEY = 0x0312
MOD_ALT, MOD_CONTROL, MOD_SHIFT, MOD_NOREPEAT = 0x1, 0x2, 0x4, 0x4000

if IS_WIN:
    from ctypes import wintypes

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    _GetWL = user32.GetWindowLongPtrW
    _GetWL.restype = ctypes.c_ssize_t
    _GetWL.argtypes = [wintypes.HWND, ctypes.c_int]
    _SetWL = user32.SetWindowLongPtrW
    _SetWL.restype = ctypes.c_ssize_t
    _SetWL.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_ssize_t]
    user32.SetWindowPos.argtypes = [wintypes.HWND, wintypes.HWND, ctypes.c_int, ctypes.c_int,
                                    ctypes.c_int, ctypes.c_int, ctypes.c_uint]
    user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_uint, ctypes.c_uint]
    user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]


def set_click_through(widget, on):
    if not IS_WIN:
        return
    hwnd = int(widget.winId())
    style = _GetWL(hwnd, GWL_EXSTYLE)
    style |= WS_EX_LAYERED | WS_EX_TOOLWINDOW
    style &= ~WS_EX_APPWINDOW
    if on:
        style |= WS_EX_TRANSPARENT | WS_EX_NOACTIVATE
    else:
        style &= ~(WS_EX_TRANSPARENT | WS_EX_NOACTIVATE)
    _SetWL(hwnd, GWL_EXSTYLE, style)


def force_topmost(widget):
    if not IS_WIN:
        return
    user32.SetWindowPos(int(widget.winId()), HWND_TOPMOST, 0, 0, 0, 0, SWP_FLAGS)


class HotkeyFilter(QAbstractNativeEventFilter):
    """Recebe WM_HOTKEY. Os atalhos são registrados sem janela (vão para a fila da thread principal)."""

    def __init__(self):
        super().__init__()
        self.callbacks = {}
        self._next = 1

    def register(self, mods, vk, callback):
        if not IS_WIN:
            return False
        hid = self._next
        self._next += 1
        ok = bool(user32.RegisterHotKey(None, hid, mods | MOD_NOREPEAT, vk))
        if ok:
            self.callbacks[hid] = callback
        return ok

    def unregister_all(self):
        if IS_WIN:
            for hid in list(self.callbacks):
                user32.UnregisterHotKey(None, hid)
        self.callbacks.clear()

    def nativeEventFilter(self, event_type, message):
        if IS_WIN and event_type == b"windows_generic_MSG":
            msg = wintypes.MSG.from_address(int(message))
            if msg.message == WM_HOTKEY:
                cb = self.callbacks.get(int(msg.wParam))
                if cb:
                    cb()
                    return True, 0
        return False, 0


RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"


def autostart_command():
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    import os
    base = os.path.dirname(os.path.abspath(__file__))
    pyw = os.path.join(base, ".venv", "Scripts", "pythonw.exe")
    if not os.path.exists(pyw):
        pyw = sys.executable.replace("python.exe", "pythonw.exe")
    return f'"{pyw}" "{os.path.join(base, "main.py")}"'


def set_autostart(on):
    """Liga/desliga abrir junto com o Windows (registro do usuário, sem precisar de administrador)."""
    if not IS_WIN:
        return False
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as k:
            if on:
                winreg.SetValueEx(k, "LLyrics", 0, winreg.REG_SZ, autostart_command())
            else:
                try:
                    winreg.DeleteValue(k, "LLyrics")
                except FileNotFoundError:
                    pass
        return True
    except OSError:
        return False
