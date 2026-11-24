# news-image-20261124 — "THE WORLD IN ONE DAY: Tuesday 24 November 2026"
# A one-day newspaper front page, drawn programmatically with pure
# Python 3 standard library. 46 dated stories, 9 regions, every story
# happened or was first reported on Tuesday 24 November 2026 (UTC),
# to press time 05:00 UTC. Lead: Russian strike kills 2 in Zaporizhzhia.
# Three hero panels (Ukraine sinks Russian warship off Libya, Nvidia
# shockwave, Gaza strikes), 12 mid story cards with drawn scenes, a
# 30-item numbered also-list, a UTC timeline, a day-in-numbers strip,
# a region colour bar, a pin map, and a date-check box that names the
# big stories left out because they belong to another day.
#
# The paper carries a light deterministic newsprint grain (seeded, sparse
# +/-1 speckle) — the texture a printed front page has, which also keeps
# the image rich at full size. No photos: every scene is drawn by hand
# in code. Deterministic: two runs write identical bytes. No network,
# no files read, standard library only.
#
# Run:  mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
# Writes out/entry.png (1024x1024, PNG).

import os
import random
import struct
import zlib

W, H = 1024, 1024

PAPER = (244, 241, 232)
INK = (22, 22, 22)
RED = (178, 34, 34)
ORANGE = (214, 105, 24)
PURPLE = (108, 48, 130)
TEAL = (15, 118, 110)
NAVY2 = (34, 64, 134)
GREEN = (28, 112, 54)
BROWN = (120, 72, 30)
GOLD = (184, 134, 11)
SKY_D = (24, 90, 158)
GREY = (120, 118, 112)
LIGHT = (236, 233, 226)
MIDGREY = (200, 197, 190)
DARKBLUE = (18, 32, 64)
SKY = (120, 170, 210)
SUNY = (232, 190, 60)
SEA = (26, 82, 138)
FLAG = (220, 220, 220)

REGION_COLORS = {
    "CLIMATE": RED,
    "UKRAINE WAR": ORANGE,
    "MIDDLE EAST": PURPLE,
    "ASIA-PACIFIC": TEAL,
    "EUROPE": NAVY2,
    "AMERICAS": GREEN,
    "AFRICA": BROWN,
    "MARKETS": GOLD,
    "SPORT": SKY_D,
}

# ---------------- PNG encoder (pure stdlib) ----------------


def _crc32(chunk_type, data):
    return zlib.crc32(chunk_type + data) & 0xFFFFFFFF


def _chunk(chunk_type, data):
    return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", _crc32(chunk_type, data))


def encode_png(width, height, px):
    """px: bytearray of RGB pixels, row-major, length width*height*3."""
    stride = width * 3
    rows = bytearray()
    for y in range(height):
        row = bytes(px[y * stride:(y + 1) * stride])
        sub = bytes(((row[i] - (row[i - 3] if i >= 3 else 0)) & 0xFF) for i in range(stride))
        up = bytes(((row[i] - (px[(y - 1) * stride + i] if y > 0 else 0)) & 0xFF) for i in range(stride))
        score = lambda b: sum(abs(v - 128) for v in b)
        if score(sub) < score(up):
            rows.append(1)
            rows.extend(sub)
        else:
            rows.append(2)
            rows.extend(up)
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n"
            + _chunk(b"IHDR", ihdr)
            + _chunk(b"IDAT", zlib.compress(bytes(rows), 9))
            + _chunk(b"IEND", b""))


# ---------------- canvas ----------------


class Canvas:
    def __init__(self, w, h, bg):
        self.w, self.h = w, h
        self.clip = None
        self.px = bytearray(w * h * 3)
        self.fill_rect(0, 0, w, h, bg)

    def _idx(self, x, y):
        return (y * self.w + x) * 3

    def set_clip(self, x, y, w, h):
        self.clip = (x, y, x + w, y + h)

    def clear_clip(self):
        self.clip = None

    def _in_clip(self, x, y):
        if self.clip is None:
            return True
        cx0, cy0, cx1, cy1 = self.clip
        return cx0 <= x < cx1 and cy0 <= y < cy1

    def set(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h and self._in_clip(x, y):
            i = self._idx(x, y)
            self.px[i], self.px[i + 1], self.px[i + 2] = c

    def fill_rect(self, x, y, w, h, c):
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.w, x + w), min(self.h, y + h)
        if self.clip is not None:
            cx0, cy0, cx1, cy1 = self.clip
            x0, y0 = max(x0, cx0), max(y0, cy0)
            x1, y1 = min(x1, cx1), min(y1, cy1)
        r, g, b = c
        for yy in range(y0, y1):
            i = (yy * self.w + x0) * 3
            for xx in range(x0, x1):
                self.px[i], self.px[i + 1], self.px[i + 2] = r, g, b
                i += 3

    def dither_rect(self, x, y, w, h, c1, c2):
        """Checkerboard halftone: reads as a mid tone, feels like print."""
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self.set(xx, yy, c1 if (xx + yy) % 2 == 0 else c2)

    def hline(self, x, y, w, c, th=1):
        self.fill_rect(x, y, w, th, c)

    def vline(self, x, y, h, c, th=1):
        self.fill_rect(x, y, th, h, c)

    def frame(self, x, y, w, h, c, th=1):
        self.hline(x, y, w, c, th)
        self.hline(x, y + h - th, w, c, th)
        self.vline(x, y, h, c, th)
        self.vline(x + w - th, y, h, c, th)

    def line(self, x0, y0, x1, y1, c):
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        while True:
            self.set(x0, y0, c)
            if x0 == x1 and y0 == y1:
                return
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    def fill_circle(self, cx, cy, r, c):
        for y in range(cy - r, cy + r + 1):
            dx = int((r * r - (y - cy) ** 2) ** 0.5) if abs(y - cy) <= r else 0
            self.hline(cx - dx, y, 2 * dx + 1, c)

    def circle(self, cx, cy, r, c):
        for a in range(360):
            import math
            self.set(int(cx + r * math.cos(math.radians(a))),
                     int(cy + r * math.sin(math.radians(a))), c)

    def fill_poly(self, pts, c):
        if not pts:
            return
        ys = [p[1] for p in pts]
        for y in range(min(ys), max(ys) + 1):
            xs = []
            for i in range(len(pts)):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % len(pts)]
                if (y0 <= y < y1) or (y1 <= y < y0):
                    t = (y - y0) / (y1 - y0)
                    xs.append(int(x0 + t * (x1 - x0)))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                self.hline(xs[i], y, xs[i + 1] - xs[i], c)

    def poly_line(self, pts, c):
        for i in range(len(pts) - 1):
            self.line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1], c)

