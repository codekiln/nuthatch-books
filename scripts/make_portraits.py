"""Make the family's 64x80 pixel-art portraits, a day and a night version of each.

Nuthatch and fawnicorn are downsampled from their existing paintings.
Supplied JPEG portraits are preserved and used for both themes.
The drawing functions below provide fallbacks for portraits without a JPEG.

    uv run --with pillow python -I scripts/make_portraits.py [--sheet PATH]

--sheet also writes a contact sheet of all twelve portraits at 4x.
"""

import argparse
import math
import os
import random
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "site" / "img" / "portraits"
SOURCE = Path(
    os.environ.get(
        "PORTRAIT_SOURCE",
        Path.home() / "ghq/github.com/codekiln/beans/public/images",
    )
)

W, H = 64, 80  # final pixel grid
S = 4  # shapes are rasterised at S x and box-reduced, so edges stay crisp
COLORS = 32  # palette size for every portrait

SLUGS = ["nuthatch", "wonderful-cat", "fawnicorn", "treefrog", "rabbit", "pigeon"]


# --- colour -----------------------------------------------------------------


def rgb(c):
    if isinstance(c, tuple):
        return c[:3]
    c = c.lstrip("#")
    return tuple(int(c[i : i + 2], 16) for i in (0, 2, 4))


def mix(a, b, t):
    a, b = rgb(a), rgb(b)
    return tuple(round(x + (y - x) * t) for x, y in zip(a, b))


def tints(night):
    """Return (character tint, scenery tint) for the time of day."""
    if not night:
        return rgb, rgb

    def tc(c):
        r, g, b = mix(c, (92, 88, 170), 0.1)
        return (round(r * 0.92), round(g * 0.92), min(255, round(b * 1.0)))

    def tb(c):
        r, g, b = mix(c, (40, 40, 104), 0.5)
        return (round(r * 0.8), round(g * 0.8), round(b * 0.92))

    return tc, tb


# --- masks ------------------------------------------------------------------


def blank():
    return Image.new("L", (W, H), 0)


def _canvas():
    im = Image.new("L", (W * S, H * S), 0)
    return im, ImageDraw.Draw(im)


def _reduce(im, threshold=128):
    return im.resize((W, H), Image.BOX).point(lambda v: 255 if v >= threshold else 0)


def ellipse_pts(cx, cy, rx, ry, angle=0, n=72):
    a = math.radians(angle)
    ca, sa = math.cos(a), math.sin(a)
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        x, y = rx * math.cos(t), ry * math.sin(t)
        pts.append((cx + x * ca - y * sa, cy + x * sa + y * ca))
    return pts


def poly(pts, threshold=128):
    im, d = _canvas()
    d.polygon([(x * S, y * S) for x, y in pts], fill=255)
    return _reduce(im, threshold)


def ell(cx, cy, rx, ry, angle=0):
    return poly(ellipse_pts(cx, cy, rx, ry, angle))


def line(pts, width=1.0):
    im, d = _canvas()
    d.line([(x * S, y * S) for x, y in pts], fill=255, width=max(1, round(width * S)), joint="curve")
    return _reduce(im, 100)


def rect(x0, y0, x1, y1):
    m = blank()
    ImageDraw.Draw(m).rectangle((x0, y0, x1 - 1, y1 - 1), fill=255)
    return m


def U(*ms):
    out = ms[0]
    for m in ms[1:]:
        out = ImageChops.lighter(out, m)
    return out


def inter(a, b):
    return ImageChops.darker(a, b)


def minus(a, b):
    return ImageChops.subtract(a, b)


def shift(m, dx, dy):
    out = blank()
    out.paste(m, (dx, dy))
    return out


def dilate(m):
    return U(m, shift(m, 1, 0), shift(m, -1, 0), shift(m, 0, 1), shift(m, 0, -1))


def erode(m):
    return ImageChops.invert(dilate(ImageChops.invert(m)))


# --- painting ---------------------------------------------------------------


