#!/usr/bin/env python3
"""PERPETUA - the desk fan that powers itself.

A small pure-stdlib rasterizer that paints a catalogue photograph of an
impossible gadget: a modern desk fan, blades spinning, whose power cord
loops out of its own base and plugs back into a socket on its own body.
One accessory only: a plain coffee mug, for scale. No network, no files
read, no randomness -- two runs are byte-identical.

Writes /output/entry.png (1024x1024 PNG).
"""

import math
import os
import struct
import zlib

W = 1024
H = 1024
OUT = "/output/entry.png"

# ---------------------------------------------------------------- framebuffer

fb = bytearray(W * H * 3)


def _idx(x, y):
    return (y * W + x) * 3


def put(x, y, r, g, b):
    if 0 <= x < W and 0 <= y < H:
        i = _idx(x, y)
        fb[i] = r
        fb[i + 1] = g
        fb[i + 2] = b


def blend(x, y, r, g, b, a):
    """Alpha-blend a colour over the pixel at (x, y). a in 0..1."""
    if 0 <= x < W and 0 <= y < H and a > 0.0:
        i = _idx(x, y)
        if a >= 1.0:
            fb[i] = r
            fb[i + 1] = g
            fb[i + 2] = b
        else:
            fb[i] = int(fb[i] + (r - fb[i]) * a)
            fb[i + 1] = int(fb[i + 1] + (g - fb[i + 1]) * a)
            fb[i + 2] = int(fb[i + 2] + (b - fb[i + 2]) * a)


def clamp255(v):
    if v < 0:
        return 0
    if v > 255:
        return 255
    return int(v)


def mix(c0, c1, t):
    return (clamp255(c0[0] + (c1[0] - c0[0]) * t),
            clamp255(c0[1] + (c1[1] - c0[1]) * t),
            clamp255(c0[2] + (c1[2] - c0[2]) * t))


def smooth(t):
    if t < 0.0:
        return 0.0
    if t > 1.0:
        return 1.0
    return t * t * (3.0 - 2.0 * t)


# ---------------------------------------------------------------- backdrop

# Warm off-white seamless sweep: wall above, desk below, curved join.
WALL_TOP = (239, 233, 223)
WALL_LOW = (228, 221, 210)
DESK_TOP = (206, 198, 187)
DESK_LOW = (176, 168, 157)

# Soft key-light pool, upper left (separable 1-D gaussians).
_kx = [math.exp(-((x - 390.0) ** 2) / (2.0 * 430.0 ** 2)) for x in range(W)]
_ky = [math.exp(-((y - 300.0) ** 2) / (2.0 * 430.0 ** 2)) for y in range(H)]


def paint_backdrop():
    for y in range(H):
        if y < 600:
            t = y / 600.0
            base = mix(WALL_TOP, WALL_LOW, t)
        elif y < 700:
            base = mix(WALL_LOW, DESK_TOP, smooth((y - 600) / 100.0))
        else:
            base = mix(DESK_TOP, DESK_LOW, (y - 700) / 324.0)
        ky = _ky[y]
        row = y * W * 3
        r0, g0, b0 = base
        for x in range(W):
            lift = 14.0 * _kx[x] * ky
            i = row + x * 3
            fb[i] = clamp255(r0 + lift)
            fb[i + 1] = clamp255(g0 + lift)
            fb[i + 2] = clamp255(b0 + lift)


# ---------------------------------------------------------------- shapes

def disc(cx, cy, rad, colour, alpha=1.0):
    """Filled disc; colour may be a tuple or a function (x, y) -> tuple."""
    r = int(rad)
    func = callable(colour)
    for y in range(cy - r, cy + r + 1):
        if y < 0 or y >= H:
            continue
        dy = y - cy
        dx = int(math.sqrt(max(0, rad * rad - dy * dy)))
        x0 = max(0, cx - dx)
        x1 = min(W - 1, cx + dx)
        for x in range(x0, x1 + 1):
            c = colour(x, y) if func else colour
            if alpha >= 1.0:
                put(x, y, c[0], c[1], c[2])
            else:
                blend(x, y, c[0], c[1], c[2], alpha)


def ring(cx, cy, r_out, r_in, colour, alpha=1.0):
    """Filled annulus."""
    for y in range(cy - int(r_out), cy + int(r_out) + 1):
        if y < 0 or y >= H:
            continue
        dy = y - cy
        dyo = math.sqrt(max(0.0, r_out * r_out - dy * dy))
        dyi = math.sqrt(max(0.0, r_in * r_in - dy * dy)) if abs(dy) < r_in else 0.0
        for x0, x1 in ((cx - dyo, cx - dyi), (cx + dyi, cx + dyo)):
            xa = max(0, int(math.ceil(x0)))
            xb = min(W - 1, int(math.floor(x1)))
            for x in range(xa, xb + 1):
                if alpha >= 1.0:
                    put(x, y, colour[0], colour[1], colour[2])
                else:
                    blend(x, y, colour[0], colour[1], colour[2], alpha)