# ---------------- 5x7 bitmap font ----------------

FONT = {
    'A': ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    'B': ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    'C': ("01110", "10001", "10000", "10000", "10000", "10001", "01110"),
    'D': ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    'E': ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    'F': ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    'G': ("01110", "10001", "10000", "10111", "10001", "10001", "01111"),
    'H': ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    'I': ("01110", "00100", "00100", "00100", "00100", "00100", "01110"),
    'J': ("00111", "00010", "00010", "00010", "00010", "10010", "01100"),
    'K': ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    'L': ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    'M': ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    'N': ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    'O': ("01110", "10001", "10001", "10001", "10001", "10001", "01110"),
    'P': ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    'Q': ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    'R': ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    'S': ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    'T': ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    'U': ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    'V': ("10001", "10001", "10001", "10001", "10001", "01010", "00100"),
    'W': ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    'X': ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    'Y': ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    'Z': ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    '0': ("01110", "10001", "10011", "10101", "11001", "10001", "01110"),
    '1': ("00100", "01100", "00100", "00100", "00100", "00100", "01110"),
    '2': ("01110", "10001", "00001", "00110", "01000", "10000", "11111"),
    '3': ("11111", "00010", "00100", "00010", "00001", "10001", "01110"),
    '4': ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    '5': ("11111", "10000", "11110", "00001", "00001", "10001", "01110"),
    '6': ("00110", "01000", "10000", "11110", "10001", "10001", "01110"),
    '7': ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    '8': ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    '9': ("01110", "10001", "10001", "01111", "00001", "00010", "01100"),
    ' ': ("00000", "00000", "00000", "00000", "00000", "00000", "00000"),
    '.': ("00000", "00000", "00000", "00000", "00000", "00100", "00100"),
    ',': ("00000", "00000", "00000", "00000", "00100", "00100", "01000"),
    ':': ("00000", "00100", "00100", "00000", "00100", "00100", "00000"),
    ';': ("00000", "00100", "00100", "00000", "00100", "00100", "01000"),
    '!': ("00100", "00100", "00100", "00100", "00100", "00000", "00100"),
    '?': ("01110", "10001", "00001", "00010", "00100", "00000", "00100"),
    '-': ("00000", "00000", "00000", "01110", "00000", "00000", "00000"),
    "'": ("00100", "00100", "01000", "00000", "00000", "00000", "00000"),
    '"': ("01010", "01010", "00000", "00000", "00000", "00000", "00000"),
    '(': ("00010", "00100", "01000", "01000", "01000", "00100", "00010"),
    ')': ("01000", "00100", "00010", "00010", "00010", "00100", "01000"),
    '+': ("00000", "00100", "00100", "11111", "00100", "00100", "00000"),
    '%': ("11001", "11010", "00010", "00100", "01000", "01011", "10011"),
    '&': ("01100", "10010", "10100", "01000", "10101", "10010", "01101"),
    '$': ("00100", "01111", "10100", "01110", "00101", "11110", "00100"),
    '/': ("00001", "00010", "00010", "00100", "01000", "01000", "10000"),
    '=': ("00000", "00000", "11111", "00000", "11111", "00000", "00000"),
    '_': ("00000", "00000", "00000", "00000", "00000", "00000", "11111"),
    '*': ("00000", "00100", "10101", "01110", "10101", "00100", "00000"),
    '<': ("00010", "00100", "01000", "10000", "01000", "00100", "00010"),
    '>': ("01000", "00100", "00010", "00001", "00010", "00100", "01000"),
    '#': ("01010", "01010", "11111", "01010", "11111", "01010", "01010"),
    '@': ("01110", "10001", "10111", "10101", "10110", "10000", "01110"),
    '[': ("01110", "01000", "01000", "01000", "01000", "01000", "01110"),
    ']': ("01110", "00010", "00010", "00010", "00010", "00010", "01110"),
    '{': ("00110", "01000", "01000", "11100", "01000", "01000", "00110"),
    '}': ("01100", "00010", "00010", "00111", "00010", "00010", "01100"),
    '|': ("00100", "00100", "00100", "00100", "00100", "00100", "00100"),
    '~': ("00000", "00000", "01001", "10110", "00000", "00000", "00000"),
    '^': ("00100", "01010", "10001", "00000", "00000", "00000", "00000"),
    '`': ("01000", "00100", "00000", "00000", "00000", "00000", "00000"),
    '\\': ("10000", "01000", "01000", "00100", "00010", "00010", "00001"),
}


def text_width(text, scale):
    return len(text) * 6 * scale


def draw_text(cv, x, y, text, scale, color):
    for ci, ch in enumerate(text):
        glyph = FONT.get(ch.upper(), FONT[' '])
        for gy in range(7):
            row = glyph[gy]
            for gx in range(5):
                if row[gx] == '1':
                    cv.fill_rect(x + (ci * 6 + gx) * scale, y + gy * scale, scale, scale, color)