class Layer:
    def __init__(self):
        self.im = Image.new("RGB", (W, H), (0, 0, 0))

    def fill(self, m, col):
        self.im.paste(rgb(col), (0, 0, W, H), m)

    def px(self, pts, col):
        col = rgb(col)
        for x, y in pts:
            if 0 <= x < W and 0 <= y < H:
                self.im.putpixel((x, y), col)

    def part(self, m, base, lo=None, hi=None, *, outline=None, k=2, hi_mask=None, lo_mask=None, j=2):
        """Fill a shape with cel shading lit from the upper left, plus a 1px outline."""
        if outline is not None:
            self.fill(minus(dilate(m), m), outline)
        self.fill(m, base)
        if lo is not None:
            shade = lo_mask if lo_mask is not None else minus(m, shift(m, -k, -k))
            self.fill(inter(m, shade), lo)
        if hi is not None:
            if hi_mask is not None:
                light = inter(erode(m), hi_mask)
            else:
                e = erode(m)
                light = minus(e, shift(e, j, j))
            self.fill(light, hi)


EYE_BIG = [
    ".OOOO.",
    "OWWPPO",
    "OWWPPO",
    "OPPPPO",
    "OPIIPO",
    "OIiiwO",
    ".OOOO.",
]
EYE_SMALL = [
    ".OOO.",
    "OWWPO",
    "OWPPO",
    "OPIIO",
    "OIiwO",
    ".OOO.",
]
EYE_HUGE = [
    ".OOOOO.",
    "OWWPPPO",
    "OWWPPPO",
    "OPPPPPO",
    "OPPIIPO",
    "OPIiiwO",
    "OIiiiiO",
    ".OOOOO.",
]


def eye(L, template, x, y, iris, iris_light, outline, pupil="#16121e"):
    cols = {
        "O": rgb(outline),
        "P": rgb(pupil),
        "I": rgb(iris),
        "i": rgb(iris_light),
        "W": (255, 255, 255),
        "w": (255, 255, 255),
    }
    for dy, row in enumerate(template):
        for dx, ch in enumerate(row):
            if ch in cols:
                L.px([(x + dx, y + dy)], cols[ch])


# --- scenery ----------------------------------------------------------------

DAY_SKY = ["#b7d9f3", "#c6e1f3", "#d7e7f1", "#e9e8ea", "#f8e2d6", "#fcd8c4"]
NIGHT_SKY = ["#1f1d55", "#26246a", "#2e2c7a", "#373588", "#403e96", "#4a479f"]


def sky(L, night, stops=None):
    stops = [rgb(c) for c in (stops or (NIGHT_SKY if night else DAY_SKY))]
    band = H / len(stops)
    for y in range(H):
        f = y / band
        i = min(int(f), len(stops) - 1)
        frac = f - int(f)
        for x in range(W):
            c = stops[i]
            if i + 1 < len(stops) and frac > 0.72 and (x + y) % 2 == 0:
                c = stops[i + 1]
            L.im.putpixel((x, y), c)


def cloud(L, x, y, w, T=rgb):
    h = w * 0.45
    m = U(
        ell(x + w * 0.5, y + h * 0.65, w * 0.5, h * 0.35),
        ell(x + w * 0.33, y + h * 0.45, w * 0.22, h * 0.33),
        ell(x + w * 0.6, y + h * 0.35, w * 0.26, h * 0.38),
    )
    L.fill(m, T("#fffaf3"))
    L.fill(minus(m, shift(m, 0, -2)), T("#f3dcd6"))


def stars(L, seed, avoid=None):
    rnd = random.Random(seed)
    for _ in range(26):
        x, y = rnd.randrange(W), rnd.randrange(H - 16)
        L.px([(x, y)], rnd.choice(["#fff3c4", "#d8d4ff", "#ffe08a"]))
    for _ in range(4):
        x, y = rnd.randrange(3, W - 3), rnd.randrange(3, 40)
        L.px([(x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)], "#f5d76e")
        L.px([(x, y)], "#fffbe8")


