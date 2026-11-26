"""Janelas do overlay (letra e widget) e o controlador que junta mídia + letras + desenho."""
import random
import threading
import time

from PySide6.QtCore import QObject, QPoint, QRect, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QGuiApplication, QPainter, QPen
from PySide6.QtWidgets import QWidget

import lyrics as lyr
import render
import winutil
from i18n import tr

DEMO_TIMES = ["00:00.50", "00:04.20", "00:08.00", "00:11.60", "00:15.20", "00:21.00", "00:25.00", "00:29.00"]


def demo_lrc():
    """Letra de exemplo no idioma atual (linhas vazias marcam a pausa instrumental)."""
    texts = [tr("demo.1"), tr("demo.2"), tr("demo.3"), tr("demo.4"), "", tr("demo.5"), tr("demo.6"), ""]
    return "\n".join(f"[{t}]{x}" for t, x in zip(DEMO_TIMES, texts))

DEMO_LEN = 31.0


class _Base(QWidget):
    moved = Signal(QPoint)

    def __init__(self):
        super().__init__(None, Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool
                         | Qt.WindowDoesNotAcceptFocus | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.edit_mode = False
        self._drag = None

    def set_edit(self, on):
        self.edit_mode = on
        winutil.set_click_through(self, not on)
        self.setCursor(Qt.SizeAllCursor if on else Qt.ArrowCursor)
        self.update()

    def showEvent(self, e):
        super().showEvent(e)
        winutil.set_click_through(self, not self.edit_mode)
        winutil.force_topmost(self)

    def mousePressEvent(self, e):
        if self.edit_mode and e.button() == Qt.LeftButton:
            self._drag = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag is not None:
            self.move(e.globalPosition().toPoint() - self._drag)

    def mouseReleaseEvent(self, e):
        if self._drag is not None:
            self._drag = None
            self.moved.emit(self.frameGeometry().center())

    def paint_edit_frame(self, p, label):
        if not self.edit_mode:
            return
        p.setPen(QPen(QColor(255, 255, 255, 200), 2, Qt.DashLine))
        p.setBrush(QColor(0, 0, 0, 60))
        p.drawRoundedRect(QRectF(self.rect()).adjusted(1, 1, -1, -1), 12, 12)
        f = QFont("Segoe UI")
        f.setPixelSize(13)
        p.setFont(f)
        p.setPen(QColor(255, 255, 255, 230))
        p.drawText(QRect(0, 4, self.width(), 20), Qt.AlignHCenter | Qt.AlignTop, label)


class LyricsWindow(_Base):
    def __init__(self, ctl, parity=None):
        super().__init__()
        self.ctl = ctl
        self.parity = parity      # None = posição fixa; 0/1 = linhas pares/ímpares (aleatória)
        self.random_mode = False

    def paintEvent(self, e):
        p = QPainter(self)
        p.setCompositionMode(QPainter.CompositionMode_Source)
        p.fillRect(self.rect(), Qt.transparent)
        p.setCompositionMode(QPainter.CompositionMode_SourceOver)
        self.paint_edit_frame(p, tr("edit.lyrics_label", key=self.ctl.cfg.get("hotkey_move", "")))
        c = self.ctl
        lines, wins, t = c.current_lyrics()
        if lines:
            rnd = self.random_mode
            render.draw_lyrics(p, self.width(), self.height(), c.view, lines, wins, t, c.album_color,
                               now=time.monotonic(), only_parity=self.parity if rnd else None,
                               stack_box=render.stack_box_for(c.view) if rnd else None)
        p.end()


class WidgetWindow(_Base):
    def __init__(self, ctl):
        super().__init__()
        self.ctl = ctl

    def paintEvent(self, e):
        p = QPainter(self)
        p.setCompositionMode(QPainter.CompositionMode_Source)
        p.fillRect(self.rect(), Qt.transparent)
        p.setCompositionMode(QPainter.CompositionMode_SourceOver)
        render.draw_widget(p, self.ctl.view, self.ctl.widget_info(), self.ctl.album_color)
        self.paint_edit_frame(p, "")
        p.end()


class Controller(QObject):
    media_signal = Signal(object)
    lyrics_signal = Signal(str, object, str)
    style_signal = Signal(str, object, object, bool)

    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg
        self.view = dict(cfg)          # cfg + estilo automático da música (quando ligado)
        self.style_override = {}
        self.style_summary = None
        self.cover_bytes = None
        self.on_style_generated = None  # callback(resumo, permanente) para avisos
        self.snap = None
        self.track_id = None
        self.lines, self.windows = [], []
        self.status = ""
        self.album_color = None
        self.cover = None
        self.base_pos = 0.0
        self.base_stamp = time.monotonic()
        self.playing = False
        self.duration = 0.0
        self.demo = False
        self.edit = False
        self.hidden_by_user = False
        self._demo_lines = lyr.parse_lrc(demo_lrc())
        self._demo_wins = render.line_windows(self._demo_lines, cfg)
        self._demo_start = time.monotonic()
        self._retry_at = None

        self.lyrics_win = LyricsWindow(self, 0)
        self.lyrics_win2 = LyricsWindow(self, 1)   # segunda janela, só no modo aleatório
        self.widget_win = WidgetWindow(self)
        self._seed = random.random()
        self._disc_angle = 0.0
        self._last_tick = time.monotonic()
        self._rand_geo = {}
        self._cfg_version = 0
        self.lyrics_win.moved.connect(self._lyrics_moved)
        self.widget_win.moved.connect(self._widget_moved)
        self.media_signal.connect(self._on_media)
        self.lyrics_signal.connect(self._on_lyrics)
        self.style_signal.connect(self._on_style)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.top_timer = QTimer(self)
        self.top_timer.timeout.connect(self._keep_on_top)
        self.top_timer.start(2000)
        self.apply_config()

    # ------------------------------------------------------------ estado
    def song_time(self):
        if self.snap is None:
            return 0.0
        t = self.base_pos
        if self.playing:
            t += time.monotonic() - self.base_stamp
        if self.duration > 0:
            t = min(t, self.duration)
        return t

    def current_lyrics(self):
        if self.lines and self.snap is not None:
            return self.lines, self.windows, self.song_time() + float(self.cfg["sync_offset"])
        if self.demo or self.edit:
            t = (time.monotonic() - self._demo_start) % DEMO_LEN
            return self._demo_lines, self._demo_wins, t
        return [], [], 0.0

    def widget_info(self):
        info = render.WidgetInfo()
        info.disc_angle = self._disc_angle
        if self.snap is not None and self.snap.title:
            info.title = self.snap.title
            info.artist = self.snap.artist
            info.position = self.song_time()
            info.duration = self.duration
            info.playing = self.playing
            info.cover = self.cover
            info.status = tr(self.status) if self.status else ""
        elif self.demo or self.edit:
            info.title, info.artist = tr("widget.preview_title"), tr("widget.preview_artist")
            info.position = (time.monotonic() - self._demo_start) % DEMO_LEN
            info.duration = DEMO_LEN
            info.playing = True
        return info

    # ------------------------------------------------------------ mídia
    def on_media_thread(self, snap):
        self.media_signal.emit(snap)  # chamado da thread de mídia

    def _on_media(self, snap):
        now = time.monotonic()
        if not snap.title:
            self.snap = None
            self.track_id = None
            self.lines, self.windows, self.status = [], [], ""
            return
        new_pos = snap.position + (now - snap.stamp)
        predicted = self.song_time()
        changed = snap.track_id != self.track_id
        if changed or snap.playing != self.playing or abs(new_pos - predicted) > 0.7:
            self.base_pos, self.base_stamp = new_pos, now
        self.playing = snap.playing
        self.duration = snap.duration
        self.snap = snap
        if changed:
            self.track_id = snap.track_id
            self.lines, self.windows = [], []
            self.cover = render.cover_pixmap(snap.thumb)
            self.album_color = render.album_accent(snap.thumb)
            self.cover_bytes = snap.thumb
            self.style_override = {}
            self.style_summary = None
            self._fetch(snap)
        elif snap.thumb is not None and self.cover is None:
            self.cover = render.cover_pixmap(snap.thumb)
            self.album_color = render.album_accent(snap.thumb)
            self.cover_bytes = snap.thumb
        if self._retry_at and now > self._retry_at:
            self._retry_at = None
            self._fetch(snap)

    def _fetch(self, snap):
        self.status = "status.searching"
        tid, title, artist, album, dur = snap.track_id, snap.title, snap.artist, snap.album, snap.duration

        def work():
            try:
                lines, instrumental = lyr.fetch(title, artist, album, dur)
                if lines:
                    msg = ""
                elif instrumental:
                    msg = "status.instrumental"
                else:
                    msg = "status.missing"
            except lyr.LrclibBusy:
                lines, msg = None, "status.busy"
            self.lyrics_signal.emit(tid, lines, msg)

        threading.Thread(target=work, daemon=True).start()

    def _on_lyrics(self, tid, lines, msg):
        if tid != self.track_id:
            return
        if lines is None:
            self._retry_at = time.monotonic() + 15
            self.lines, self.windows = [], []
        else:
            self.lines = lines
            self.windows = render.line_windows(lines, self.view)
        self.status = msg
        if self.lines and self.duration <= 0:
            self.status = "status.no_time"
        if lines is not None and self.cfg.get("auto_style"):
            self.generate_style(permanent=False)

    # ------------------------------------------------------------ estilo da música
    def generate_style(self, permanent=True):
        """Cria um estilo para a música atual. permanent=True grava como o estilo do usuário."""
        if self.snap is None or not self.snap.title:
            if self.on_style_generated:
                self.on_style_generated(None, permanent)
            return False
        import autostyle
        tid, title, artist = self.track_id, self.snap.title, self.snap.artist
        lines, cover = list(self.lines), self.cover_bytes

        def work():
            try:
                fam = autostyle.artist_family(artist)
            except Exception:  # noqa: BLE001
                fam = None
            try:
                style, summary = autostyle.generate(title, artist, lines, cover, fam)
            except Exception as e:  # noqa: BLE001
                print("[autostyle]", repr(e))
                return
            self.style_signal.emit(tid, style, summary, permanent)

        threading.Thread(target=work, daemon=True).start()
        return True

    def _on_style(self, tid, style, summary, permanent):
        if tid != self.track_id:
            return
        self.style_summary = summary
        if permanent:
            self.cfg.update(style)
            self.cfg.save()
            self.style_override = {}
            self.config_changed_externally()
        else:
            self.style_override = style
        self.apply_config()
        if self.on_style_generated:
            self.on_style_generated(summary, permanent)

    # ------------------------------------------------------------ janelas
    def screen(self):
        screens = QGuiApplication.screens()
        i = int(self.cfg.get("screen_index", 0))
        return screens[i] if 0 <= i < len(screens) else QGuiApplication.primaryScreen()

    def apply_config(self):
        self.view = dict(self.cfg)
        if self.cfg.get("auto_style") and self.style_override:
            self.view.update(self.style_override)
        cfg = self.view
        if self.lines:
            self.windows = render.line_windows(self.lines, cfg)
        self._demo_lines = lyr.parse_lrc(demo_lrc())
        self._demo_wins = render.line_windows(self._demo_lines, cfg)
        geo = self.screen().geometry()
        size = float(cfg["text_size"])
        lw = int(float(cfg["line_width"]) + size * 5)
        lh = int(size * 9 + 80)
        lw, lh = min(lw, geo.width()), min(lh, geo.height())
        cx = geo.x() + float(cfg["lyrics_x"]) * geo.width()
        cy = geo.y() + float(cfg["lyrics_y"]) * geo.height()
        if not cfg["allow_center"]:
            # empurra o texto para cima ou para baixo da área livre do centro
            zone = self.center_zone()
            text_h = size * 2.6
            text_rect = QRect(int(cx - cfg["line_width"] / 2), int(cy - text_h / 2), int(cfg["line_width"]), int(text_h))
            if text_rect.intersects(zone):
                if cy >= zone.center().y():
                    cy = zone.bottom() + text_h / 2 + 8
                else:
                    cy = zone.top() - text_h / 2 - 8
        x = int(min(max(cx - lw / 2, geo.x()), geo.right() - lw))
        y = int(min(max(cy - lh / 2, geo.y()), geo.bottom() - lh))
        self._cfg_version += 1
        self._rand_geo.clear()
        rnd = cfg["position_mode"] == "random" and not self.edit
        for w in (self.lyrics_win, self.lyrics_win2):
            w.random_mode = rnd
        if not rnd:
            self.lyrics_win.setGeometry(x, y, lw, lh)

        s = float(cfg["widget_scale"])
        ww, wh = render.widget_size(cfg)
        ww, wh = int(ww + 2), int(wh + 2)
        m = 24
        pos = cfg["widget_position"]
        if pos == "top_left":
            wx, wy = geo.x() + m, geo.y() + m
        elif pos == "bottom_left":
            wx, wy = geo.x() + m, geo.bottom() - wh - m
        elif pos == "bottom_right":
            wx, wy = geo.right() - ww - m, geo.bottom() - wh - m
        elif pos == "custom":
            wx = int(geo.x() + float(cfg["widget_x"]) * geo.width() - ww / 2)
            wy = int(geo.y() + float(cfg["widget_y"]) * geo.height() - wh / 2)
        else:
            wx, wy = geo.right() - ww - m, geo.y() + m
        self.widget_win.setGeometry(wx, wy, ww, wh)
        self.timer.start(max(8, int(1000 / max(15, int(cfg["fps"])))))
        self._update_visibility()

    def center_zone(self):
        geo = self.screen().geometry()
        f = float(self.cfg["center_zone"])
        zh = geo.height() * f
        zw = zh * 1.3
        c = geo.center()
        return QRect(int(c.x() - zw / 2), int(c.y() - zh / 2), int(zw), int(zh))

    def _random_rect(self, index, text):
        """Lugar aleatório (mas fixo para esta linha) que não cai no centro proibido nem em cima do widget."""
        key = (self.track_id, index, text)
        if key in self._rand_geo:
            return self._rand_geo[key]
        cfg = self.view
        geo = self.screen().geometry()
        ww, wh = render.content_size(cfg, text, index)
        ww, wh = int(min(ww, geo.width())), int(min(wh, geo.height()))
        m = int(min(geo.width(), geo.height()) * 0.03)
        avoid = []
        if not cfg["allow_center"]:
            avoid.append(self.center_zone())
        if cfg["show_widget"]:
            avoid.append(self.widget_win.geometry().adjusted(-12, -12, 12, 12))
        prev = self._rand_geo.get((self.track_id, index - 1, None))
        if prev is not None:
            avoid.append(prev)
        rng = random.Random(f"{self._seed}|{key}")
        best, best_overlap = None, None
        for _ in range(80):
            x = rng.randint(geo.x() + m, max(geo.x() + m, geo.right() - ww - m))
            y = rng.randint(geo.y() + m, max(geo.y() + m, geo.bottom() - wh - m))
            r = QRect(x, y, ww, wh)
            # o que conta é o texto, não a margem transparente da janela
            core = r.adjusted(int(ww * 0.12), int(wh * 0.18), -int(ww * 0.12), -int(wh * 0.18))
            overlap = sum(core.intersected(a).width() * core.intersected(a).height() for a in avoid)
            if best is None or overlap < best_overlap:
                best, best_overlap = r, overlap
            if overlap == 0:
                break
        self._rand_geo[key] = best
        self._rand_geo[(self.track_id, index, None)] = best
        return best

    def _place_random(self):
        lines, _wins, t = self.current_lyrics()
        if not lines:
            return
        f = render.compute_frame(lines, _wins, t, self.view, self.view.get("layout") == "stack")
        k = f.idx
        for win in (self.lyrics_win, self.lyrics_win2):
            p = win.parity
            i = k if (k >= 0 and k % 2 == p) else k - 1
            if k < 0:
                i = 0 if p == 0 else -1
            if i < 0 or i >= len(lines):
                continue
            r = self._random_rect(i, lines[i].text)
            if win.geometry() != r:
                win.setGeometry(r)

    def _lyrics_moved(self, center):
        geo = self.screen().geometry()
        self.cfg["lyrics_x"] = round((center.x() - geo.x()) / geo.width(), 4)
        self.cfg["lyrics_y"] = round((center.y() - geo.y()) / geo.height(), 4)
        self.cfg.save()

    def _widget_moved(self, center):
        geo = self.screen().geometry()
        self.cfg["widget_position"] = "custom"
        self.cfg["widget_x"] = round((center.x() - geo.x()) / geo.width(), 4)
        self.cfg["widget_y"] = round((center.y() - geo.y()) / geo.height(), 4)
        self.cfg.save()
        self.config_changed_externally()

    def config_changed_externally(self):
        pass  # substituído pela janela de configurações para atualizar os campos

    def set_edit(self, on):
        self.edit = on
        self.lyrics_win.set_edit(on)
        self.widget_win.set_edit(on)
        self.apply_config()

    def toggle_edit(self):
        self.set_edit(not self.edit)

    def toggle_hidden(self):
        self.hidden_by_user = not self.hidden_by_user
        self._update_visibility()

    def _update_visibility(self):
        cfg = self.cfg
        has_track = self.snap is not None and bool(self.snap.title)
        paused_hide = has_track and cfg["hide_paused"] and not self.playing and not self.edit
        base = not self.hidden_by_user and not paused_hide
        show_l = base and cfg["show_lyrics"] and (has_track or self.demo or self.edit)
        show_w = base and cfg["show_widget"] and (has_track or self.demo or self.edit)
        show_l2 = show_l and self.cfg["position_mode"] == "random" and not self.edit
        for win, show in ((self.lyrics_win, show_l), (self.lyrics_win2, show_l2), (self.widget_win, show_w)):
            if show and not win.isVisible():
                win.show()
            elif not show and win.isVisible():
                win.hide()

    def _keep_on_top(self):
        for w in (self.lyrics_win, self.lyrics_win2, self.widget_win):
            if w.isVisible():
                winutil.force_topmost(w)

    def _tick(self):
        now = time.monotonic()
        dt_ = min(0.2, now - self._last_tick)
        self._last_tick = now
        spinning = (self.snap is not None and self.playing) or ((self.demo or self.edit) and self.snap is None)
        if spinning:
            self._disc_angle = (self._disc_angle + dt_ * 100.0) % 360.0  # ~33 rpm, como um vinil
        self._update_visibility()
        if self.lyrics_win.random_mode:
            self._place_random()
            if self.lyrics_win2.isVisible():
                self.lyrics_win2.update()
        if self.lyrics_win.isVisible():
            self.lyrics_win.update()
        if self.widget_win.isVisible():
            self.widget_win.update()

    def shutdown(self):
        self.timer.stop()
        self.lyrics_win.close()
        self.lyrics_win2.close()
        self.widget_win.close()
