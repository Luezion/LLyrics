"""Desenho da letra (animações, karaokê, contorno, brilho) e do widget "tocando agora"."""
import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QBrush, QColor, QFont, QFontDatabase, QFontMetricsF, QImage,
                           QLinearGradient, QPainter, QPainterPath, QPen, QPixmap, QTransform)

from config import ACCENTS, FONTS, RAINBOW, resource_path
from i18n import tr

ENTER = 0.38     # segundos de animação de entrada
EXIT = 0.32      # saída
ERASE = 0.28     # apagar da máquina de escrever
PREV_FADE = 1.4  # quanto tempo a linha anterior fica esmaecida


def clamp(v, a=0.0, b=1.0):
    return a if v < a else b if v > b else v


def ease_out(x):
    return 1 - (1 - x) ** 3


def ease_out_back(x, s=1.9):
    x -= 1
    return 1 + (s + 1) * x ** 3 + s * x ** 2


def fmt_time(s):
    s = max(0, int(s))
    return f"{s // 60}:{s % 60:02d}"


# ----------------------------------------------------------------- fontes
_families = {}


def load_fonts():
    for key, _name, files in FONTS:
        fam = None
        for fn in files:
            fid = QFontDatabase.addApplicationFont(resource_path("fonts", fn))
            if fid >= 0 and fam is None:
                fams = QFontDatabase.applicationFontFamilies(fid)
                fam = fams[0] if fams else None
        _families[key] = fam or "Segoe UI"


def family(key):
    return _families.get(key) or "Segoe UI"