def moon(L, x, y, r=5):
    disc = ell(x, y, r, r)
    bite = ell(x + r * 0.7, y - r * 0.4, r, r)
    m = minus(disc, bite)
    L.fill(minus(dilate(dilate(m)), m), "#5d5aac")
    L.fill(m, "#fff1b8")
    L.fill(minus(m, shift(m, 1, 1)), "#f3d27a")


def fireflies(L, pts):
    for x, y in pts:
        L.px([(x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)], "#9a9a52")
        L.px([(x, y)], "#fff27a")


# --- wonderful cat -----------------------------------------------------------


def wonderful_cat(L, night):
    T, B = tints(night)
    sky(L, night)
    if night:
        stars(L, 11)
        moon(L, 52, 11)
    else:
        cloud(L, 2, 6, 22)
        cloud(L, 42, 14, 20)

    # woodpile behind the cat: stacked log ends
    ol = B("#3b2416")
    for row, (cy, off) in enumerate([(58, 0), (66, 4.5), (74, 0)]):
        for i in range(-1, 8):
            cx = off + i * 9 + 1
            bark = ell(cx, cy, 4.6, 4.2)
            L.part(bark, B("#7d4c2c"), B("#5c3620"), outline=ol, k=1)
            face = ell(cx - 0.4, cy - 0.3, 3.4, 3.0)
            L.part(face, B("#ecc48c"), B("#d4a46a"), k=1)
            L.px([(round(cx - 1), round(cy - 1))], B("#c08a52"))
    roof = poly([(-2, 53), (66, 50), (66, 53), (-2, 56)])
    L.part(roof, B("#8c6a52"), B("#6c4e3c"), outline=ol, k=1)

    OL = T("#4a2212")
    fur, fur_hi, fur_lo, stripe = T("#f39a3e"), T("#ffc276"), T("#cc6a2c"), T("#b8521e")
    cream, cream_lo = T("#fff4e2"), T("#ecd2b6")

    # tail curling up on the right
    tail = line([(50, 80), (56, 72), (59, 64), (57, 57), (53, 55)], 4.2)
    L.part(tail, fur, fur_lo, fur_hi, outline=OL, k=1)
    for y in (62, 67, 72):
        L.px([(56, y), (57, y), (58, y)], stripe)

    body = ell(32, 79, 21, 15)
    L.part(body, fur, fur_lo, fur_hi, outline=OL, k=3)
    bib = ell(28, 76, 9, 9)
    L.part(inter(bib, body), cream, cream_lo, k=2)

    # ears behind the head
    ear_far = poly([(12, 40), (13, 21), (27, 32)])
    ear_near = poly([(33, 31), (47, 19), (51, 39)])
    for ear in (ear_far, ear_near):
        L.part(ear, fur, fur_lo, outline=OL, k=1)
    L.fill(poly([(15, 37), (15.5, 26), (23, 33)]), T("#f4a2a6"))
    L.fill(poly([(37, 32), (46, 24), (48, 37)]), T("#f4a2a6"))

    head = U(ell(31, 44, 19, 14.5), ell(16.5, 50, 6.5, 5), ell(45.5, 50, 6.5, 5))
    L.part(head, fur, fur_lo, fur_hi, outline=OL, k=2)
    # tabby marks
    for x in (27, 31, 35):
        L.px([(x, 31), (x, 32), (x, 33)], stripe)
    L.px([(26, 34), (36, 34)], stripe)
    L.px([(46, 44), (47, 44), (48, 44), (47, 47), (48, 47), (49, 47)], stripe)
    L.px([(13, 45), (14, 45), (12, 48), (13, 48)], stripe)

    muzzle = U(ell(22.5, 51.5, 5.5, 3.8), ell(29.5, 51.5, 5.5, 3.8), ell(26, 54, 5, 3))
    L.part(inter(muzzle, head), cream, cream_lo, k=1)

    eye(L, EYE_SMALL, 15, 39, T("#5cb848"), T("#a8e070"), OL)
    eye(L, EYE_HUGE, 31, 38, T("#5cb848"), T("#a8e070"), OL)
    L.px([(38, 37), (39, 36)], OL)  # lashes
    L.px([(16, 46), (31, 47), (32, 47), (36, 47)], T("#f58f8f"))  # blush

    L.px([(25, 49), (26, 49), (27, 49), (26, 50)], T("#e8728a"))  # nose
    L.px([(26, 51), (25, 52), (27, 52), (24, 51), (28, 51)], OL)  # mouth
    whisk = T("#fff8ec")
    L.px([(9, 49), (10, 49), (11, 50), (8, 53), (9, 53), (10, 52)], whisk)
    L.px([(52, 50), (53, 50), (54, 49), (53, 53), (54, 53), (55, 54)], whisk)