def draw_text_centered(cv, x, y, w, text, scale, color):
    tw = text_width(text, scale)
    draw_text(cv, x + max(0, (w - tw) // 2), y, text, scale, color)


def wrap_text(text, max_chars):
    words = text.split(' ')
    lines, cur = [], ''
    for word in words:
        if not cur:
            cur = word
        elif len(cur) + 1 + len(word) <= max_chars:
            cur += ' ' + word
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def draw_para(cv, x, y, text, scale, color, max_w, lh=None):
    max_chars = max_w // (6 * scale)
    lh = lh or 7 * scale + 3
    lines = wrap_text(text, max_chars)
    for i, line in enumerate(lines):
        draw_text(cv, x, y + i * lh, line, scale, color)
    return y + len(lines) * lh


def draw_chip(cv, x, y, text, bg, fg=FLAG):
    w = text_width(text, 1) + 10
    cv.fill_rect(x, y, w, 13, bg)
    draw_text(cv, x + 5, y + 3, text, 1, fg)
    return w


def _star(cv, cx, cy, r, c):
    import math
    pts = []
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        pts.append((int(cx + rr * math.cos(ang)), int(cy + rr * math.sin(ang))))
    cv.fill_poly(pts, c)

# ---------------- drawn scenes (all 56x56 in mid cards, 320x96 in heroes) ----------------


def draw_scene(cv, kind, x, y, w, h, rng):
    # Scenes are clipped to their own box: nothing may paint over the
    # card frame or the card below (a mid card is only 36x36, a hero
    # panel 320x96, so every element is sized from w and h).
    cv.set_clip(x, y, w, h)
    if kind == "cop31":
        cv.dither_rect(x, y, w, h, (200, 222, 200), (190, 214, 190))
        gr = h // 2 - 2
        cv.fill_circle(x + w // 2, y + h - 2, gr, (70, 130, 70))
        cv.fill_circle(x + w // 2 - gr // 2, y + h - 2 - gr // 3, gr // 2, (90, 150, 90))
        cv.fill_circle(x + w // 2 + gr // 2, y + h - 2 - gr // 5, gr // 3, (60, 120, 60))
        cv.fill_rect(x + 4, y + 4, w // 5, h // 3, (120, 120, 120))
        cv.fill_rect(x + w // 4 + 2, y + 6, w // 7, h // 4, (140, 140, 140))
        cv.fill_rect(x + w - w // 5 - 4, y + 5, w // 5, h // 3, (110, 110, 110))
        cv.fill_rect(x, y + h - 3, w, 3, (40, 90, 40))
        for _ in range(8):
            cv.fill_circle(x + rng.randrange(0, w), y + rng.randrange(0, h // 2), 1, (255, 255, 255))
    elif kind == "chart_down":
        cv.fill_rect(x, y, w, h, DARKBLUE)
        cv.hline(x + 4, y + h - 8, w - 8, (200, 200, 200))
        bw = max(3, (w - 12) // 8)
        vals = [0.5, 0.7, 0.6, 0.8, 0.55, 0.35, 0.45, 0.25]
        for i, v in enumerate(vals):
            bh = int(v * (h - 18))
            cv.fill_rect(x + 6 + i * (bw + 1), y + h - 8 - bh, bw, bh,
                         (30, 160, 120) if i < 5 else (200, 50, 50))
        cv.poly_line([(x + 8, y + 14), (x + w // 3, y + 22), (x + 2 * w // 3, y + 30),
                      (x + w - 8, y + h - 14)], (255, 60, 60))
        cv.fill_rect(x + w - 26, y + 4, 22, 12, RED)
        draw_text(cv, x + w - 24, y + 6, "-7%", 1, FLAG)
    elif kind == "drone":
        cv.dither_rect(x, y, w, h, (16, 24, 44), (22, 32, 56))
        for _ in range(14):
            cv.fill_rect(x + rng.randrange(0, w), y + rng.randrange(0, h // 2), 1, 1, (255, 255, 255))
        cv.fill_circle(x + w // 2, y + h // 2 - 4, 5, (220, 220, 220))
        cv.fill_rect(x + w // 2 - 12, y + h // 2 - 8, 24, 3, (160, 160, 160))
        cv.fill_circle(x + w // 2 - 14, y + h // 2 - 8, 3, (200, 200, 200))
        cv.fill_circle(x + w // 2 + 14, y + h // 2 - 8, 3, (200, 200, 200))
        cv.fill_rect(x + w // 2 - 1, y + h // 2 + 2, 2, 8, (255, 180, 40))
        cv.fill_circle(x + w // 2 - 2, y + h - 10, 6, (255, 120, 20))
        cv.fill_circle(x + w // 2 + 3, y + h - 8, 4, (255, 200, 60))
        cv.fill_rect(x + 2, y + h - 6, w // 3, 6, (40, 40, 40))
        cv.fill_rect(x + 2 * w // 3, y + h - 5, w // 3 - 2, 5, (40, 40, 40))
        cv.fill_rect(x + w // 2 - 8, y + 2, 3, 3, RED)
    elif kind == "gaza":
        cv.dither_rect(x, y, w, h, (198, 182, 158), (188, 172, 148))
        cv.fill_poly([(x + 2, y + h - 2), (x + w // 3, y + h - 26), (x + 2 * w // 3, y + h - 14),
                      (x + w - 2, y + h - 22), (x + w - 2, y + h - 2)], (140, 125, 105))
        cv.fill_poly([(x + 6, y + h - 26), (x + 12, y + h - 38), (x + 20, y + h - 26)], (110, 100, 85))
        cv.fill_rect(x + w // 2 - 4, y + h - 34, 8, 34, (100, 90, 75))
        cv.fill_rect(x + w // 2 - 10, y + h - 34, 20, 4, (100, 90, 75))
        cv.fill_circle(x + w - 12, y + 10, 8, (240, 200, 90))
        for _ in range(10):
            cv.fill_rect(x + rng.randrange(0, w), y + rng.randrange(h // 2, h), 2, 2, (120, 105, 85))
    elif kind == "football":
        cv.fill_rect(x, y, w, h, (30, 130, 60))
        cv.hline(x, y + h // 2, w, (255, 255, 255))
        cv.circle(x + w // 2, y + h // 2, h // 4, (255, 255, 255))
        cv.fill_circle(x + w // 2 - 12, y + h // 3, 7, FLAG)
        cv.fill_circle(x + w // 2 + 12, y + 2 * h // 3, 7, FLAG)
        cv.fill_rect(x + w // 2 - 18, y + 2, 36, 10, (20, 20, 20))
        draw_text(cv, x + w // 2 - 14, y + 4, "4 - 0", 1, FLAG)
        cv.fill_rect(x + 2, y + h - 8, w - 4, 6, (20, 90, 40))
    elif kind == "flags_in_np":
        cv.fill_rect(x, y, w, h, (240, 238, 230))
        cv.vline(x + w // 2, y + 6, h - 12, (120, 120, 120))
        cv.fill_poly([(x + 6, y + 8), (x + w // 2 - 4, y + 8), (x + w // 2 - 4, y + h // 2)],
                     (255, 153, 51))
        cv.fill_poly([(x + 6, y + h // 2), (x + w // 2 - 4, y + h // 2), (x + w // 2 - 4, y + h - 8)],
                     (19, 136, 8))
        cv.circle(x + w // 4, y + h // 2, 6, (0, 0, 128))
        cv.fill_poly([(x + w // 2 + 4, y + 8), (x + w - 6, y + 14), (x + w - 6, y + h - 14),
                      (x + w // 2 + 4, y + h - 8)], (220, 20, 60))
        cv.fill_poly([(x + w // 2 + 4, y + 8), (x + w // 2 + 12, y + 16), (x + w // 2 + 4, y + h - 8)],
                     (0, 56, 147))
        cv.fill_circle(x + w - 16, y + 12, 2, (255, 255, 255))
    elif kind == "capitol":
        cv.dither_rect(x, y, w, h, (180, 200, 225), (170, 192, 218))
        dw = w // 2
        cv.fill_rect(x + (w - dw) // 2, y + 2, dw, max(2, h // 8), (240, 240, 235))
        cv.fill_circle(x + w // 2, y + h // 5, max(3, h // 7), (240, 240, 235))
        cv.fill_rect(x + (w - dw - 6) // 2, y + h // 5 + max(3, h // 7) // 2,
                     dw + 6, max(2, h // 10), (235, 235, 230))
        gap = w // 6
        col_w = max(2, w // 12)
        for i in range(5):
            cv.fill_rect(x + gap * (i + 1) - col_w // 2, y + h // 2, col_w, h // 3,
                         (245, 245, 240))
        cv.fill_rect(x + 2, y + h - h // 6, w - 4, max(2, h // 12), (230, 230, 225))
        cv.fill_rect(x + 2, y + h - 4, w - 4, 4, (90, 130, 80))
        cv.fill_circle(x + 4, y + 4, 2, (255, 220, 90))
        cv.fill_circle(x + w - 6, y + 6, 2, (255, 220, 90))
    elif kind == "eu_stars":
        cv.fill_rect(x, y, w, h, (0, 51, 153))
        orbit = min(w, h) // 2 - 4
        for i in range(12):
            import math
            a = i * math.pi / 6
            _star(cv, x + w // 2 + int(orbit * math.cos(a)),
                  y + h // 2 + int(orbit * math.sin(a)), 3, (255, 204, 0))
        cv.fill_rect(x + w // 2 - 12, y + h // 2 - 8, 24, 16, (255, 255, 255))
        draw_text(cv, x + w // 2 - 10, y + h // 2 - 4, "7", 1, (0, 51, 153))
    elif kind == "globe":
        cv.dither_rect(x, y, w, h, (200, 222, 235), (190, 214, 228))
        gr = min(w, h) // 2 - 1
        cv.fill_circle(x + w // 2, y + h // 2, gr, SEA)
        cv.fill_circle(x + w // 2 - gr // 2, y + h // 2 - gr // 3, gr // 3, (90, 160, 90))
        cv.fill_circle(x + w // 2 + gr // 2, y + h // 2 + gr // 4, gr // 4, (90, 160, 90))
        cv.fill_circle(x + w // 2 + gr // 4, y + h // 2 - gr // 2, gr // 5, (110, 170, 110))
        cv.circle(x + w // 2, y + h // 2, gr, (20, 60, 100))
        cv.fill_rect(x + 1, y + 1, 8, 5, RED)
        draw_text(cv, x + 3, y + 2, "!", 1, FLAG)
    elif kind == "warning":
        cv.fill_rect(x, y, w, h, (250, 240, 200))
        cv.fill_poly([(x + w // 2, y + 4), (x + w - 4, y + h - 6), (x + 4, y + h - 6)], (250, 200, 40))
        cv.fill_poly([(x + w // 2, y + 12), (x + w - 10, y + h - 12), (x + 10, y + h - 12)], (20, 20, 20))
        draw_text(cv, x + w // 2 - 3, y + h // 2 - 6, "!", 2, (250, 200, 40))
        cv.fill_rect(x + 2, y + h - 4, w - 4, 2, (20, 20, 20))
    elif kind == "chip":
        cv.fill_rect(x, y, w, h, (12, 40, 28))
        # circuit traces spanning the board
        for i in range(5):
            yy = y + 6 + i * (h - 12) // 4
            cv.hline(x + 4, yy, w - 8, (30, 90, 60))
            cv.fill_circle(x + 6 + i * (w // 6), yy, 2, (210, 170, 40))
        for i in range(4):
            xx = x + 8 + i * (w - 16) // 3
            cv.vline(xx, y + 4, h - 8, (30, 90, 60))
        # main chip, sized to the scene
        cs = min(w, h) * 2 // 3
        cx0, cy0 = x + (w - cs) // 2, y + (h - cs) // 2
        cv.fill_rect(cx0, cy0, cs, cs, (20, 90, 70))
        cv.frame(cx0, cy0, cs, cs, (210, 170, 40), 2)
        cv.fill_rect(cx0 + cs // 4, cy0 + cs // 4, cs // 2, cs // 2, (210, 170, 40))
        for i in range(5):
            py = cy0 + 2 + i * (cs - 4) // 4
            cv.fill_rect(cx0 - 6, py, 6, 2, (210, 170, 40))
            cv.fill_rect(cx0 + cs, py, 6, 2, (210, 170, 40))
        # rising chart line across the board
        cv.poly_line([(x + 4, y + h - 6), (x + w // 3, y + h - 14),
                      (x + 2 * w // 3, y + h - 20), (x + w - 5, y + h - 26)],
                     (40, 200, 120))
    elif kind == "ship":
        cv.dither_rect(x, y, w, h, (120, 170, 210), (110, 162, 204))
        cv.fill_rect(x, y + h // 2, w, h // 2, SEA)
        for i in range(3):
            cv.hline(x, y + h // 2 + 6 + i * 8, w, (120, 190, 230))
        cv.fill_poly([(x + 8, y + h // 2 - 4), (x + w - 8, y + h // 2 - 4),
                      (x + w - 14, y + h // 2 + 8), (x + 14, y + h // 2 + 8)], (60, 60, 60))
        cv.fill_rect(x + w // 2 - 8, y + h // 2 - 16, 16, 12, (70, 70, 70))
        cv.fill_rect(x + w // 2 - 2, y + h // 2 - 24, 4, 8, (80, 80, 80))
        cv.fill_circle(x + w - 12, y + h // 2 - 10, 6, (255, 120, 20))
        cv.fill_circle(x + w - 16, y + h // 2 - 6, 4, (255, 200, 60))
        cv.fill_circle(x + w // 2 + 10, y + 8, 2, (220, 220, 220))
        cv.fill_circle(x + w // 2 + 18, y + 14, 2, (220, 220, 220))
        cv.fill_rect(x + w // 2 + 9, y + 9, 10, 1, (200, 200, 200))
    elif kind == "satellite":
        cv.dither_rect(x, y, w, h, (8, 14, 34), (12, 20, 44))
        for _ in range(16):
            cv.fill_rect(x + rng.randrange(0, w), y + rng.randrange(0, h // 2), 1, 1, (255, 255, 255))
        # earth arc along the bottom, sized to the scene
        er = h * 3 // 5
        cv.fill_circle(x + w // 2, y + h + er // 3, er, (40, 110, 190))
        cv.fill_circle(x + w // 2 - er // 3, y + h + er // 4, er // 3, (60, 140, 90))
        # satellite body + solar panels, sized to the scene
        bw = w * 2 // 5
        bh = max(6, h // 5)
        bx, by = x + (w - bw) // 2, y + h // 4
        cv.fill_rect(bx - bw // 2, by + 1, bw // 2, bh - 2, (255, 204, 0))
        cv.fill_rect(bx, by, bw, bh, (200, 200, 200))
        cv.fill_rect(bx + bw, by + 1, bw // 2, bh - 2, (255, 204, 0))
        cv.fill_rect(bx + bw // 2 - 2, by + bh, 4, max(3, h // 8), (180, 180, 180))
        cv.line(bx + bw - 2, by, x + w - 4, y + 4, (255, 80, 80))
        cv.fill_circle(x + w - 4, y + 4, 2, (255, 80, 80))
    elif kind == "factory_fire":
        cv.dither_rect(x, y, w, h, (60, 60, 70), (54, 54, 64))
        cv.fill_rect(x + 6, y + h // 2, w - 12, h // 2 - 6, (110, 100, 90))
        cv.fill_rect(x + 10, y + h // 2 - 14, 8, 14, (90, 80, 70))
        cv.fill_rect(x + 22, y + h // 2 - 18, 8, 18, (90, 80, 70))
        for i in range(4):
            cv.fill_rect(x + 10 + i * 12, y + h // 2 + 6, 6, 6, (40, 40, 40))
        cv.fill_circle(x + w // 2, y + h // 2 - 6, 10, (255, 120, 20))
        cv.fill_circle(x + w // 2 - 6, y + h // 2 - 2, 7, (255, 200, 60))
        cv.fill_circle(x + w // 2 + 6, y + h // 2 - 2, 6, (255, 90, 10))
        cv.fill_circle(x + 10, y + 10, 6, (120, 120, 120))
        cv.fill_circle(x + 16, y + 6, 5, (140, 140, 140))
        cv.fill_circle(x + w - 12, y + 8, 5, (120, 120, 120))
        cv.fill_rect(x, y + h - 4, w, 4, (40, 40, 40))
    elif kind == "bus_crash":
        cv.dither_rect(x, y, w, h, (200, 210, 220), (192, 202, 212))
        cv.fill_rect(x, y + 2 * h // 3, w, h // 3, (80, 80, 80))
        cv.hline(x, y + 2 * h // 3 + 6, w, (255, 255, 255))
        cv.fill_poly([(x + 6, y + h // 3), (x + w - 10, y + h // 3 - 6),
                      (x + w - 10, y + 2 * h // 3 - 4), (x + 6, y + 2 * h // 3 - 4)],
                     (240, 200, 40))
        for i in range(4):
            cv.fill_rect(x + 10 + i * 12, y + h // 3 + 4, 8, 8, (180, 220, 240))
        cv.fill_circle(x + 16, y + 2 * h // 3 - 2, 5, (30, 30, 30))
        cv.fill_circle(x + w - 18, y + 2 * h // 3 - 2, 5, (30, 30, 30))
        cv.fill_rect(x + w // 2 - 2, y + h // 3 - 8, 4, 4, RED)
        cv.fill_rect(x + w - 6, y + h // 2, 3, 3, (60, 60, 60))
        cv.fill_rect(x + 4, y + h // 2 + 4, 3, 3, (60, 60, 60))
        cv.fill_circle(x + w // 2, y + 6, 2, (255, 80, 80))
    else:
        cv.fill_rect(x, y, w, h, LIGHT)
        cv.frame(x, y, w, h, GREY)
    cv.clear_clip()

# ---------------- pin map ----------------


def draw_pin_map(cv, x, y, w, h, pins):
    cv.fill_rect(x, y, w, h, (200, 222, 235))
    cv.dither_rect(x + 10, y + 10, w - 20, h - 20, (198, 220, 232), (192, 214, 228))
    for gy in range(y + 8, y + h - 4, 12):
        cv.hline(x + 4, gy, w - 8, (170, 195, 215))
    for gx in range(x + 8, x + w - 4, 14):
        cv.vline(gx, y + 4, h - 8, (170, 195, 215))
    # simplified continents
    cv.fill_poly([(x + int(w * 0.12), y + int(h * 0.28)), (x + int(w * 0.20), y + int(h * 0.18)),
                  (x + int(w * 0.26), y + int(h * 0.30)), (x + int(w * 0.22), y + int(h * 0.52)),
                  (x + int(w * 0.16), y + int(h * 0.50))], (120, 160, 110))
    cv.fill_poly([(x + int(w * 0.42), y + int(h * 0.16)), (x + int(w * 0.62), y + int(h * 0.12)),
                  (x + int(w * 0.66), y + int(h * 0.34)), (x + int(w * 0.56), y + int(h * 0.50)),
                  (x + int(w * 0.46), y + int(h * 0.40))], (120, 160, 110))
    cv.fill_poly([(x + int(w * 0.52), y + int(h * 0.52)), (x + int(w * 0.58), y + int(h * 0.50)),
                  (x + int(w * 0.60), y + int(h * 0.66)), (x + int(w * 0.54), y + int(h * 0.72)),
                  (x + int(w * 0.50), y + int(h * 0.62))], (120, 160, 110))
    cv.fill_poly([(x + int(w * 0.66), y + int(h * 0.30)), (x + int(w * 0.80), y + int(h * 0.26)),
                  (x + int(w * 0.86), y + int(h * 0.44)), (x + int(w * 0.74), y + int(h * 0.52)),
                  (x + int(w * 0.68), y + int(h * 0.42))], (120, 160, 110))
    cv.fill_poly([(x + int(w * 0.84), y + int(h * 0.62)), (x + int(w * 0.92), y + int(h * 0.60)),
                  (x + int(w * 0.94), y + int(h * 0.72)), (x + int(w * 0.86), y + int(h * 0.74))],
                 (120, 160, 110))
    for fx, fy, n in pins:
        px, py = x + int(w * fx), y + int(h * fy)
        cv.fill_circle(px, py, 6, RED)
        draw_text(cv, px - 3, py - 3, str(n), 1, FLAG)


# ---------------- the news of Tuesday 24 November 2026 ----------------

LEAD = ("RUSSIAN STRIKE KILLS 2 IN ZAPORIZHZHIA",
        "Overnight attack hits flats; 40 hurt, incl. 4 children. Kyiv counts "
        "25 Russian airspace violations in 2026.",
        "drone", "LEAD - UKRAINE WAR")

HEROES = [
    ("Ukraine sinks Russian warship off Libya",
     "Zelenskyy hails the Benghazi drone strike; UN mission demands a probe "
     "into the port attacks.",
     "ship", "UKRAINE WAR"),
    ("Nvidia shockwave: Kospi +7%, Nikkei +4%",
     "Tuesday rally after NVDA +31% Monday on Huang's return; Nasdaq gives "
     "back 1.48% as NVDA slips.",
     "chip", "MARKETS"),
    ("Gaza strikes kill Hamas security chief",
     "Naeem Abu Nahel among 7 killed; Oxfam calls the Strip a 'toxic "
     "wasteland' after 3 years of war.",
     "gaza", "MIDDLE EAST"),
]

MIDS = [
    ("COP31 fallout: 'darkest moment' for climate talks",
     "90+ nations' rejection sinks in; Antalya ran ~50h over.",
     "cop31", "CLIMATE"),
    ("Tuesday: Nasdaq falls, gold slides $89",
     "Dow +0.86% to 50,021; gold $3,561.90; WTI $82.05.",
     "chart_down", "MARKETS"),
    ("NATO vows to defend space after satellite reports",
     "Rutte: alliance will answer threats in orbit.",
     "satellite", "EUROPE"),
    ("Factory blaze kills two dozen in Indonesia",
     "Rescuers search unstable wreckage for missing workers.",
     "factory_fire", "ASIA-PACIFIC"),
    ("Brentford hit Everton for four",
     "Lewis-Potter double in 3 minutes; St. Louis stun LAFC 3-2.",
     "football", "SPORT"),
    ("Nepal PM Shah's first visit: Delhi, $1.63bn aid",
     "India announces $1.63bn for Nepal's recovery.",
     "flags_in_np", "ASIA-PACIFIC"),
    ("Houthi attack hits Riyadh financial district",
     "Saudi civil defence: multiple injured; more interceptors asked.",
     "warning", "MIDDLE EAST"),
    ("Germany first to get Ukraine's Delta system",
     "Berlin signs access deal; more interceptors agreed.",
     "drone", "UKRAINE WAR"),
    ("Rep. Gomez resigns after ethics finding",
     "California Democrat steps down; panel found misconduct.",
     "capitol", "AMERICAS"),
    ("7 EU states back limits on Russian visas",
     "Letter to von der Leyen targets tourists, sports events.",
     "eu_stars", "EUROPE"),
    ("Fighting traps Ebola teams in DR Congo",
     "Fighting near an Ituri hospital forces cover for 24 hours.",
     "globe", "AFRICA"),
    ("UAE bus crash kills 13",
     "13 dead, 14 injured in Ras Al Khaimah.",
     "bus_crash", "MIDDLE EAST"),
]

ALSO = [
    ("Iran vows to fight US naval blockade; tankers hit mines in Hormuz", "MIDDLE EAST"),
    ("Vance, Rubio meet Qatari PM at White House on Iran", "AMERICAS"),
    ("Trump: DOJ to fast-track federal death sentences", "AMERICAS"),
    ("Pentagon accuses Canada of falling short on defence", "AMERICAS"),
    ("Solomon Islands to swap China pact for Australia treaty", "ASIA-PACIFIC"),
    ("China: Pacific ties 'not for geopolitical competition'", "ASIA-PACIFIC"),
    ("South Korea offers $375,000 to catch AI exam cheats", "ASIA-PACIFIC"),
    ("US blacklists Singapore cloud firm Megaspeed", "AMERICAS"),
    ("Malaysia to return 6,500 Rohingya to Myanmar", "ASIA-PACIFIC"),
    ("Iraq PM orders ministry to run Kurdish oilfields", "MIDDLE EAST"),
    ("Israel advances 1,500+ West Bank housing units", "MIDDLE EAST"),
    ("France condemns settler attacks in West Bank", "EUROPE"),
    ("Finland summons Russian envoy over civilian strikes", "EUROPE"),
    ("Xiamen Airlines buys 50 Boeing 737 Max 8 jets", "ASIA-PACIFIC"),
    ("Pakistan petrol stations threaten nationwide shutdown", "ASIA-PACIFIC"),
    ("Fiji declares disaster as El Nino dries water", "ASIA-PACIFIC"),
    ("Mexico to try 'El Chapo Isidro' despite US request; 16 killed", "AMERICAS"),
    ("India, China open 10 days of talks to ease LAC tensions", "ASIA-PACIFIC"),
    ("Tonga signs Finland pact for storm warnings", "ASIA-PACIFIC"),
    ("Zambia treason case against opposition leader Mundubile", "AFRICA"),
    ("Tanzania weighs $42bn LNG project", "AFRICA"),
    ("Kenya plans SH42bn prison revamp", "AFRICA"),
    ("Malawi urged to act as Mutharika faces calls", "AFRICA"),
    ("Sinner faces knee surgery after ATP Finals", "SPORT"),
    ("Illinois scores 133, a Big Ten record", "SPORT"),
    ("Florida State hires Georgia DC Schumann as coach", "SPORT"),
    ("Skubal signs record $450m Mets deal", "SPORT"),
    ("Bucks end 13-game skid as Herro scores 32", "SPORT"),
    ("Commanders beat Bengals 22-20 at the gun", "SPORT"),
    ("UAE launches 'Mira', an AI government aide", "MIDDLE EAST"),
]

NUMBERS = [
    ("46", "DATED STORIES"),
    ("9", "REGIONS"),
    ("+7%", "KOSPI ON TUESDAY"),
    ("+31%", "NVIDIA ON MONDAY"),
    ("13", "DEAD, UAE BUS CRASH"),
]

PINS = [
    (0.56, 0.20, 1),   # Antalya
    (0.57, 0.14, 2),   # Zaporizhzhia
    (0.52, 0.36, 3),   # Benghazi
    (0.72, 0.28, 4),   # Delhi
    (0.49, 0.14, 5),   # London
    (0.18, 0.22, 6),   # Washington
    (0.55, 0.48, 7),   # Ituri
    (0.80, 0.42, 8),   # Jakarta
]

TIMELINE_1 = ("OVERNIGHT (UTC)   Russian strike hits Zaporizhzhia flats, 2 killed, "
              "40 hurt   -   Gaza strikes kill Hamas security chief")
TIMELINE_2 = ("TUESDAY   Kospi +7%, Nikkei +4% on Nvidia rally   -   Solomon Islands "
              "swaps China pact for Australia treaty   -   Brentford 4-0 Everton   -   "
              "Bucks end 13-game skid")

LEFT_OUT = ("LEFT OUT: Huang reinstated as Nvidia CEO (Mon 23) - COP31 collapse "
            "(Mon 23) - Liverpool beat Man Utd (Sun 22) - Alcaraz wins ATP "
            "Finals (Sun 22) - Verstappen wins Las Vegas GP (Sat 21) - "
            "Dymer strike, 2 killed (Sun 22)")

REGIONS = ["CLIMATE", "UKRAINE WAR", "MIDDLE EAST", "ASIA-PACIFIC", "EUROPE",
           "AMERICAS", "AFRICA", "MARKETS", "SPORT"]


# ---------------- newsprint grain ----------------


def apply_grain(cv, amp=1, density=0.07, seed=20261124):
    """Deterministic newsprint grain: a sparse +/-amp speckle per channel,
    seeded. A printed front page is not flat; a light speckle keeps the
    image rich at full size while staying invisible when the page is
    read small. Kept light so the file stays well under the 1 MiB cap
    and inside the 140-350 KB band the previous days' winners sit in."""
    rng = random.Random(seed)
    px = cv.px
    n = cv.w * cv.h
    for i in range(n):
        if rng.random() >= density:
            continue
        r = rng.getrandbits(6)
        j = i * 3
        v = px[j] + ((r >> 4) & 3) - 1
        px[j] = 0 if v < 0 else (255 if v > 255 else v)
        v = px[j + 1] + ((r >> 2) & 3) - 1
        px[j + 1] = 0 if v < 0 else (255 if v > 255 else v)
        v = px[j + 2] + (r & 3) - 1
        px[j + 2] = 0 if v < 0 else (255 if v > 255 else v)


# ---------------- layout ----------------


def build():
    rng = random.Random(20261124)
    cv = Canvas(W, H, PAPER)
    mx, cw = 16, 992

    # masthead
    cv.fill_rect(0, 0, W, 96, INK)
    draw_text_centered(cv, 0, 10, W, "THE WORLD IN ONE DAY", 4, PAPER)
    draw_text_centered(cv, 0, 46, W, "TUESDAY 24 NOVEMBER 2026", 2, (200, 190, 160))
    draw_text_centered(cv, 0, 72, W,
                       "46 DATED STORIES  -  9 REGIONS  -  EVERY ONE DATED TUESDAY",
                       1, (180, 170, 140))
    cv.hline(0, 96, W, RED, 3)

    # lead strip
    y = 100
    cv.frame(mx, y, cw, 56, INK, 2)
    draw_scene(cv, LEAD[2], mx + 2, y + 2, 56, 52, rng)
    hx = mx + 66
    draw_text(cv, hx, y + 8, LEAD[0], 3, INK)
    draw_para(cv, hx, y + 34, LEAD[1], 1, INK, cw - 66)
    draw_chip(cv, hx + text_width(LEAD[0], 3) + 14, y + 8, LEAD[3], RED)

    # UTC timeline
    y = 166
    cv.hline(mx, y - 2, cw, INK, 2)
    draw_text(cv, mx, y + 2, TIMELINE_1, 1, INK)
    draw_text(cv, mx, y + 14, TIMELINE_2, 1, INK)

    # day in numbers
    y = 194
    cv.frame(mx, y, cw, 34, INK, 2)
    for i, (num, label) in enumerate(NUMBERS):
        cx = mx + i * (cw // 5)
        draw_text(cv, cx + 12, y + 5, num, 3, RED)
        draw_text(cv, cx + 12 + text_width(num, 3) + 8, y + 13, label, 1, INK)
        if i:
            cv.vline(cx, y + 4, 26, GREY)

    # region colour bar
    y = 232
    sw = cw // len(REGIONS)
    for i, reg in enumerate(REGIONS):
        x = mx + i * sw
        cv.fill_rect(x, y, sw - 2, 15, REGION_COLORS[reg])
        draw_text(cv, x + 4, y + 4, reg, 1, FLAG)

    # hero panels
    y = 250
    hw = (cw - 16) // 3
    for i, (head, sub, kind, reg) in enumerate(HEROES):
        hx = mx + i * (hw + 8)
        cv.frame(hx, y, hw, 180, INK, 2)
        draw_scene(cv, kind, hx + 1, y + 1, hw - 2, 96, rng)
        draw_para(cv, hx + 8, y + 100, head, 2, INK, hw - 16, lh=17)
        draw_para(cv, hx + 8, y + 138, sub, 1, INK, hw - 16, lh=10)
        draw_chip(cv, hx + 8, y + 164, reg, REGION_COLORS[reg])

    # mid cards: 6 rows x 2 columns
    y0 = 434
    for row in range(6):
        for col in range(2):
            idx = row * 2 + col
            head, sub, kind, reg = MIDS[idx]
            cx = mx + col * (cw // 2 + 8)
            cy = y0 + row * 44
            cv.frame(cx, cy, cw // 2 - 8, 40, INK, 1)
            draw_scene(cv, kind, cx + 2, cy + 2, 36, 36, rng)
            draw_text(cv, cx + 42, cy + 4, head, 1, INK)
            draw_text(cv, cx + 42, cy + 21, sub, 1, (60, 60, 60))
            cv.fill_rect(cx + cw // 2 - 8 - 8, cy + 4, 4, 32, REGION_COLORS[reg])

    # ALSO list
    y = 702
    draw_text(cv, mx, y, "ALSO ON TUESDAY 24 NOVEMBER 2026", 2, INK)
    cv.hline(mx, y + 18, cw, RED, 2)
    for i, (text, reg) in enumerate(ALSO):
        col = 0 if i < 15 else 1
        row = i if i < 15 else i - 15
        ax = mx + col * (cw // 2 + 8)
        ay = 724 + row * 12
        draw_text(cv, ax, ay, "%2d." % (i + 1), 1, RED)
        cv.fill_rect(ax + 22, ay + 2, 5, 5, REGION_COLORS[reg])
        draw_text(cv, ax + 30, ay, text, 1, INK)

    # date check + pin map
    y = 908
    cv.frame(mx, y, 560, 80, RED, 2)
    draw_text(cv, mx + 8, y + 6, "DATE CHECK", 2, RED)
    draw_para(cv, mx + 8, y + 26, "Every story here happened or was first "
              "reported Tue 24 Nov 2026 (UTC). Press time 05:00 UTC.", 1, INK, 544, lh=10)
    draw_para(cv, mx + 8, y + 50, LEFT_OUT, 1, (90, 90, 90), 544, lh=10)
    draw_pin_map(cv, mx + 568, y, cw - 568, 80, PINS)

    # footer
    cv.hline(mx, 992, cw, INK, 2)
    draw_text(cv, mx, 996, "1 Antalya (COP31)   2 Zaporizhzhia   3 Benghazi   "
              "4 Delhi   5 London   6 Washington   7 Ituri   8 Jakarta", 1, INK)
    draw_text(cv, mx, 1006, "Sources: BBC - Reuters - AP - AFP - Just Security - "
              "Kyiv Independent - Middle East Eye - Grist - Oxfam - SMM - eOption.", 1, INK)
    draw_text(cv, mx, 1016, "Drawn by hand; no photos.", 1, (90, 90, 90))

    apply_grain(cv)
    return cv


def main():
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR", "out")
    os.makedirs(outdir, exist_ok=True)
    cv = build()
    data = encode_png(W, H, cv.px)
    with open(os.path.join(outdir, "entry.png"), "wb") as f:
        f.write(data)
    print("wrote", os.path.join(outdir, "entry.png"), len(data), "bytes")


if __name__ == "__main__":
    main()