# ----------------------------------------------------------------- cores
def album_accent(image_bytes):
    """Cor mais forte da capa, clareada para ficar legível sobre o jogo."""
    if not image_bytes:
        return None
    img = QImage()
    if not img.loadFromData(image_bytes):
        return None
    img = img.scaled(36, 36, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
    bins = [[0.0, 0.0, 0.0, 0.0] for _ in range(18)]  # peso, r, g, b
    for y in range(img.height()):
        for x in range(img.width()):
            c = img.pixelColor(x, y)
            h, s, v = c.hsvHueF(), c.hsvSaturationF(), c.valueF()
            if h < 0 or s < 0.25 or v < 0.25:
                continue
            w = s * s * v
            b = bins[int(h * 18) % 18]
            b[0] += w
            b[1] += c.redF() * w
            b[2] += c.greenF() * w
            b[3] += c.blueF() * w
    best = max(bins, key=lambda b: b[0])
    if best[0] < 1.5:
        return None
    col = QColor.fromRgbF(best[1] / best[0], best[2] / best[0], best[3] / best[0])
    h, s, v = col.hsvHueF(), col.hsvSaturationF(), col.valueF()
    return QColor.fromHsvF(h, min(s, 0.62), max(v, 0.95))


def accent_for(cfg, album_color, line_index):
    a = cfg["accent"]
    if a == "album":
        return QColor(album_color) if album_color else QColor(ACCENTS["cream"])
    if a == "rainbow":
        return QColor(RAINBOW[line_index % len(RAINBOW)])
    if a == "custom":
        c = QColor(cfg.get("custom_colour") or "#ffffff")
        return c if c.isValid() else QColor("#ffffff")
    return QColor(ACCENTS.get(a, "#ffffff"))


def with_alpha(c, a):
    c = QColor(c)
    c.setAlphaF(clamp(c.alphaF() * a))
    return c


# ----------------------------------------------------------------- tempo das linhas
def line_windows(lines, cfg):
    """Para cada linha: (início, fim_visível, início_próxima)."""
    out = []
    for i, ln in enumerate(lines):
        s = ln.time
        nxt = lines[i + 1].time if i + 1 < len(lines) else None
        est = max(2.6, len(ln.text) * 0.085 + 1.3)
        gap_end = ln.end if ln.end is not None else (nxt if nxt is not None else s + est + 2)
        limit = nxt if nxt is not None else s + est + 2.5
        if cfg["countdown"] and limit - s > est + 4.0:
            hide = min(max(gap_end, s + 1.2), s + est)
        elif cfg["countdown"] and gap_end < limit - 4.0:
            hide = max(gap_end, s + 1.2)
        else:
            hide = limit
        if cfg.get("exit_animation", "auto") != "auto" and nxt is not None and nxt - hide < 0.3:
            # a saída começa um pouco antes, para não embolar com a próxima linha
            hide = max(s + 0.6, hide - min(0.55, (hide - s) * 0.25))
        out.append((s, hide, nxt))
    return out


class Frame:
    """Tudo que é preciso para desenhar a letra num instante."""

    def __init__(self):
        self.current = None     # (index, line, start, hide)
        self.leaving = []       # [(index, line, start, hide)] em saída
        self.previous = None    # (index, line, alpha)
        self.next_text = None
        self.countdown = None   # (progress, alpha)
        self.idx = -1           # última linha que já começou


def compute_frame(lines, windows, t, cfg, stack=False):
    prev_on = cfg["previous_line"] and not stack and cfg.get("exit_animation", "auto") == "auto"
    f = Frame()
    if not lines:
        return f
    # índice da última linha que já começou
    idx = -1
    lo, hi = 0, len(lines) - 1
    while lo <= hi:
        mid = (lo + hi) // 2
        if lines[mid].time <= t:
            idx = mid
            lo = mid + 1
        else:
            hi = mid - 1

    f.idx = idx
    if idx >= 0:
        s, hide, nxt = windows[idx]
        if t < hide:
            f.current = (idx, lines[idx], s, hide)
        elif t < hide + exit_duration(cfg) and (not prev_on or nxt is None or nxt - hide > 0.5):
            f.leaving.append((idx, lines[idx], s, hide))
        if nxt is not None and t >= hide + 0.25 and nxt - hide > 3.0 and cfg["countdown"]:
            span = nxt - (hide + 0.25)
            prog = clamp((t - hide - 0.25) / span)
            alpha = clamp((t - hide - 0.25) / 0.3) * clamp((nxt - t) / 0.25)
            f.countdown = (prog, alpha)
        # linha anterior: esmaecida acima da atual
        if idx >= 1 and prev_on and f.current is not None:
            ps, phide, _ = windows[idx - 1]
            since = t - s
            if phide >= s - 0.6 and since < PREV_FADE:
                f.previous = (idx - 1, lines[idx - 1], 1.0 - ease_out(clamp(since / PREV_FADE)))
        # a linha anterior também sai normalmente se não houver "linha anterior"
        if idx >= 1 and not prev_on:
            ps, phide, _ = windows[idx - 1]
            if phide <= t < phide + exit_duration(cfg):
                f.leaving.append((idx - 1, lines[idx - 1], ps, phide))
        if cfg["preview"] and not stack and idx + 1 < len(lines) and f.current is not None:
            f.next_text = lines[idx + 1].text
    else:
        first = lines[0].time
        if cfg["countdown"] and first > 4.0 and t > 0.4:
            f.countdown = (clamp((t - 0.4) / (first - 0.4)), clamp((t - 0.4) / 0.3) * clamp((first - t) / 0.25))
        if cfg["preview"] and not stack:
            f.next_text = lines[0].text
    return f


# ----------------------------------------------------------------- texto
_glyph_cache = {}

LITTLE_WORDS = set("""
a o e é as os um uma uns umas de do da dos das no na nos nas em ao à aos às por pra pro pras pros
que se me te lhe nos vos eu tu ele ela eles elas você vocês meu minha teu tua seu sua mas nem ou
com sem só já vai vou tá tô é
the and you your got was for but not are his her its our i'm im i'll i'd ain't can all too yeah
they she him them this from that's it's don't to of in on at is my me we be so oh
el la los las un una y en con por para mi tu su lo le
""".split())


def glyph_path(font, ch):
    key = (font.key(), ch)
    p = _glyph_cache.get(key)
    if p is None:
        p = QPainterPath()
        p.addText(0, 0, font, ch)
        if len(_glyph_cache) > 4000:
            _glyph_cache.clear()
        _glyph_cache[key] = p
    return p


class TextStyle:
    def __init__(self, cfg, scale=1.0):
        self.cfg = cfg
        size = max(8.0, float(cfg["text_size"]) * scale)
        self.font = QFont(family(cfg["font"]))
        self.font.setPixelSize(int(round(size)))
        self.font.setBold(bool(cfg["bold"]))
        self.font.setLetterSpacing(QFont.AbsoluteSpacing, float(cfg["letter_spacing"]) * scale)
        self.font.setHintingPreference(QFont.PreferNoHinting)
        self.fm = QFontMetricsF(self.font)
        self.size = size
        self.row_h = self.fm.height()
        self.gap = float(cfg["line_spacing"]) * scale + size * 0.12
        self.max_w = float(cfg["line_width"]) * scale

    def prep(self, text):
        return text.upper() if self.cfg["uppercase"] else text

    def wrap(self, text):
        words = text.split()
        rows, cur = [], ""
        for w in words:
            trial = (cur + " " + w) if cur else w
            if cur and self.fm.horizontalAdvance(trial) > self.max_w:
                rows.append(cur)
                cur = w
            else:
                cur = trial
        if cur:
            rows.append(cur)
        return rows or [""]

    def block_height(self, rows):
        return len(rows) * self.row_h + (len(rows) - 1) * self.gap


def _hsl(h, s, l):
    return QColor.fromHslF((h % 360) / 360.0, s, l)


def mix(a, b, t):
    return QColor.fromRgbF(a.redF() + (b.redF() - a.redF()) * t,
                           a.greenF() + (b.greenF() - a.greenF()) * t,
                           a.blueF() + (b.blueF() - a.blueF()) * t)


def glyph_colour(cfg, accent, i, n, now):
    mode = cfg.get("colour_mode", "solid")
    if mode in ("gradient", "gradient3"):
        second = QColor(cfg.get("second_colour") or "#DB9BE0")
        k = i / (n - 1) if n > 1 else 0
        if mode == "gradient":
            return mix(accent, second, k)
        third = QColor(cfg.get("third_colour") or "#8FC9F2")
        return mix(accent, second, k * 2) if k < 0.5 else mix(second, third, (k - 0.5) * 2)
    if mode == "rainbow_flow":
        return _hsl(now * 90 * float(cfg.get("idle_speed", 1.0) or 1) - i * 14, 0.72, 0.76)
    return accent


class Glyph:
    __slots__ = ("ch", "x", "y", "alpha", "i", "word", "font", "scale", "cx", "cy", "rot", "rx", "ry")

    def __init__(self):
        self.scale, self.cx, self.cy, self.rot, self.rx, self.ry = 1.0, 0.0, 0.0, 0.0, 0.0, 0.0


def _idle_offset(cfg, g, now, size):
    """Movimento parado (enquanto a linha está na tela), por letra."""
    idle = cfg.get("idle", "none")
    amp = float(cfg.get("idle_strength", 1.0))
    spd = max(0.05, float(cfg.get("idle_speed", 1.0)))
    if idle == "shake":
        period = 0.2 / spd
        phase = ((now + g.i * 0.05) / period) % 1.0
        d = size * 0.045 * amp * (1 if phase < 0.5 else -1)
        return d, -d
    if idle == "wave":
        ph = (now + g.i * 0.07) / (1.2 / spd)
        return 0.0, math.sin(ph * 2 * math.pi) * size * 0.1 * amp
    return 0.0, 0.0


def _block_idle(p, cfg, now, cx, cy, size):
    idle = cfg.get("idle", "none")
    amp = float(cfg.get("idle_strength", 1.0))
    spd = max(0.05, float(cfg.get("idle_speed", 1.0)))
    if idle == "pulse":
        k = 1 + 0.06 * amp * (0.5 - 0.5 * math.cos(now * 2 * math.pi / (1.1 / spd)))
        p.translate(cx, cy)
        p.scale(k, k)
        p.translate(-cx, -cy)
    elif idle == "float":
        p.translate(0, math.sin(now * 2 * math.pi / (2.6 / spd)) * size * 0.12 * amp)
    elif idle == "sway":
        p.translate(cx, cy)
        p.rotate(math.sin(now * 2 * math.pi / (2.4 / spd)) * 3 * amp)
        p.translate(-cx, -cy)
    elif idle == "bounce":
        ph = (now / (1.0 / spd)) % 1.0
        hop = 0.0
        if 0.7 < ph < 0.94:
            hop = math.sin((ph - 0.7) / 0.24 * math.pi)
        p.translate(0, -hop * size * 0.22 * amp)


def _paint_glyphs(p, st, glyphs, colours, alphas, karaoke, cfg, accent):
    """Desenha letras em camadas: brilho, sombra, contorno e preenchimento.
    karaoke: (cantadas, total) ou None."""
    items = []
    for g, col, a in zip(glyphs, colours, alphas):
        if a <= 0.003 or g.ch == " ":
            continue
        path = glyph_path(g.font or st.font, g.ch)
        tr = QTransform()
        tr.translate(g.x, g.y)
        if g.scale != 1.0:
            tr = QTransform()
            tr.translate(g.cx, g.cy)
            tr.scale(g.scale, g.scale)
            tr.translate(g.x - g.cx, g.y - g.cy)
        if g.rot:
            rt = QTransform()
            rt.translate(g.rx, g.ry)
            rt.rotate(g.rot)
            rt.translate(-g.rx, -g.ry)
            tr = tr * rt
        items.append((g, tr.map(path), col, a))
    if not items:
        return
    size = st.size
    if cfg["glow"]:
        for w, ga in ((size * 0.42, 0.07), (size * 0.24, 0.10), (size * 0.11, 0.14)):
            for g, path, col, a in items:
                p.strokePath(path, QPen(with_alpha(col, ga * a), w * g.scale, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    if cfg["drop_shadow"]:
        off = max(1.5, size * 0.06)
        for g, path, col, a in items:
            sh = QColor.fromRgbF(col.redF() * 0.22, col.greenF() * 0.22, col.blueF() * 0.22)
            sh.setAlphaF(0.85 * a)
            p.fillPath(path.translated(off * g.scale, off * g.scale), sh)
    if cfg["outline"]:
        oc = QColor(cfg.get("outline_colour") or "#000000")
        width = max(1.2, size * 0.085 * float(cfg["outline_thickness"]))
        for g, path, col, a in items:
            p.strokePath(path, QPen(with_alpha(oc, 0.95 * a), width * g.scale, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
    for g, path, col, a in items:
        if karaoke is None:
            p.fillPath(path, with_alpha(col, a))
            continue
        sung, _total = karaoke
        dim = QColor(col)
        dim.setHsvF(max(0.0, dim.hsvHueF()), dim.hsvSaturationF(), dim.valueF() * 0.45)
        dim.setAlphaF(0.92 * a)
        if g.i + 1 <= sung:
            p.fillPath(path, with_alpha(col, a))
        elif g.i >= sung:
            p.fillPath(path, dim)
        else:
            p.fillPath(path, dim)
            r = path.boundingRect()
            frac = sung - g.i
            p.save()
            p.setClipRect(QRectF(r.x() - 2, r.y() - size, (r.width() + 2) * frac + 2, r.height() + size * 2),
                          Qt.IntersectClip)
            p.fillPath(path, with_alpha(col, a))
            p.restore()


def _timing(text, start, hide):
    since_total = max(0.6, hide - start)
    est = max(2.6, len(text) * 0.085 + 1.3)
    sung = min(since_total, est * 1.3)
    return since_total, est, sung


def line_rows(st, text, layout):
    """Linhas de texto e a escala de cada uma. 'words'/'words_tilted': primeira palavra sozinha e maior."""
    text = st.prep(text)
    if layout in ("words", "words_tilted"):
        parts = text.split(" ", 1)
        if len(parts) == 2 and parts[1].strip():
            k = 1.5 if layout == "words" else 1.45
            return [(parts[0], k)] + [(r, 1.0) for r in st.wrap(parts[1])]
    return [(r, 1.0) for r in st.wrap(text)]


def rows_height(st, rows):
    return sum(st.row_h * k for _, k in rows) + (len(rows) - 1) * st.gap


def exit_duration(cfg):
    return 1.1 if cfg.get("exit_animation") == "drift" else EXIT * 1.6


def _tilt(wi):
    return ((wi * 37) % 11) - 5


def draw_line(p, st, text, cx, cy, t, start, hide, accent, cfg, mode="current", alpha_mult=1.0,
              now=0.0, line_index=0):
    """Layout de linhas: desenha uma linha de letra centrada em (cx, cy)."""
    layout = cfg.get("layout", "lines")
    if mode in ("previous", "preview"):
        layout = "lines"
    rows = line_rows(st, text, layout)
    ptext = st.prep(text)
    total = sum(len(r) for r, _ in rows) + max(0, len(rows) - 1)
    bh = rows_height(st, rows)
    top = cy - bh / 2
    anim = cfg["animation"]
    exit_anim = cfg.get("exit_animation", "auto")
    since = t - start
    enter = clamp(since / ENTER)
    sung_window, est, sung_dur = _timing(ptext, start, hide)
    leaving = mode == "leaving"
    static = mode in ("previous", "preview")
    ex = clamp((t - hide) / EXIT) if leaving and exit_anim != "drift" else 0.0
    if leaving and exit_anim == "fade":
        anim_exit_alpha, ex = 1 - ex, 0.0   # só esmaece; a entrada não "volta"
    else:
        anim_exit_alpha = 1.0

    alpha = alpha_mult * anim_exit_alpha
    dy = 0.0
    scale = 1.0
    visible = total
    if static:
        pass
    elif anim == "typewriter":
        if cfg["typewriter_sync"]:
            dur = max(0.25, sung_dur * 0.82)
        else:
            dur = min(total / (26.0 * max(0.2, float(cfg["typewriter_speed"]))), sung_window * 0.6)
        visible = int(total * clamp(since / dur)) if dur > 0 else total
        if mode == "current" and not cfg["previous_line"] and exit_anim == "auto":
            visible = int(visible * (1 - clamp((t - (hide - ERASE)) / ERASE)))
        if leaving:
            visible = 0 if exit_anim == "auto" else total
    elif anim == "drop":
        dy = (-1 + ease_out(enter)) * st.size * 0.9 + (ease_out(ex) * st.size * 0.9 if leaving else 0)
        alpha *= enter * (1 - ex)
    elif anim == "rise":
        dy = (1 - ease_out(enter)) * st.size * 0.9 - (ease_out(ex) * st.size * 0.9 if leaving else 0)
        alpha *= enter * (1 - ex)
    elif anim == "fade":
        alpha *= ease_out(enter) * (1 - ex)
    elif anim == "pop":
        scale = (0.55 + 0.45 * ease_out_back(enter) if enter < 1 else 1.0) * (1 - 0.15 * ex)
        alpha *= clamp(enter * 2.5) * (1 - ex)
    else:
        alpha *= (1 - ex)
    if alpha <= 0.003 or visible <= 0:
        return bh

    glyphs, alphas = [], []
    gi = 0
    word = 0
    n_words = max(1, len(ptext.split()))
    step = min(0.22, max(0.06, sung_window * 0.5 / n_words))
    tilted = layout == "words_tilted"
    y_acc = top
    for row, k in rows:
        adv_row = st.fm.horizontalAdvance(row)
        x0 = cx - adv_row / 2
        base = y_acc + st.fm.ascent() * k + dy
        y_acc += st.row_h * k + st.gap
        # centro de cada palavra (para a inclinação)
        wstart = 0
        word_centers = {}
        for wtxt in row.split(" "):
            wx = x0 + st.fm.horizontalAdvance(row[:wstart])
            wmid = wx + st.fm.horizontalAdvance(wtxt) / 2
            word_centers[wstart] = (cx + (wmid - cx) * k, base - st.fm.ascent() * k * 0.35)
            wstart += len(wtxt) + 1
        cur_wc = word_centers.get(0)
        for ci, ch in enumerate(row):
            if ci in word_centers:
                cur_wc = word_centers[ci]
            g = Glyph()
            g.ch, g.i, g.word, g.font = ch, gi, word, None
            g.scale, g.cx, g.cy = k, cx, base
            g.x = x0 + st.fm.horizontalAdvance(row[:ci])
            g.y = base
            g.rot, g.rx, g.ry = (_tilt(word), cur_wc[0], cur_wc[1]) if tilted else (0.0, 0.0, 0.0)
            a = alpha
            if not static:
                if anim == "typewriter":
                    a = alpha if gi < visible else 0.0
                elif anim == "words":
                    wt = clamp((since - word * step) / 0.22)
                    g.y -= math.sin(wt * math.pi) * st.size * 0.18
                    a = alpha * clamp(wt * 2)
                elif anim in ("wave", "wave_down"):
                    ct = clamp((since - gi * 0.022) / 0.28)
                    g.y += (1 - ease_out_back(ct, 2.2)) * st.size * 0.45 * (1 if anim == "wave" else -1)
                    a = alpha * clamp(ct * 2)
                if leaving and exit_anim == "drift":
                    e = clamp((t - hide - gi * min(0.022, 0.45 / max(1, total))) / 0.6)
                    e = e * e
                    g.x += st.size * 0.7 * e / k
                    g.y -= st.size * 0.3 * e / k
                    gcx = cx + (g.x + st.fm.horizontalAdvance(ch) / 2 - cx) * k
                    g.rot, g.rx, g.ry = g.rot + 10 * e, gcx, base - st.fm.ascent() * k * 0.35
                    a *= 1 - e
                ox, oy = _idle_offset(cfg, g, now, st.size)
                g.x += ox
                g.y += oy
            glyphs.append(g)
            alphas.append(a)
            if ch == " ":
                word += 1
            gi += 1
        gi += 1  # espaço da quebra de linha
        word += 1

    if mode == "preview":
        colours = [accent] * len(glyphs)
    else:
        colours = [glyph_colour(cfg, accent, g.i, total, now) for g in glyphs]
    karaoke = None
    if cfg["karaoke"] and mode == "current":
        karaoke = (clamp(since / (sung_dur * 0.92)) * total, total)
    if mode == "previous":
        alphas = [a * 0.45 for a in alphas]

    p.save()
    if not static:
        _block_idle(p, cfg, now, cx, cy, st.size)
    if scale != 1.0:
        p.translate(cx, cy)
        p.scale(scale, scale)
        p.translate(-cx, -cy)
    _paint_glyphs(p, st, glyphs, colours, alphas, karaoke, cfg, accent)
    p.restore()
    return bh


# ----------------------------------------------------------------- layout pilha
def _rng(text, index):
    h = 2166136261
    for c in f"{text}#{index}":
        h = ((h ^ ord(c)) * 16777619) & 0xFFFFFFFF

    def r():
        nonlocal h
        h = (h * 1664525 + 1013904223) & 0xFFFFFFFF
        return h / 4294967296.0
    return r


_stack_cache = {}


def stack_layout(st, text, index, max_w, max_h):
    """Palavras pequenas pequenas, as que carregam a linha grandes, encaixadas umas nas outras.
    Devolve [(palavra, escala, centro_x, centro_y)] relativos ao centro, já ajustados ao espaço."""
    key = (text, index, st.font.key(), int(max_w), int(max_h))
    if key in _stack_cache:
        return _stack_cache[key]
    rnd = _rng(text, index)
    words = st.prep(text).split()
    n = len(words)
    if n == 0:
        return []
    widths = [max(1.0, st.fm.horizontalAdvance(w)) for w in words]
    hgt = st.fm.ascent() + st.fm.descent() * 0.3
    small = []
    for w in words:
        bare = "".join(c for c in w.lower() if c.isalnum() or c == "'")
        small.append(n > 1 and (len(bare) <= 2 or bare in LITTLE_WORDS) and rnd() >= 0.2)
    longest = max((i for i in range(n) if not small[i]), key=lambda i: widths[i], default=0)
    scale = []
    for i, w in enumerate(words):
        clause = w[-1:] in ",.!?"
        big = (n == 1 or i == longest or (i == n - 1 and not small[i])
               or (not small[i] and clause and rnd() < 0.9) or (not small[i] and rnd() < 0.3))
        scale.append(0.62 + rnd() * 0.12 if small[i] else 1.75 + rnd() * 0.45 if big else 0.95 + rnd() * 0.3)
    if small[0]:
        small[0] = False
        scale[0] = 0.95 + rnd() * 0.3

    size = st.size
    gap_base = size * 0.3
    row_gap = size * 0.02
    area = sum((widths[i] * scale[i] + gap_base) * hgt * scale[i] for i in range(n))
    widest = max(widths[i] * scale[i] for i in range(n))
    target = max(widest, math.sqrt(area * 2.2))
    boxes = [(-widths[0] * scale[0] / 2, -hgt * scale[0] / 2, widths[0] * scale[0], hgt * scale[0])]
    minx, miny, maxx, maxy = boxes[0][0], boxes[0][1], -boxes[0][0], -boxes[0][1]

    def touches(x, y, w, h):
        for bx, by, bw, bh in boxes:
            if x < bx + bw - 0.5 and x + w > bx + 0.5 and y < by + bh - 0.5 and y + h > by + 0.5:
                return True
        return False

    for i in range(1, n):
        w, h = widths[i] * scale[i], hgt * scale[i]
        gap = gap_base * min(1.5, max(scale[i], scale[i - 1]))
        pair = small[i] and small[i - 1]
        best, best_score = None, 1e18
        for j, (bx, by, bw, bh) in enumerate(boxes):
            prev = j == i - 1
            right, left = bx + bw + gap, bx - gap - w
            below, above = by + bh + row_gap, by - row_gap - h
            spots = [
                (right, by + bh - h, 0 if prev else 1.6), (right, by, 0.2 if prev else 1.6),
                (bx, below, (-0.4 if pair else 1) if prev else 1.6), (bx + bw - w, below, 1 if prev else 1.6),
                (bx + (bw - w) / 2, below, 1.2 if prev else 1.6),
                (left, by + bh - h, 2.2 if prev else 2.1), (left, by, 2.2 if prev else 2.1),
                (bx, above, (0.2 if pair else 2.2) if prev else 2.1), (bx + bw - w, above, 2.2 if prev else 2.1),
            ]
            for x, y, cost in spots:
                if touches(x, y, w, h):
                    continue
                nx, ny = min(minx, x), min(miny, y)
                wide, tall = max(maxx, x + w) - nx, max(maxy, y + h) - ny
                growth = (wide * tall - (maxx - minx) * (maxy - miny)) / (size * size)
                score = cost + 0.08 * growth + rnd() * 0.6
                if wide > target * 1.1:
                    score += 4 * (wide - target * 1.1) / size
                if score < best_score:
                    best_score, best = score, (x, y, w, h)
        b = best or (minx, maxy + row_gap, w, h)
        boxes.append(b)
        minx, miny = min(minx, b[0]), min(miny, b[1])
        maxx, maxy = max(maxx, b[0] + w), max(maxy, b[1] + h)

    fit = min(1.0, max_w * 0.92 / max(1.0, maxx - minx), max_h * 0.86 / max(1.0, maxy - miny))
    midx, midy = (minx + maxx) / 2, (miny + maxy) / 2
    out = []
    for i, (bx, by, bw, bh) in enumerate(boxes):
        out.append((words[i], scale[i] * fit, (bx + bw / 2 - midx) * fit, (by + bh / 2 - midy) * fit))
    if len(_stack_cache) > 200:
        _stack_cache.clear()
    _stack_cache[key] = out
    return out


def draw_stack(p, st, text, w, h, t, start, hide, accent, cfg, index, now, leaving=False, box=None):
    layout = stack_layout(st, text, index, *(box or (w, h)))
    if not layout:
        return None
    since = t - start
    _, _, sung_dur = _timing(text, start, hide)
    n = len(layout)
    step = clamp(sung_dur * 0.75 / max(1, n), 0.12, 0.45)
    ex = clamp((t - hide) / (EXIT * 1.6)) if leaving else 0.0
    total = sum(len(wd) for wd, *_ in layout) + n - 1
    glyphs, alphas, word_alpha = [], [], []
    gi = 0
    cx0, cy0 = w / 2, h / 2
    bbox = None
    for wi, (word, sc, ox, oy) in enumerate(layout):
        wt = clamp((since - wi * step) / 0.14)
        pop = 1.0 if wt >= 1 else 0.7 + 0.3 * ease_out_back(wt, 2.4)
        a = wt * (1 - ex)
        ww = st.fm.horizontalAdvance(word)
        wx = cx0 + ox - ww * sc / 2
        base = cy0 + oy + (st.fm.ascent() - st.fm.descent() * 0.35) * sc / 2
        r = QRectF(cx0 + ox - ww * sc / 2, cy0 + oy - st.fm.ascent() * sc / 2, ww * sc, st.fm.ascent() * sc)
        bbox = r if bbox is None else bbox.united(r)
        for ci, ch in enumerate(word):
            g = Glyph()
            g.ch, g.i, g.word, g.font = ch, gi, wi, None
            g.scale = sc * pop
            g.cx, g.cy = cx0 + ox, cy0 + oy
            g.x = wx + st.fm.horizontalAdvance(word[:ci]) * sc
            g.y = base
            # o pop é aplicado em volta do centro da palavra; x/y já incluem a escala, então desfaz
            g.x = g.cx + (g.x - g.cx) / sc if sc else g.x
            g.y = g.cy + (g.y - g.cy) / sc if sc else g.y
            ox_i, oy_i = _idle_offset(cfg, g, now, st.size * sc)
            g.x += ox_i / sc
            g.y += oy_i / sc
            glyphs.append(g)
            alphas.append(a)
            gi += 1
        gi += 1
    colours = [glyph_colour(cfg, accent, g.i, total, now) for g in glyphs]
    karaoke = None
    if cfg["karaoke"] and not leaving:
        karaoke = (clamp(since / (sung_dur * 0.92)) * total, total)
    p.save()
    _block_idle(p, cfg, now, cx0, cy0, st.size)
    _paint_glyphs(p, st, glyphs, colours, alphas, karaoke, cfg, accent)
    p.restore()
    done_at = start + (n - 1) * step + 0.14
    return bbox, done_at


def stack_box_for(cfg):
    size = float(cfg["text_size"])
    return float(cfg["line_width"]) + size * 2, size * 7


def content_size(cfg, text, index):
    """Tamanho da janela necessária para uma linha (posição aleatória)."""
    st = TextStyle(cfg)
    pad = st.size * 1.3
    if cfg.get("layout") == "stack":
        box = stack_box_for(cfg)
        lay = stack_layout(st, text, index, *box)
        if not lay:
            return pad * 2, pad * 2
        hgt = st.fm.ascent() + st.fm.descent() * 0.3
        xs, ys = [], []
        for word, sc, ox, oy in lay:
            ww = st.fm.horizontalAdvance(word) * sc / 2
            hh = hgt * sc / 2
            xs += [ox - ww, ox + ww]
            ys += [oy - hh, oy + hh]
        # a pilha é desenhada centrada na janela, então usa o maior lado a partir do centro
        bw = 2 * max(abs(v) for v in xs)
        bh = 2 * max(abs(v) for v in ys)
        return bw + pad * 2, bh + pad * 2
    rows = line_rows(st, text, cfg.get("layout"))
    bw = max(st.fm.horizontalAdvance(r) * k for r, k in rows)
    return bw + pad * 2, rows_height(st, rows) + pad * 2


# ----------------------------------------------------------------- efeitos
def _star_path(cx, cy, r):
    path = QPainterPath()
    pts = []
    for k in range(8):
        ang = k * math.pi / 4 - math.pi / 2
        rr = r if k % 2 == 0 else r * 0.28
        pts.append(QPointF(cx + math.cos(ang) * rr, cy + math.sin(ang) * rr))
    path.moveTo(pts[0])
    for q in pts[1:]:
        path.lineTo(q)
    path.closeSubpath()
    return path


def draw_sparkles(p, rect, since_done, cfg, seed_text, size):
    if since_done < 0 or rect is None:
        return
    amount = clamp(float(cfg.get("sparkle_amount", 1.0)), 0.5, 4.0)
    count = max(1, round(4 * amount))
    rnd = _rng(seed_text, 7)
    for k in range(count):
        x = rect.x() + (0.08 + rnd() * 0.84) * rect.width()
        y = rect.y() + rnd() * 0.85 * rect.height()
        delay = k * 1.8 / count
        ph = ((since_done - delay) / 1.6)
        if ph < 0:
            continue
        ph %= 1.0
        a = math.sin(ph * math.pi)
        r = size * 0.34 * (0.3 + 0.7 * a)
        p.save()
        p.translate(x, y)
        p.rotate(45 * ph)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(255, 255, 255, int(235 * a)))
        p.drawPath(_star_path(0, 0, r))
        p.restore()


_PARTY_COLOURS = ["#F2879B", "#FF8360", "#F2B33D", "#7FE0BD", "#8FC9F2", "#B3A5F0", "#DB9BE0"]


def draw_party(p, w, h, now, cfg, size):
    kind = cfg.get("party_effects", "both")
    glyphs = ["♪", "♫"] if kind == "notes" else ["✦", "✧"] if kind == "sparkles" else ["♪", "♫", "✦", "♪"]
    f = QFont("Segoe UI Symbol")
    f.setPixelSize(int(max(14, size * 0.55)))
    p.setFont(f)
    rise = h * 0.85
    for k in range(7):
        ph = ((now - k * 0.85) / 6.0) % 1.0
        a = (ph / 0.15) * 0.85 if ph < 0.15 else 0.85 - (ph - 0.15) / 0.7 * 0.25 if ph < 0.85 else 0.6 * (1 - (ph - 0.85) / 0.15)
        x = w * (0.06 + k * 0.13)
        y = h * 0.98 - rise * ph
        p.save()
        p.translate(x, y)
        p.rotate(-8 + 20 * ph)
        c = QColor(_PARTY_COLOURS[k % len(_PARTY_COLOURS)])
        c.setAlphaF(clamp(a))
        p.setPen(c)
        p.drawText(QPointF(0, 0), glyphs[k % len(glyphs)])
        p.restore()


def draw_countdown(p, cx, cy, size, prog, alpha, accent):
    r = size * 0.13
    gap = r * 3.4
    for i in range(3):
        x = cx + (i - 1) * gap
        fill = clamp(prog * 3 - i)
        pulse = 1 + 0.18 * math.sin(fill * math.pi) if 0 < fill < 1 else 1.0
        rr = r * pulse
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(0, 0, 0, int(110 * alpha)))
        p.drawEllipse(QPointF(x + 1.5, cy + 2), rr, rr)
        p.setBrush(with_alpha(accent, 0.28 * alpha))
        p.drawEllipse(QPointF(x, cy), rr, rr)
        if fill > 0:
            p.setBrush(with_alpha(accent, alpha * (0.35 + 0.65 * fill)))
            p.drawEllipse(QPointF(x, cy), rr * (0.35 + 0.65 * fill), rr * (0.35 + 0.65 * fill))


def draw_lyrics(p, w, h, cfg, lines, windows, t, album_color, playing=True, now=None,
                only_parity=None, stack_box=None):
    """Desenha o bloco de letra inteiro numa área w x h."""
    if now is None:
        now = t
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setRenderHint(QPainter.TextAntialiasing, True)
    stack = cfg.get("layout") == "stack"
    st = TextStyle(cfg)
    f = compute_frame(lines, windows, t, cfg, stack)
    if only_parity is not None:  # posição aleatória: cada janela desenha só as linhas dela
        f.previous, f.next_text = None, None
        if f.current and f.current[0] % 2 != only_parity:
            f.current = None
        f.leaving = [x for x in f.leaving if x[0] % 2 == only_parity]
        if f.countdown and max(f.idx, 0) % 2 != only_parity:
            f.countdown = None
    cx, cy = w / 2, h / 2
    p.setOpacity(float(cfg["lyrics_opacity"]))

    if cfg.get("party") and (f.current or f.leaving or f.countdown):
        draw_party(p, w, h, now, cfg, st.size)

    if stack:
        if cfg["background"] and f.current:
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(8, 8, 12, 110))
            p.drawRoundedRect(QRectF(w * 0.04, h * 0.06, w * 0.92, h * 0.88), st.size * 0.4, st.size * 0.4)
        for i, ln, s, hide in f.leaving:
            draw_stack(p, st, ln.text, w, h, t, s, hide, accent_for(cfg, album_color, i), cfg, i, now, True, stack_box)
        if f.current:
            i, ln, s, hide = f.current
            res = draw_stack(p, st, ln.text, w, h, t, s, hide, accent_for(cfg, album_color, i), cfg, i, now,
                             box=stack_box)
            if res and cfg.get("sparkle"):
                bbox, done_at = res
                draw_sparkles(p, bbox, t - done_at, cfg, ln.text, st.size)
    else:
        if cfg["background"] and (f.current or f.countdown):
            rows = line_rows(st, f.current[1].text, cfg.get("layout")) if f.current else [("", 1.0)]
            bw = max(st.fm.horizontalAdvance(r) * k for r, k in rows) + st.size * 1.2
            bh = rows_height(st, rows) + st.size * 0.7
            p.setPen(Qt.NoPen)
            p.setBrush(QColor(8, 8, 12, 120))
            p.drawRoundedRect(QRectF(cx - bw / 2, cy - bh / 2, bw, bh), st.size * 0.35, st.size * 0.35)
        cur_h = 0.0
        if f.current:
            i, ln, s, hide = f.current
            cur_h = draw_line(p, st, ln.text, cx, cy, t, s, hide, accent_for(cfg, album_color, i), cfg,
                              "current", now=now, line_index=i)
            if cfg.get("sparkle"):
                rows = line_rows(st, ln.text, cfg.get("layout"))
                bw = max(st.fm.horizontalAdvance(r) * k for r, k in rows)
                _, est, sung_dur = _timing(ln.text, s, hide)
                done_at = s + (sung_dur * 0.82 if cfg["animation"] == "typewriter" else ENTER)
                draw_sparkles(p, QRectF(cx - bw / 2, cy - cur_h / 2, bw, cur_h), t - done_at, cfg, ln.text, st.size)
        for i, ln, s, hide in f.leaving:
            draw_line(p, st, ln.text, cx, cy, t, s, hide, accent_for(cfg, album_color, i), cfg, "leaving",
                      now=now, line_index=i)
        if f.previous:
            i, ln, a = f.previous
            pst = TextStyle(cfg, 0.62)
            prow = pst.wrap(pst.prep(ln.text))
            ph = pst.block_height(prow)
            py = cy - cur_h / 2 - st.gap * 2 - ph / 2 - (1 - a) * st.size * 0.4
            draw_line(p, pst, ln.text, cx, py, t, 0, 1e9, accent_for(cfg, album_color, i), cfg,
                      "previous", alpha_mult=a * 0.8, now=now)
        if f.next_text:
            nst = TextStyle(cfg, 0.55)
            nrows = nst.wrap(nst.prep(f.next_text))
            nh = nst.block_height(nrows)
            ny = cy + max(cur_h, st.row_h) / 2 + st.gap * 2 + nh / 2
            draw_line(p, nst, f.next_text, cx, ny, t, 0, 1e9, QColor(235, 235, 240), cfg,
                      "preview", alpha_mult=0.55, now=now)
    if f.countdown:
        prog, a = f.countdown
        draw_countdown(p, cx, cy, st.size, prog, a, accent_for(cfg, album_color, 0))
    p.setOpacity(1.0)


# ----------------------------------------------------------------- widget
def _cover_art(p, rect, info, accent, op):
    """Capa (ou um ♪ na cor de destaque quando não tem capa) preenchendo o retângulo."""
    if info.cover is not None and not info.cover.isNull():
        p.setOpacity(op)
        pm = info.cover
        src = QRectF(pm.rect())
        side = min(src.width(), src.height())
        src = QRectF((src.width() - side) / 2, (src.height() - side) / 2, side, side)
        p.drawPixmap(rect, pm, src)
        p.setOpacity(1)
    else:
        g = QLinearGradient(rect.topLeft(), rect.bottomRight())
        g.setColorAt(0, with_alpha(accent, op))
        g.setColorAt(1, with_alpha(accent.darker(220), op))
        p.fillRect(rect, g)
        nf = QFont(family("poppins"))
        nf.setPixelSize(int(rect.height() * 0.45))
        p.setFont(nf)
        p.setPen(QColor(255, 255, 255, int(220 * op)))
        p.drawText(rect, Qt.AlignCenter, "♪")


def draw_cover(p, rect, style, info, accent, op, s=1.0):
    """Estilos da capa no widget: quadrado arredondado, quadrado, círculo ou disco de vinil girando."""
    p.save()
    clip = QPainterPath()
    if style == "square":
        clip.addRect(rect)
    elif style in ("circle", "vinyl"):
        clip.addEllipse(rect)
    else:
        clip.addRoundedRect(rect, 10 * s, 10 * s)

    if style != "vinyl":
        p.setClipPath(clip)
        if style == "circle" and info.playing:
            # gira devagar, como o adesivo de música do Instagram
            c = rect.center()
            p.translate(c)
            p.rotate(info.disc_angle * 0.35)
            p.translate(-c)
        _cover_art(p, rect, info, accent, op)
        p.restore()
        return

    # ---- disco de vinil
    c = rect.center()
    r = rect.width() / 2
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(0, 0, 0, int(90 * op)))
    p.drawEllipse(c + QPointF(1.5 * s, 2 * s), r, r)  # sombra
    p.translate(c)
    p.rotate(info.disc_angle)
    p.translate(-c)
    p.setBrush(QColor(14, 14, 16, int(255 * op)))
    p.drawEllipse(c, r, r)
    # sulcos
    for k in range(9):
        rr = r * (0.94 - k * 0.045)
        p.setPen(QPen(QColor(255, 255, 255, int((10 if k % 2 else 18) * op)), max(0.6, 0.7 * s)))
        p.setBrush(Qt.NoBrush)
        p.drawEllipse(c, rr, rr)
    # rótulo do disco com a capa
    lr = r * 0.58
    label = QRectF(c.x() - lr, c.y() - lr, lr * 2, lr * 2)
    lab_clip = QPainterPath()
    lab_clip.addEllipse(label)
    p.save()
    p.setClipPath(lab_clip)
    _cover_art(p, label, info, accent, op)
    p.restore()
    p.setPen(QPen(QColor(0, 0, 0, int(120 * op)), max(1.0, 1.2 * s)))
    p.setBrush(Qt.NoBrush)
    p.drawEllipse(c, lr, lr)
    # furo do meio
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(20, 20, 24, int(255 * op)))
    p.drawEllipse(c, r * 0.07, r * 0.07)
    p.restore()
    # brilho do vinil (não gira, como a luz refletindo)
    p.save()
    clip2 = QPainterPath()
    clip2.addEllipse(rect)
    p.setClipPath(clip2)
    sheen = QLinearGradient(rect.topLeft(), rect.bottomRight())
    sheen.setColorAt(0.0, QColor(255, 255, 255, 0))
    sheen.setColorAt(0.42, QColor(255, 255, 255, int(28 * op)))
    sheen.setColorAt(0.5, QColor(255, 255, 255, 0))
    sheen.setColorAt(0.62, QColor(255, 255, 255, int(16 * op)))
    sheen.setColorAt(1.0, QColor(255, 255, 255, 0))
    p.fillRect(rect, sheen)
    p.restore()