# --- treefrog ----------------------------------------------------------------


def treefrog(L, night):
    T, B = tints(night)
    sky(L, night)
    if night:
        stars(L, 23)
    else:
        cloud(L, 36, 4, 24)
        cloud(L, -4, 16, 18)

    # pond with lily pads and cattails
    water = rect(0, 54, W, H)
    L.fill(water, B("#8fcde6"))
    for y, x0, x1 in [(58, 4, 14), (62, 46, 58), (66, 8, 20), (70, 50, 60)]:
        L.px([(x, y) for x in range(x0, x1)], B("#c4ecf6"))
    L.fill(rect(0, 54, W, 55), B("#6aa8c6"))
    for cx, cy in [(8, 60), (56, 58)]:
        pad = ell(cx, cy, 6, 2.2)
        L.part(pad, B("#6cb85a"), B("#4a8c44"), outline=B("#2a5a34"), k=1)
    for x, top in [(4, 30), (59, 34), (62, 40)]:
        L.fill(rect(x, top, x + 1, 56), B("#4f8a3c"))
        cat = ell(x + 0.5, top + 3, 1.6, 3.5)
        L.part(cat, B("#8a5230"), B("#6a3a20"), outline=B("#3a2416"), k=1)

    OL = T("#123c22")
    g, g_hi, g_lo = T("#5fcc4c"), T("#a6ea66"), T("#2f9a3c")
    belly, belly_lo = T("#f6f2b4"), T("#dcd68c")

    leaf = poly([(-4, 82), (-2, 72), (12, 65), (32, 61), (52, 60), (68, 57), (62, 68), (46, 75), (28, 80), (14, 84)])
    L.part(leaf, T("#b8de5e"), T("#82b440"), outline=T("#3c5a20"), k=2)
    L.fill(line([(0, 79), (30, 70), (64, 60)], 1), T("#e4f29a"))
    for x0, y0 in [(10, 76), (22, 72.5), (46, 65.5), (56, 62.5)]:
        L.fill(inter(line([(x0, y0), (x0 + 6, y0 + 4)], 1), leaf), T("#9cc84c"))

    body = ell(34, 63, 19, 12)
    L.part(body, g, g_lo, g_hi, outline=OL, k=2)
    # back leg folded at the right
    leg = ell(50, 66, 7, 5.5, -20)
    L.part(leg, g, g_lo, g_hi, outline=OL, k=1)

    head = U(ell(31, 47, 21, 12.5), ell(20, 36, 7.5, 7.5), ell(42, 35, 8.5, 8.5))
    L.part(head, g, g_lo, g_hi, outline=OL, k=2)
    chin = ell(30, 60, 13, 7)
    L.part(inter(chin, U(head, body)), belly, belly_lo, k=1)

    # front arms with orange toe pads gripping the leaf
    toe, toe_lo = T("#ff9a3a"), T("#d4661e")
    for ax in (16, 41):
        arm = poly([(ax, 58), (ax + 5, 58), (ax + 4, 68), (ax + 1, 68)])
        L.part(arm, g, g_lo, outline=OL, k=1)
        for dx in (-2, 2.5, 7):
            pad = ell(ax + dx + 0.5, 69, 1.7, 1.5)
            L.part(pad, toe, toe_lo, outline=OL, k=1)

    eye(L, EYE_BIG, 16, 32, T("#e8b830"), T("#ffe070"), OL)
    eye(L, EYE_HUGE, 38, 31, T("#e8b830"), T("#ffe070"), OL)
    # smile and nostrils
    L.px([(14, 49), (15, 50), (16, 51)] + [(x, 52) for x in range(17, 36)] + [(36, 51), (37, 51), (38, 50)], OL)
    L.px([(17, 44), (21, 44)], OL)
    L.px([(14, 47), (15, 47), (41, 47), (42, 47), (43, 47)], T("#f59a8a"))
    if night:
        fireflies(L, [(10, 26), (52, 22), (28, 12), (58, 48)])