def ellipse(cx, cy, rx, ry, colour, alpha=1.0):
    for y in range(int(cy - ry), int(cy + ry) + 1):
        if y < 0 or y >= H:
            continue
        dy = (y - cy) / ry
        rem = 1.0 - dy * dy
        if rem <= 0.0:
            continue
        dx = int(rx * math.sqrt(rem))
        for x in range(max(0, cx - dx), min(W - 1, cx + dx) + 1):
            if alpha >= 1.0:
                put(x, y, colour[0], colour[1], colour[2])
            else:
                blend(x, y, colour[0], colour[1], colour[2], alpha)


def soft_shadow(cx, cy, rx, ry, strength=0.30):
    """Layered ellipses: a soft contact shadow with no blur pass."""
    layers = 9
    for k in range(layers, 0, -1):
        t = k / layers
        a = strength * (1.0 - t) * 0.28
        ellipse(cx, cy, int(rx * (0.55 + 0.45 * t)),
                int(ry * (0.55 + 0.45 * t)), (52, 46, 40), a)


def hspan(y, x0, x1, colour, alpha=1.0):
    xa = max(0, int(x0))
    xb = min(W - 1, int(x1))
    if y < 0 or y >= H or xa > xb:
        return
    for x in range(xa, xb + 1):
        if alpha >= 1.0:
            put(x, y, colour[0], colour[1], colour[2])
        else:
            blend(x, y, colour[0], colour[1], colour[2], alpha)


def rounded_rect(x0, y0, x1, y1, rad, shade):
    """Rounded rect; shade(y, t) -> colour, t = 0 top .. 1 bottom."""
    rad = min(rad, (x1 - x0) / 2.0, (y1 - y0) / 2.0)
    for y in range(int(y0), int(y1) + 1):
        if y < 0 or y >= H:
            continue
        t = (y - y0) / max(1.0, (y1 - y0))
        c = shade(y, t)
        if y < y0 + rad:
            dy = y0 + rad - y
            dx = int(math.sqrt(max(0.0, rad * rad - dy * dy)))
            xa, xb = x0 + rad - dx, x1 - rad + dx
        elif y > y1 - rad:
            dy = y - (y1 - rad)
            dx = int(math.sqrt(max(0.0, rad * rad - dy * dy)))
            xa, xb = x0 + rad - dx, x1 - rad + dx
        else:
            xa, xb = x0, x1
        hspan(y, xa, xb, c)


def line_stamp(x0, y0, x1, y1, radius, colour, alpha=1.0):
    """Thick line drawn as a chain of small discs."""
    steps = int(max(abs(x1 - x0), abs(y1 - y0)) * 1.5) + 2
    for k in range(steps + 1):
        t = k / steps
        disc(int(x0 + (x1 - x0) * t), int(y0 + (y1 - y0) * t),
             radius, colour, alpha)


def bezier_stamp(p0, p1, p2, p3, radius, colour, alpha=1.0, steps=260):
    for k in range(steps + 1):
        t = k / steps
        u = 1.0 - t
        x = (u ** 3 * p0[0] + 3 * u * u * t * p1[0]
             + 3 * u * t * t * p2[0] + t ** 3 * p3[0])
        y = (u ** 3 * p0[1] + 3 * u * u * t * p1[1]
             + 3 * u * t * t * p2[1] + t ** 3 * p3[1])
        disc(int(x), int(y), radius, colour, alpha)


# ---------------------------------------------------------------- tiny font

