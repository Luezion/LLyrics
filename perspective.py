"""Layout "Perspectiva nas laterais": cada linha aparece inclinada em 3D, como se estivesse numa
parede da esquerda ou da direita. O lado muda em sequências aleatórias (ex.: 3 na direita, 2 na
esquerda, 4 na direita, 1 na esquerda…). Não usa captura de tela nem nada do jogo."""
import random
import time

from PySide6.QtCore import QObject, QPointF, QRectF, Qt
from PySide6.QtGui import QImage, QPainter, QPolygonF, QTransform

import render
from overlay import _Base


def side_for(track, index):
    """Esquerda ou direita para a linha 'index', em sequências de 1 a 4 linhas do mesmo lado."""
    rnd = random.Random(f"{track}|sides")
    side = rnd.choice(("left", "right"))
    pos = 0
    while True:
        run = rnd.choice((1, 2, 2, 3, 3, 4))
        if index < pos + run:
            return side
        pos += run
        side = "left" if side == "right" else "right"


class PerspWindow(_Base):
    def __init__(self, mgr, parity):
        super().__init__()
        self.mgr = mgr
        self.parity = parity
        self.index = None

    def paintEvent(self, e):
        p = QPainter(self)
        p.setCompositionMode(QPainter.CompositionMode_Source)
        p.fillRect(self.rect(), Qt.transparent)
        p.setCompositionMode(QPainter.CompositionMode_SourceOver)
        self.mgr.paint(self, p)
        p.end()


class PerspectiveManager(QObject):
    def __init__(self, ctl):
        super().__init__()
        self.ctl = ctl
        self.wins = [PerspWindow(self, 0), PerspWindow(self, 1)]
        self.cache = {}
        self.active = False

    def set_active(self, on):
        self.active = on
        self.cache.clear()
        if not on:
            for w in self.wins:
                w.hide()

    # ------------------------------------------------------------ geometria
    def _flat_cfg(self, text):
        cfg = dict(self.ctl.view)
        cfg.update(layout="lines", previous_line=False, preview=False, party=False)
        st = render.TextStyle(dict(cfg, line_width=100000))
        width = st.fm.horizontalAdvance(st.prep(text))
        # frase muito comprida vai em 2 linhas para não ficar fininha
        cfg["line_width"] = width / 1.8 if width / max(1.0, st.row_h) > 11 else 100000
        st = render.TextStyle(cfg)
        rows = st.wrap(st.prep(text))
        fw = max(st.fm.horizontalAdvance(r) for r in rows) + st.size * 0.8
        fh = st.block_height(rows) + st.row_h * 0.35
        return cfg, int(fw), int(fh)

    def quad_for(self, index, text):
        key = (self.ctl.track_id, index, text, self.ctl._cfg_version)
        if key in self.cache:
            return self.cache[key]
        cfg = self.ctl.view
        geo = self.ctl.screen().geometry()
        W, H = geo.width(), geo.height()
        side = side_for(self.ctl.track_id, index)
        rnd = random.Random(f"{self.ctl.track_id}|{index}|y")
        strength = max(0.05, min(1.0, float(cfg.get("persp_strength", 0.6))))
        _, fw, fh = self._flat_cfg(text)
        aspect = fw / max(1, fh)
        hb = H * float(cfg.get("persp_size", 0.15))            # altura perto da borda
        cz = float(cfg.get("center_zone", 0.35)) if not cfg.get("allow_center", True) else 0.18
        x_near = W * 0.95 if side == "right" else W * 0.05
        x_lim = W * (0.5 + cz * 0.65) if side == "right" else W * (0.5 - cz * 0.65)
        r = 1.0 - 0.6 * strength                                # quanto a ponta de longe encolhe
        length = aspect * hb * (1 + r) / 2
        max_len = abs(x_near - x_lim)
        if length > max_len:
            hb *= max_len / length
            length = max_len
        x_far = x_near - length if side == "right" else x_near + length
        yc = geo.height() * (float(cfg.get("persp_height", 0.5)) + (rnd.random() - 0.5) * 0.08)
        yc = min(max(yc, H * 0.12 + hb / 2), H * 0.78 - hb / 2)
        # a ponta de longe encolhe em direção a um ponto de fuga na altura do centro da tela
        vy = H * 0.46
        yc_f = vy + (yc - vy) * r
        top_n, bot_n = yc - hb / 2, yc + hb / 2
        top_f, bot_f = yc_f - hb * r / 2, yc_f + hb * r / 2
        if side == "right":
            pts = [(x_far, top_f), (x_near, top_n), (x_near, bot_n), (x_far, bot_f)]
        else:
            pts = [(x_near, top_n), (x_far, top_f), (x_far, bot_f), (x_near, bot_n)]
        quad = QPolygonF([QPointF(geo.x() + x, geo.y() + y) for x, y in pts])
        rect = quad.boundingRect().toAlignedRect().adjusted(-30, -30, 30, 30)
        self.cache[key] = (quad, rect)
        if len(self.cache) > 300:
            self.cache.clear()
        return quad, rect

    # ------------------------------------------------------------ quadro a quadro
    def tick(self):
        if not self.active:
            return
        lines, wins, t = self.ctl.current_lyrics()
        if not lines:
            for w in self.wins:
                w.hide()
            return
        f = render.compute_frame(lines, wins, t, self.ctl.view, True)
        k = f.idx
        for w in self.wins:
            i = k if (k >= 0 and k % 2 == w.parity) else k - 1
            if k < 0:
                i = 0 if w.parity == 0 else -1
            if i < 0 or i >= len(lines):
                w.hide()
                continue
            w.index = i
            _, rect = self.quad_for(i, lines[i].text)
            if w.geometry() != rect:
                w.setGeometry(rect)
            if not w.isVisible():
                w.show()
            w.update()

    def paint(self, win, p):
        lines, wins, t = self.ctl.current_lyrics()
        if not lines or win.index is None or win.index >= len(lines):
            return
        text = lines[win.index].text
        quad, rect = self.quad_for(win.index, text)
        cfg, fw, fh = self._flat_cfg(text)
        img = QImage(max(8, fw), max(8, fh), QImage.Format_ARGB32_Premultiplied)
        img.fill(Qt.transparent)
        ip = QPainter(img)
        render.draw_lyrics(ip, fw, fh, cfg, lines, render.line_windows(lines, cfg), t, self.ctl.album_color,
                           now=time.monotonic(), only_parity=win.index % 2)
        ip.end()
        src = QPolygonF([QPointF(0, 0), QPointF(fw, 0), QPointF(fw, fh), QPointF(0, fh)])
        off = rect.topLeft()
        dst = QPolygonF([QPointF(pt.x() - off.x(), pt.y() - off.y()) for pt in quad])
        tr = QTransform()
        if not QTransform.quadToQuad(src, dst, tr):
            return
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setTransform(tr)
        p.drawImage(0, 0, img)