# --- rabbit ------------------------------------------------------------------


def rabbit(L, night):
    T, B = tints(night)
    sky(L, night)
    if night:
        stars(L, 37)
        moon(L, 10, 10)
    else:
        cloud(L, 40, 6, 22)
        cloud(L, 0, 22, 16)

    # garden: fence, soil, lettuces and carrot tops
    ol = B("#4a3424")
    for x in range(-2, W, 7):
        picket = poly([(x, 50), (x + 2.5, 47), (x + 5, 50), (x + 5, 64), (x, 64)])
        L.part(picket, B("#f2e2c4"), B("#d8c2a0"), outline=ol, k=1)
    L.part(rect(0, 53, W, 55), B("#e0ccaa"), outline=None)
    soil = poly([(0, 64), (W, 62), (W, H), (0, H)])
    L.part(soil, B("#9c6a46"), outline=ol)
    for y in (68, 73, 78):
        L.px([(x, y) for x in range(0, W, 2)], B("#7e5236"))
    # a ruffled lettuce: a ring of outer leaves around a pale heart
    cx, cy = 8, 71
    for ang in range(200, 560, 45):
        a = math.radians(ang)
        leaf = ell(cx + 5.5 * math.cos(a), cy + 3.5 * math.sin(a), 3.4, 3.0)
        L.part(leaf, B("#8ccc58"), B("#5e9a3c"), outline=B("#2e5a28"), k=1)
    heart = ell(cx, cy - 0.5, 3.6, 3)
    L.part(heart, B("#d4f094"), B("#a6dc6a"), outline=B("#3e7a32"), k=1)
    L.px([(cx - 1, cy - 2), (cx + 1, cy)], B("#f0fac4"))
    for cx in (52, 60):
        for dx in (-2, 0, 2):
            L.fill(line([(cx, 70), (cx + dx * 1.8, 59)], 1), B("#4e9c3e"))
            L.px([(round(cx + dx * 1.8) + d, 58) for d in (-1, 0, 1)], B("#7cc454"))
        top = ell(cx, 71.5, 3, 2)
        L.part(top, B("#f48a2e"), B("#c8601c"), outline=ol, k=1)

    OL = T("#3e2a22")
    fur, fur_hi, fur_lo = T("#b89a80"), T("#dcc6aa"), T("#8c705c")
    white, white_lo = T("#fdf8f2"), T("#e6d8cc")
    pink = T("#f4b0b6")

    body = ell(33, 80, 20, 14)
    L.part(body, fur, fur_lo, fur_hi, outline=OL, k=3)
    L.part(inter(ell(29, 78, 9, 9), body), white, white_lo, k=2)

    ear_far = ell(22, 27, 4.4, 14, -14)
    ear_near = ell(39, 24, 5.2, 15.5, 10)
    for ear, inner in ((ear_far, ell(22.5, 28, 2.0, 10, -14)), (ear_near, ell(38.8, 25, 2.6, 11.5, 10))):
        L.part(ear, fur, fur_lo, fur_hi, outline=OL, k=1)
        L.part(inner, pink, T("#e08a98"), k=1)

    head = U(ell(31, 48, 17, 13.5), ell(20, 55, 8, 6), ell(41, 55, 8, 6))
    L.part(head, fur, fur_lo, fur_hi, outline=OL, k=2)
    muzzle = U(ell(22.5, 56, 5, 3.5), ell(28.5, 56, 5, 3.5), ell(25.5, 59, 4, 3))
    L.part(inter(muzzle, head), white, white_lo, k=1)
    L.part(inter(ell(30, 37, 3, 2.5), head), fur_hi)  # forehead tuft

    eye(L, EYE_SMALL, 15, 43, T("#7a4630"), T("#b07650"), OL)
    eye(L, EYE_HUGE, 31, 42, T("#7a4630"), T("#b07650"), OL)
    L.px([(38, 41), (39, 40)], OL)  # lashes
    L.px([(16, 50), (31, 51), (32, 51), (36, 51)], T("#f59a9a"))
    L.px([(24, 53), (25, 53), (26, 53), (25, 54)], T("#ec7a92"))  # nose
    L.px([(25, 55), (24, 56), (26, 56)], OL)
    L.px([(25, 57)], white)
    whisk = T("#f8f0e4")
    L.px([(10, 54), (11, 54), (12, 55), (10, 58), (11, 57)], whisk)
    L.px([(49, 54), (50, 54), (50, 57), (51, 58)], whisk)


