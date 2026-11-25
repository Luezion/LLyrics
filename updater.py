"""Atualização automática: procura uma versão nova nas Releases do GitHub e instala com um clique.

- No .exe: baixa LLyrics-windows.zip da release, troca os arquivos e abre a versão nova.
- Rodando pelo código (Iniciar.bat): baixa o código da release, troca os arquivos,
  atualiza as dependências e abre de novo.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import urllib.error
import urllib.request
import zipfile

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import (QDialog, QHBoxLayout, QLabel, QProgressBar, QPushButton,
                               QTextBrowser, QVBoxLayout)

from version import UPDATE_REPO, __version__

API = f"https://api.github.com/repos/{UPDATE_REPO}/releases/latest"
ASSET_NAME = "LLyrics-windows.zip"
UA = {"User-Agent": f"LLyrics/{__version__}", "Accept": "application/vnd.github+json"}

FROZEN = getattr(sys, "frozen", False)
APP_DIR = os.path.dirname(sys.executable) if FROZEN else os.path.dirname(os.path.abspath(__file__))


def parse_version(v):
    nums = re.findall(r"\d+", v or "")
    return tuple(int(n) for n in nums[:3]) + (0,) * (3 - len(nums[:3]))


def is_newer(remote, local=__version__):
    return parse_version(remote) > parse_version(local)


def latest_release():
    """Devolve dict(version, notes, url, download) ou None. Lança OSError se não der para checar."""
    req = urllib.request.Request(API, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        if e.code == 404:  # ainda não tem nenhuma release
            return None
        raise OSError(f"GitHub respondeu {e.code}") from e
    except (urllib.error.URLError, TimeoutError, ValueError) as e:
        raise OSError(str(e)) from e
    download = None
    if FROZEN:
        for a in data.get("assets") or []:
            if a.get("name") == ASSET_NAME:
                download = a.get("browser_download_url")
    else:
        download = data.get("zipball_url")
    return {
        "version": (data.get("tag_name") or "").lstrip("vV"),
        "notes": data.get("body") or "",
        "url": data.get("html_url") or f"https://github.com/{UPDATE_REPO}/releases/latest",
        "download": download,
    }


class _Signals(QObject):
    checked = Signal(object, str)        # release (ou None), erro
    progress = Signal(int, int)          # baixado, total
    finished = Signal(bool, str)         # ok, mensagem/caminho


def check_async(callback):
    """Procura atualização numa thread; chama callback(release_ou_None, erro) na thread do Qt."""
    sig = _Signals()
    sig.checked.connect(callback)
    sig._keep = sig  # noqa: SLF001 - evita coleta antes do sinal

    def work():
        try:
            rel = latest_release()
            sig.checked.emit(rel, "")
        except OSError as e:
            sig.checked.emit(None, str(e))

    threading.Thread(target=work, daemon=True).start()
    return sig


def _find_root(folder, marker):
    for root, _dirs, files in os.walk(folder):
        if marker in files:
            return root
    return None


def _download_and_prepare(url, sig):
    tmp = tempfile.mkdtemp(prefix="llyrics-update-")
    zpath = os.path.join(tmp, "update.zip")
    req = urllib.request.Request(url, headers={"User-Agent": UA["User-Agent"]})
    with urllib.request.urlopen(req, timeout=30) as r, open(zpath, "wb") as f:
        total = int(r.headers.get("Content-Length") or 0)
        got = 0
        while True:
            chunk = r.read(256 * 1024)
            if not chunk:
                break
            f.write(chunk)
            got += len(chunk)
            sig.progress.emit(got, total)
    out = os.path.join(tmp, "new")
    with zipfile.ZipFile(zpath) as z:
        for name in z.namelist():  # proteção contra caminhos estranhos no zip
            target = os.path.realpath(os.path.join(out, name))
            if not target.startswith(os.path.realpath(out) + os.sep) and target != os.path.realpath(out):
                raise OSError("arquivo de atualização inválido")
        z.extractall(out)
    src = _find_root(out, "LLyrics.exe" if FROZEN else "main.py")
    if not src:
        raise OSError("a atualização não tem os arquivos esperados")
    return tmp, src


def _write_script(tmp, src):
    pid = os.getpid()
    bat = os.path.join(tmp, "aplicar.bat")
    if FROZEN:
        restart = f'start "" "{os.path.join(APP_DIR, "LLyrics.exe")}"'
    else:
        py = os.path.join(APP_DIR, ".venv", "Scripts", "python.exe")
        pyw = os.path.join(APP_DIR, ".venv", "Scripts", "pythonw.exe")
        restart = (f'"{py}" -m pip install -q -r "{os.path.join(APP_DIR, "requirements.txt")}"\r\n'
                   f'cd /d "{APP_DIR}"\r\nstart "" "{pyw}" main.py')
    lines = [
        "@echo off",
        "chcp 65001 >nul",
        "set n=0",
        ":espera",
        # espera o app antigo fechar; se travar, fecha à força depois de ~15 s
        f'tasklist /FI "PID eq {pid}" /NH 2>nul | find " {pid} " >nul || goto pronto',
        "set /a n+=1",
        f"if %n% geq 15 taskkill /PID {pid} /F >nul 2>&1",
        "ping -n 2 127.0.0.1 >nul",
        "goto espera",
        ":pronto",
        "ping -n 2 127.0.0.1 >nul",
        f'robocopy "{src}" "{APP_DIR}" /E /XD .git .venv /R:5 /W:1 /NFL /NDL /NJH /NJS /NP >nul',
        restart,
        f'(goto) 2>nul & rmdir /s /q "{tmp}"',
    ]
    with open(bat, "w", encoding="utf-8") as f:
        f.write("\r\n".join(lines) + "\r\n")
    # roda o .bat escondido (sem janela preta), mesmo com o Terminal do Windows 11
    vbs = os.path.join(tmp, "aplicar.vbs")
    with open(vbs, "w", encoding="utf-16") as f:
        f.write('CreateObject("WScript.Shell").Run "cmd /c """ & "' + bat.replace('"', '""')
                + '" & """", 0, False\r\n')
    return vbs