# 5x7 bitmap glyphs, only the letters the brand plate needs.
FONT = {
    "P": ("01110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "R": ("01110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
}


def draw_text(cx, top, word, colour, scale=1):
    """Centred 5x7 text; scale 1 draws 5x7 px per glyph."""
    widths = [5 * scale for _ in word]
    total = sum(widths) + (len(word) - 1) * scale
    x = int(cx - total / 2.0)
    for ch in word:
        glyph = FONT.get(ch)
        if glyph is None:
            x += 6 * scale
            continue
        for row_i, row in enumerate(glyph):
            for col_i, bit in enumerate(row):
                if bit == "1":
                    for dy in range(scale):
                        for dx in range(scale):
                            put(x + col_i * scale + dx,
                                top + row_i * scale + dy,
                                colour[0], colour[1], colour[2])
        x += 6 * scale


# ---------------------------------------------------------------- the fan

CREAM_HI = (247, 243, 233)
CREAM = (233, 226, 211)
CREAM_LO = (206, 197, 181)
CHARCOAL = (56, 54, 52)
CHARCOAL_SOFT = (84, 81, 77)
BLADE_HI = (202, 206, 210)
BLADE_LO = (164, 168, 173)
CORD = (48, 46, 44)
CORD_HI = (104, 100, 94)

FAN_CX = 455
FAN_CY = 478
FAN_R = 215


def paint_fan():
    # ---- head housing: cream disc, then dark grille ring
    disc(FAN_CX, FAN_CY, FAN_R + 4,
         lambda x, y: mix(CREAM, CREAM_LO,
                          smooth(math.hypot(x - FAN_CX, y - FAN_CY) / (FAN_R + 4))))
    # top-edge highlight on the housing
    ring(FAN_CX, FAN_CY, FAN_R + 4, FAN_R - 2, CREAM_HI, 0.55)

    # ---- spinning blade disc: radial falloff + angular swirl = motion blur
    def blade_shade(x, y):
        dx = x - FAN_CX
        dy = y - FAN_CY
        r = math.hypot(dx, dy)
        t = r / 200.0
        ang = math.atan2(dy, dx)
        swirl = 0.5 + 0.5 * math.sin(5.0 * ang + r * 0.06)
        base = mix(BLADE_HI, BLADE_LO, smooth(t))
        lift = int(16.0 * swirl * (1.0 - t * 0.6))
        return (clamp255(base[0] + lift), clamp255(base[1] + lift),
                clamp255(base[2] + lift))

    disc(FAN_CX, FAN_CY, 200, blade_shade)
    # soften the swirl so it reads as a blurred spinning disc, not blades
    disc(FAN_CX, FAN_CY, 200, (188, 192, 196), 0.22)

    # ---- grille: concentric rings + radial spokes, thin dark metal
    for rr in (72, 97, 122, 147, 172, 196):
        ring(FAN_CX, FAN_CY, rr + 1.5, rr - 1.5, CHARCOAL)
    for k in range(12):
        a = math.radians(k * 30.0)
        x0 = FAN_CX + int(58 * math.cos(a))
        y0 = FAN_CY + int(58 * math.sin(a))
        x1 = FAN_CX + int(206 * math.cos(a))
        y1 = FAN_CY + int(206 * math.sin(a))
        line_stamp(x0, y0, x1, y1, 2, CHARCOAL)
    ring(FAN_CX, FAN_CY, 210, 202, CHARCOAL)
    ring(FAN_CX, FAN_CY, 202, 200, CHARCOAL_SOFT)

    # ---- hub cap with brand plate
    disc(FAN_CX, FAN_CY, 56,
         lambda x, y: mix(CREAM_HI, CREAM_LO,
                          smooth(math.hypot(x - FAN_CX, y - FAN_CY) / 56.0)))
    ellipse(FAN_CX - 16, FAN_CY - 20, 26, 13, (255, 252, 244), 0.5)
    rounded_rect(FAN_CX - 46, FAN_CY - 9, FAN_CX + 46, FAN_CY + 9, 6,
                 lambda y, t: mix((226, 218, 202), (204, 194, 176), t))
    draw_text(FAN_CX, FAN_CY - 4, "PERPETUA", (74, 70, 64), scale=1)

    # ---- neck: tapered post from head to base
    for y in range(632, 776):
        t = (y - 632) / 144.0
        half = 34.0 + 14.0 * t
        c = mix(CREAM_HI, CREAM_LO, t * 0.7)
        hspan(y, FAN_CX - half, FAN_CX + half, c)
    # neck shading: soft right-side shade, left-side light
    for y in range(632, 776):
        t = (y - 632) / 144.0
        half = 34.0 + 14.0 * t
        hspan(y, FAN_CX + half - 12, FAN_CX + half, (196, 187, 170), 0.55)
        hspan(y, FAN_CX - half, FAN_CX - half + 8, (250, 246, 238), 0.5)

    # ---- base: moulded-plastic foot
    rounded_rect(348, 760, 562, 828, 18,
                 lambda y, t: mix(CREAM_HI, CREAM_LO, t))
    # top edge highlight, bottom edge shade
    hspan(762, 366, 544, (252, 248, 240), 0.9)
    hspan(826, 366, 544, (186, 177, 160), 0.8)
    # round socket on the base front, with the plug seated in it (left)
    disc(398, 793, 17, (38, 36, 34))
    ring(398, 793, 17, 14, (120, 114, 106))
    # plug body, seated in the socket
    rounded_rect(378, 782, 418, 806, 7,
                 lambda y, t: mix((88, 84, 80), (52, 50, 47), t))
    hspan(783, 382, 414, (140, 134, 126), 0.7)
    # rocker switch on the base front (right)
    rounded_rect(512, 784, 540, 802, 5,
                 lambda y, t: mix((92, 88, 84), (58, 55, 52), t))
    hspan(785, 516, 536, (128, 122, 114), 0.7)


def paint_cord():
    """The joke: the cord leaves the base's right edge, loops across the
    desk, and plugs back into the socket on the base's left side."""
    # main loop: out of the base's right edge, down, around, back to the plug
    bezier_stamp((560, 792), (835, 830), (800, 955), (406, 800), 8, CORD)
    # highlight along the upper edge of the cord for roundness
    bezier_stamp((560, 788), (833, 824), (796, 947), (406, 796), 3, CORD_HI,
                 alpha=0.8)
    # cord's far end disappears into the plug
    disc(406, 798, 9, CORD)


# ---------------------------------------------------------------- the mug

MUG_CX = 772
MUG_TOP = 668
MUG_BOT = 824


def paint_mug():
    # handle: sage ring segment on the right side
    for y in range(MUG_TOP + 8, MUG_BOT - 8):
        dy = y - 746
        if abs(dy) > 52:
            continue
        # outer and inner half-widths of the handle ring
        xo = math.sqrt(max(0.0, 52 * 52 - dy * dy))
        xi = math.sqrt(max(0.0, 40 * 40 - dy * dy)) if abs(dy) < 40 else 0.0
        xa = MUG_CX + 52 + int(xi) - 12
        xb = MUG_CX + 52 + int(xo)
        hspan(y, xa, xb, (118, 132, 110))
    # body: cylinder with a left-lit horizontal gradient
    for y in range(MUG_TOP, MUG_BOT + 1):
        t = (y - MUG_TOP) / (MUG_BOT - MUG_TOP)
        for x in range(MUG_CX - 58, MUG_CX + 59):
            u = (x - (MUG_CX - 58)) / 116.0
            c = mix((172, 186, 160), (100, 114, 92), smooth(u))
            # gentle vertical shading: brighter near the rim
            lift = int(10.0 * (1.0 - t))
            put(x, y, clamp255(c[0] + lift), clamp255(c[1] + lift),
                clamp255(c[2] + lift))
    # rounded bottom corners
    for y in range(MUG_BOT - 14, MUG_BOT + 1):
        dy = y - (MUG_BOT - 14)
        dx = int(math.sqrt(max(0.0, 14 * 14 - dy * dy)))
        hspan(y, MUG_CX - 58, MUG_CX - 58 + (14 - dx), DESK_TOP)
        hspan(y, MUG_CX + 58 - (14 - dx), MUG_CX + 58, DESK_TOP)
    # rim + coffee surface
    ellipse(MUG_CX, MUG_TOP, 58, 12, (186, 200, 174))
    ellipse(MUG_CX, MUG_TOP, 50, 9, (66, 46, 34))
    ellipse(MUG_CX - 12, MUG_TOP - 1, 22, 4, (96, 68, 50), 0.7)


# ---------------------------------------------------------------- finishing

def paint_shadows_and_reflection():
    soft_shadow(FAN_CX, 830, 205, 20, 0.32)
    soft_shadow(MUG_CX, 826, 82, 14, 0.30)
    # faint floor reflection under the fan base
    for y in range(830, 874):
        t = (y - 830) / 44.0
        a = 0.05 * (1.0 - t)
        hspan(y, 372, 538, (214, 206, 192), a)


def finish():
    """Gentle vignette + fixed-seed grain, one pass over the frame."""
    cx, cy = W / 2.0, H / 2.0
    maxd2 = cx * cx + cy * cy
    for y in range(H):
        dy = y - cy
        row = y * W * 3
        for x in range(W):
            dx = x - cx
            vig = 1.0 - 0.10 * (dx * dx + dy * dy) / maxd2
            h = ((x * 2654435761) ^ (y * 40503) ^ 0x9E3779B9) & 0xFFFF
            grain = (h % 5) - 2
            i = row + x * 3
            fb[i] = clamp255(fb[i] * vig + grain)
            fb[i + 1] = clamp255(fb[i + 1] * vig + grain)
            fb[i + 2] = clamp255(fb[i + 2] * vig + grain)


# ---------------------------------------------------------------- PNG encode

def _chunk(kind, data):
    return (struct.pack(">I", len(data)) + kind + data
            + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF))


def encode_png():
    raw = bytearray()
    for y in range(H):
        raw.append(0)
        raw += fb[y * W * 3:(y + 1) * W * 3]
    png = (b"\x89PNG\r\n\x1a\n"
           + _chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
           + _chunk(b"IDAT", zlib.compress(bytes(raw), 9))
           + _chunk(b"IEND", b""))
    return png


def main():
    paint_backdrop()
    paint_shadows_and_reflection()
    paint_fan()
    paint_cord()
    paint_mug()
    finish()
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "wb") as f:
        f.write(encode_png())


if __name__ == "__main__":
    main()