# --- pigeon ------------------------------------------------------------------


def pigeon(L, night):
    T, B = tints(night)
    sky(L, night)
    if night:
        stars(L, 53)
        moon(L, 10, 10)
    else:
        cloud(L, 36, 4, 24)
        cloud(L, -4, 18, 18)

    # distant pines
    for x, h in [(3, 26), (11, 18), (56, 18), (63, 28)]:
        tree = poly([(x, 74 - h), (x - 6, 76), (x + 6, 76)])
        L.part(tree, B("#5e9a6c"), B("#467c56"), k=1)

    # chimney with smoke, behind the roof
    ol = B("#3a2420")
    L.part(rect(47, 50, 54, 74), B("#b4786a"), B("#8c564c"), outline=ol, k=1)
    L.part(rect(46, 48, 55, 51), B("#8c6a5e"), outline=ol)
    for sx, sy, r in [(51, 43, 2.6), (53, 37, 3.2), (50, 30, 3.8)]:
        L.part(ell(sx, sy, r, r * 0.8), B("#f4f0f0"), B("#d6d0d8"), k=1)

    # the cabin's gable end: a peaked shake roof over a log wall
    wall = poly([(30, 68), (-6, 90), (66, 90)])
    L.fill(wall, B("#ae7a4e"))
    for y in range(71, 81, 3):
        L.fill(inter(wall, rect(0, y, W, y + 1)), B("#6e4630"))
        L.fill(inter(wall, rect(0, y + 1, W, y + 2)), B("#cc9a64"))
    roof = minus(poly([(30, 62), (-8, 86), (68, 86)]), wall)
    L.part(roof, B("#8a6c5c"), B("#6a5046"), outline=ol, k=1)
    for i in range(3, 40, 3):
        L.px([(30 - i, 63 + round(i * 0.63)), (30 + i, 63 + round(i * 0.63))], B("#5a4038"))

    OL = T("#262a40")
    grey, grey_hi, grey_lo = T("#a6b2c4"), T("#ccd4e2"), T("#76829a")
    slate, slate_hi = T("#8994b0"), T("#aab4cc")
    dark = T("#3a4058")

    tail = poly([(48, 56), (64, 59), (64, 67), (50, 65)])
    L.part(tail, T("#7c889c"), T("#5c667a"), outline=OL, k=1)
    L.fill(inter(tail, rect(59, 0, W, H)), dark)

    head_m = ell(28, 31, 11, 10.5)
    breast_m = ell(28, 55, 13, 10.5)
    body_m = ell(40, 58, 16, 9.5, -10)
    neck_m = poly([(18, 34), (38, 34), (41, 50), (16, 52)])
    sil = U(head_m, breast_m, body_m, neck_m)
    L.part(sil, grey, grey_lo, grey_hi, outline=OL, k=2)
    L.part(inter(sil, ell(26, 59, 9, 6)), T("#c6bad4"), T("#a69cba"), k=1)  # rosy breast

    # iridescent neck: a green-to-purple sheen on the neck sides, dithered at the top
    sheen = minus(inter(erode(sil), U(ell(19, 45, 5, 6), ell(37, 44, 6, 7))), head_m)
    L.fill(sheen, T("#5cc69c"))
    L.fill(inter(sheen, rect(0, 46, W, H)), T("#a274cc"))
    for x in range(14, 46):
        for y in (40, 46):
            if (x + y) % 2 == 0 and sheen.getpixel((x, y + 1)):
                L.px([(x, y)], T("#5cc69c") if y == 40 else T("#a274cc"))
    L.px([(17, 43), (35, 42), (36, 42)], T("#b4f4d4"))

    L.part(head_m, slate, None, slate_hi, j=2)
    wing = poly([(36, 50), (46, 48), (56, 54), (62, 62), (50, 64), (40, 60)])
    L.part(wing, T("#9ca8bc"), T("#6c788e"), T("#bcc6d6"), outline=T("#4c5670"), k=2)
    for x0 in (44, 50):
        L.fill(inter(line([(x0, 50), (x0 + 1, 62)], 1.6), erode(wing)), dark)
    L.px([(25, 64), (26, 65), (27, 65), (33, 65), (34, 65), (35, 64)], T("#f07a78"))  # feet

    beak = poly([(19.5, 35), (19.5, 31.5), (10, 36)])
    L.part(beak, T("#4a4658"), outline=OL)
    L.px([(17, 32), (18, 32), (19, 32), (18, 31)], T("#f6f0f4"))  # cere
    eye(L, EYE_HUGE, 21, 24, T("#f08a2e"), T("#ffc060"), OL)
    L.px([(28, 23), (29, 22)], OL)  # lashes
    L.px([(22, 33), (23, 33), (28, 33)], T("#f2a0b0"))