def can_write_app_dir():
    try:
        test = os.path.join(APP_DIR, ".llyrics-write-test")
        with open(test, "w") as f:
            f.write("ok")
        os.remove(test)
        return True
    except OSError:
        return False


STYLE = """
QDialog { background: #141419; color: #ECECF1; font-family: 'Segoe UI'; font-size: 13px; }
QLabel { color: #ECECF1; }
QLabel#title { font-size: 19px; font-weight: 600; }
QLabel#sub { color: #A8A8B5; }
QTextBrowser { background: #1C1C23; border: 1px solid #2A2A33; border-radius: 10px; padding: 8px; color: #DADAE2; }
QPushButton { background: #22222A; border: 1px solid #33333D; border-radius: 8px; padding: 7px 14px; color: #ECECF1; }
QPushButton:hover { border-color: #C4B3FF; }
QPushButton#primary { background: #C4B3FF; color: #141419; border: none; font-weight: 600; }
QPushButton#primary:disabled { background: #55516A; color: #2A2A33; }
QProgressBar { background: #22222A; border: none; border-radius: 4px; height: 8px; text-align: center; color: transparent; }
QProgressBar::chunk { background: #C4B3FF; border-radius: 4px; }
"""


class UpdateDialog(QDialog):
    def __init__(self, release, cfg, on_quit, quiet=False):
        super().__init__(None, Qt.Window if quiet else Qt.Window | Qt.WindowStaysOnTopHint)
        if quiet:  # checagem automática: não rouba o foco do jogo
            self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.release, self.cfg, self.on_quit = release, cfg, on_quit
        self.setWindowTitle("LLyrics — atualização")
        self.setStyleSheet(STYLE)
        self.resize(480, 420)
        v = QVBoxLayout(self)
        v.setContentsMargins(20, 18, 20, 18)
        t = QLabel(f"Nova versão do LLyrics: {release['version']}")
        t.setObjectName("title")
        v.addWidget(t)
        s = QLabel(f"Você está usando a {__version__}. Novidades:")
        s.setObjectName("sub")
        v.addWidget(s)
        notes = QTextBrowser()
        notes.setOpenExternalLinks(True)
        notes.setMarkdown(release["notes"] or "Melhorias e correções.")
        v.addWidget(notes, 1)
        self.bar = QProgressBar()
        self.bar.setVisible(False)
        v.addWidget(self.bar)
        self.msg = QLabel("")
        self.msg.setObjectName("sub")
        self.msg.setWordWrap(True)
        v.addWidget(self.msg)
        row = QHBoxLayout()
        self.skip_btn = QPushButton("Pular esta versão")
        self.later_btn = QPushButton("Depois")
        self.go_btn = QPushButton("Atualizar agora")
        self.go_btn.setObjectName("primary")
        row.addWidget(self.skip_btn)
        row.addStretch(1)
        row.addWidget(self.later_btn)
        row.addWidget(self.go_btn)
        v.addLayout(row)
        self.skip_btn.clicked.connect(self._skip)
        self.later_btn.clicked.connect(self.close)
        self.go_btn.clicked.connect(self._update)
        if not release.get("download"):
            self.go_btn.setText("Abrir página de download")
        elif not can_write_app_dir():
            self.msg.setText("Não tenho permissão para trocar os arquivos na pasta do app "
                             "(ele está em Arquivos de Programas?). Use \"Abrir página\" e baixe manualmente.")
            self.go_btn.setText("Abrir página de download")
            self.release = dict(release, download=None)

    def _skip(self):
        self.cfg["skip_version"] = self.release["version"]
        self.cfg.save()
        self.close()

    def _update(self):
        if not self.release.get("download"):
            import webbrowser
            webbrowser.open(self.release["url"])
            self.close()
            return
        for b in (self.go_btn, self.later_btn, self.skip_btn):
            b.setEnabled(False)
        self.bar.setVisible(True)
        self.bar.setRange(0, 0)
        self.msg.setText("Baixando…")
        sig = _Signals(self)
        sig.progress.connect(self._progress)
        sig.finished.connect(self._done)
        url = self.release["download"]

        def work():
            try:
                tmp, src = _download_and_prepare(url, sig)
                sig.finished.emit(True, _write_script(tmp, src))
            except (OSError, zipfile.BadZipFile, urllib.error.URLError) as e:
                sig.finished.emit(False, str(e))

        threading.Thread(target=work, daemon=True).start()

    def _progress(self, got, total):
        if total > 0:
            self.bar.setRange(0, total)
            self.bar.setValue(got)
            self.msg.setText(f"Baixando… {got / 1e6:.1f} de {total / 1e6:.1f} MB")
        else:
            self.msg.setText(f"Baixando… {got / 1e6:.1f} MB")

    def _done(self, ok, info):
        if not ok:
            self.bar.setVisible(False)
            self.msg.setText(f"Não deu para atualizar: {info}")
            for b in (self.go_btn, self.later_btn, self.skip_btn):
                b.setEnabled(True)
            return
        self.msg.setText("Instalando e reabrindo o LLyrics…")
        flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        subprocess.Popen(["wscript.exe", "//B", "//Nologo", info], creationflags=flags, close_fds=True)
        self.on_quit()