class WidgetInfo:
    def __init__(self):
        self.disc_angle = 0.0
        self.title = ""
        self.artist = ""
        self.position = 0.0
        self.duration = 0.0
        self.playing = False
        self.cover = None       # QPixmap
        self.status = ""


def draw_widget(p, cfg, info, album_color):
    s = float(cfg["widget_scale"])
    W, H = 360 * s, 96 * s
    op = float(cfg["widget_opacity"])
    p.setRenderHint(QPainter.Antialiasing, True)
    p.setRenderHint(QPainter.TextAntialiasing, True)
    p.setRenderHint(QPainter.SmoothPixmapTransform, True)
    accent = accent_for(cfg, album_color, 0)

    # painel
    panel = QRectF(1, 1, W - 2, H - 2)
    grad = QLinearGradient(0, 0, W, H)
    grad.setColorAt(0, QColor(22, 22, 28, int(225 * op)))
    grad.setColorAt(1, QColor(12, 12, 16, int(225 * op)))
    p.setPen(QPen(QColor(255, 255, 255, int(22 * op)), 1))
    p.setBrush(QBrush(grad))
    p.drawRoundedRect(panel, 16 * s, 16 * s)

    # capa
    pad = 12 * s
    cs = H - pad * 2
    crect = QRectF(pad, pad, cs, cs)
    draw_cover(p, crect, cfg.get("cover_style", "rounded"), info, accent, op, s)

    # textos
    tx = pad * 2 + cs - 2 * s
    tw = W - tx - pad * 1.3
    tf = QFont(family("poppins"))
    tf.setPixelSize(int(15 * s))
    tf.setBold(True)
    af = QFont(family("poppins"))
    af.setPixelSize(int(12 * s))
    sf = QFont(family("poppins"))
    sf.setPixelSize(int(10 * s))
    p.setFont(tf)
    title = QFontMetricsF(tf).elidedText(info.title or tr("widget.nothing"), Qt.ElideRight, tw)
    p.setPen(QColor(255, 255, 255, int(245 * op)))
    p.drawText(QPointF(tx, pad + 15 * s), title)
    p.setFont(af)
    artist = QFontMetricsF(af).elidedText(info.artist or tr("widget.open_player"),
                                          Qt.ElideRight, tw)
    p.setPen(QColor(255, 255, 255, int(150 * op)))
    p.drawText(QPointF(tx, pad + 33 * s), artist)

    # barra de progresso
    by = H - pad - 16 * s
    bar = QRectF(tx, by, tw, 4 * s)
    p.setPen(Qt.NoPen)
    p.setBrush(QColor(255, 255, 255, int(38 * op)))
    p.drawRoundedRect(bar, 2 * s, 2 * s)
    frac = clamp(info.position / info.duration) if info.duration > 0 else 0
    if frac > 0:
        fb = QRectF(bar.x(), bar.y(), max(bar.height(), bar.width() * frac), bar.height())
        p.setBrush(with_alpha(accent, op))
        p.drawRoundedRect(fb, 2 * s, 2 * s)
        p.setBrush(with_alpha(accent, 0.25 * op))
        p.drawEllipse(QPointF(fb.right(), fb.center().y()), 5 * s, 5 * s)
    p.setFont(sf)
    if info.status:
        p.setPen(with_alpha(accent, 0.9 * op))
        msg = QFontMetricsF(sf).elidedText(info.status, Qt.ElideRight, tw)
        p.drawText(QPointF(tx, H - pad), msg)
    elif info.duration > 0:
        p.setPen(QColor(255, 255, 255, int(120 * op)))
        p.drawText(QPointF(tx, H - pad), fmt_time(info.position))
        dur = fmt_time(info.duration)
        p.drawText(QPointF(tx + tw - QFontMetricsF(sf).horizontalAdvance(dur), H - pad), dur)
    if not info.playing and info.title:
        p.setPen(QColor(255, 255, 255, int(120 * op)))
        pz = tr("widget.paused")
        p.drawText(QPointF(tx + tw / 2 - QFontMetricsF(sf).horizontalAdvance(pz) / 2, H - pad), pz)
    return W, H


def cover_pixmap(image_bytes):
    if not image_bytes:
        return None
    pm = QPixmap()
    return pm if pm.loadFromData(image_bytes) else None