# --- the two portraits that already exist ------------------------------------


def from_painting(path, box):
    im = Image.open(path).convert("RGB")
    if box:
        im = im.crop(box)
    return im.resize((W, H), Image.LANCZOS)


def nuthatch(night):
    name = "nuthatch-portrait-dark.jpg" if night else "nuthatch-portrait.jpg"
    # 4:5 crop of the 1254 square; the bird runs from its tail (x 170) to its beak (x 1155)
    return from_painting(SOURCE / name, (154, 0, 1157, 1254))


def fawnicorn(night):
    name = "unicorn-portrait-dark.png" if night else "unicorn-portrait.png"
    return from_painting(SOURCE / name, None)


DRAWN = {
    "wonderful-cat": wonderful_cat,
    "treefrog": treefrog,
    "rabbit": rabbit,
    "pigeon": pigeon,
}
PAINTED = {"nuthatch": nuthatch, "fawnicorn": fawnicorn}


def portrait(slug, night):
    if slug in PAINTED:
        im = PAINTED[slug](night)
    else:
        layer = Layer()
        DRAWN[slug](layer, night)
        im = layer.im
    return im.quantize(colors=COLORS, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE, kmeans=8)


def contact_sheet(images, path, scale=4, gap=6):
    cols = len(SLUGS)
    sheet = Image.new("RGB", (cols * (W * scale + gap) + gap, 2 * (H * scale + gap) + gap), (40, 40, 48))
    for (slug, night), im in images.items():
        x = gap + SLUGS.index(slug) * (W * scale + gap)
        y = gap + int(night) * (H * scale + gap)
        sheet.paste(im.convert("RGB").resize((W * scale, H * scale), Image.NEAREST), (x, y))
    sheet.save(path)


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sheet", type=Path, help="also write a 4x contact sheet here")
    args = parser.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    images = {}
    for slug in SLUGS:
        for night in (False, True):
            supplied = OUT / f"{slug}.jpg"
            if supplied.exists():
                with Image.open(supplied) as source:
                    im = source.convert("RGB").resize((W, H), Image.Resampling.LANCZOS)
            else:
                im = portrait(slug, night)
                im.save(OUT / f"{slug}-{'night' if night else 'day'}.png", optimize=True)
            images[slug, night] = im
    if args.sheet:
        contact_sheet(images, args.sheet)
    print(f"wrote {len(images)} portraits to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