class Updater(QObject):
    """Checa ao abrir e a cada 6 horas; mostra a tela quando tiver versão nova."""

    def __init__(self, cfg, on_quit, notify=None):
        super().__init__()
        self.cfg, self.on_quit, self.notify = cfg, on_quit, notify
        self.dialog = None
        self._sig = None

    def check(self, manual=False):
        if not manual and not self.cfg.get("auto_update", True):
            return

        def got(rel, err):
            if rel and is_newer(rel["version"]):
                if not manual and self.cfg.get("skip_version") == rel["version"]:
                    return
                self.show(rel, quiet=not manual)
            elif manual and self.notify:
                if err:
                    self.notify(f"Não consegui procurar atualizações agora ({err}).")
                else:
                    self.notify(f"Você já está na versão mais recente ({__version__}).")

        self._sig = check_async(got)

    def show(self, rel, quiet=False):
        if self.dialog and self.dialog.isVisible():
            if not quiet:
                self.dialog.raise_()
                self.dialog.activateWindow()
            return
        self.dialog = UpdateDialog(rel, self.cfg, self.on_quit, quiet)
        self.dialog.show()
        if quiet:
            self.dialog.lower()
            if self.notify:
                self.notify(f"Nova versão {rel['version']} disponível. A janela de atualização está aberta.")
        else:
            self.dialog.raise_()
            self.dialog.activateWindow()
