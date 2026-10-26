"""Full bowl: at 7 AM the cat screams at its food bowl. She shuffles in half asleep: "It's
FULL." The cat stares, looks down at the bowl, looks back up: "MEOW." Close-up from above:
the bowl IS full, except one tiny spot where the bottom shows. She sighs and nudges the bowl
with her foot; the food slides over the spot. The cat eats ONE bite... the spot is back.
"MEOW." She gives up and adds food: the bowl overflows, the cat eats, purring, and she
smiles.

Both characters are drawn in code every frame (lib/girl3.py, lib/cat3.py); the kitchen,
the bowl and the food too. Premise: the genre's "cat says the bowl is empty" moment, our own
characters, staging, close-up gag and loop ending.

Usage:
  python scenes/full_bowl.py stills            -> output/full_bowl_stills.png
  python scenes/full_bowl.py video [out.mp4]   -> silent 1080x1920 30 fps render
"""
import math
import os
import random
import subprocess
import sys

import cairo
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'lib'))
import cat3  # noqa: E402
import girl3  # noqa: E402

W, H, FPS = 1080, 1920, 30
DUR = 21.6
INK = (43 / 255, 31 / 255, 30 / 255)
FLOOR_Y = 1330

CAT_X, CAT_Y, CAT_S = 770, 1650, 0.62
BOWL = (770.0, 1752.0)                 # centre of the bowl's rim (side view)
GIRL_Y, GIRL_S = 1800, 0.95
GIRL_X0, GIRL_STOP = -150, 540

# ------------------------------------------------------------------ timeline (s)
MEOWS = [(0.15, 0.55, 'MEOW!'), (0.95, 0.65, 'MEOOW!'), (1.8, 0.6, 'MEOW!!'),
         (8.3, 0.7, 'MEOW.'), (15.6, 0.75, 'MEOW.')]
T_WALK = 2.0
T_LOOK = 4.7                           # she looks down at the bowl
SAY = (5.15, 6.6)                      # "It's FULL."
T_CAT_DOWN, T_CAT_UP = 7.55, 8.05
CLOSE1 = (9.2, 11.4)                   # top view: the spot
T_SIGH = 11.5
TAP = (11.95, 12.55)                   # foot nudges the bowl; the hit at TAP_HIT
TAP_HIT = 12.2
CLOSE2 = (12.75, 13.55)                # top view: the food slides over the spot
EAT = (13.85, 14.55)                   # one bite
CLOSE3 = (14.7, 15.4)                  # top view: the spot is back
SIGH2 = (16.4, 17.0)                   # she gives up
REACH = (17.0, 17.5)                   # her hand goes up to the food bag on the counter
LIFT = (17.5, 18.0)                    # she takes it and brings it over the bowl
POUR = (18.0, 19.25)                   # she tips it: food streams in, the bowl overflows
PUT = (19.25, 19.65)                   # the bag comes back upright, her arm comes down
T_FEAST = 19.5                         # the cat eats, purring; she smiles
BAG_ON_COUNTER = (830.0, 958.0)        # bottom centre of the bag on the counter (screen)


def ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def ease_out(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def pulse(t, a, b):
    """0 -> 1 -> 0 over [a, b]."""
    if not a <= t <= b:
        return 0.0
    return math.sin(math.pi * (t - a) / (b - a))


def meow_at(t):
    for i, (a, d, w) in enumerate(MEOWS):
        if a - 0.12 <= t < a + d:
            return i, (t - a) / d, w
    return None


# ------------------------------------------------------------------ the kitchen

def _box(ctx, x0, y0, x1, y1, fill, lw=7, r=0):
    if r:
        ctx.new_sub_path()
        ctx.arc(x1 - r, y0 + r, r, -math.pi / 2, 0)
        ctx.arc(x1 - r, y1 - r, r, 0, math.pi / 2)
        ctx.arc(x0 + r, y1 - r, r, math.pi / 2, math.pi)
        ctx.arc(x0 + r, y0 + r, r, math.pi, 3 * math.pi / 2)
        ctx.close_path()
    else:
        ctx.rectangle(x0, y0, x1 - x0, y1 - y0)
    ctx.set_source_rgb(*fill)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(lw)
    ctx.stroke()


def kitchen(ctx, t):
    ctx.set_source_rgb(0.95, 0.91, 0.84)
    ctx.paint()
    # wall stripes
    ctx.set_source_rgb(0.93, 0.88, 0.80)
    for x in range(0, W, 120):
        ctx.rectangle(x, 0, 60, FLOOR_Y)
    ctx.fill()
    # window with morning light
    _box(ctx, 90, 330, 470, 830, (1.0, 0.93, 0.74), 8, 12)
    g = cairo.LinearGradient(0, 330, 0, 830)
    g.add_color_stop_rgb(0, 0.99, 0.80, 0.55)
    g.add_color_stop_rgb(1, 0.70, 0.86, 0.95)
    ctx.rectangle(98, 338, 364, 484)
    ctx.set_source(g)
    ctx.fill()
    ctx.arc(330, 640, 70, 0, 2 * math.pi)                    # the rising sun
    ctx.set_source_rgb(1.0, 0.86, 0.45)
    ctx.fill()
    _box(ctx, 270, 330, 290, 830, (0.97, 0.94, 0.88), 6)
    _box(ctx, 90, 570, 470, 590, (0.97, 0.94, 0.88), 6)
    _box(ctx, 60, 830, 500, 862, (0.87, 0.77, 0.63), 7)
    # the wall clock: 7:00
    cx, cy = 650, 470
    ctx.arc(cx, cy, 92, 0, 2 * math.pi)
    ctx.set_source_rgb(1, 1, 1)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(9)
    ctx.stroke()
    for k in range(12):
        a = k * math.pi / 6
        ctx.move_to(cx + 72 * math.sin(a), cy - 72 * math.cos(a))
        ctx.line_to(cx + 80 * math.sin(a), cy - 80 * math.cos(a))
    ctx.set_line_width(5)
    ctx.stroke()
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    mins = (t / 60.0) * 360 * 4                               # the minute hand creeps
    for ang, L, w in ((210, 44, 10), (mins, 66, 7)):
        a = math.radians(ang)
        ctx.move_to(cx, cy)
        ctx.line_to(cx + L * math.sin(a), cy - L * math.cos(a))
        ctx.set_line_width(w)
        ctx.stroke()
    # cabinets with the counter
    _box(ctx, 600, 960, 1110, 1000, (0.93, 0.87, 0.78), 7)
    _box(ctx, 610, 1000, 1100, FLOOR_Y, (0.62, 0.79, 0.74), 7)
    for x0 in (610, 855):
        _box(ctx, x0 + 22, 1025, x0 + 223, FLOOR_Y - 30, (0.66, 0.83, 0.78), 5, 8)
        _box(ctx, x0 + 190 if x0 == 610 else x0 + 36, 1120, x0 + 202 if x0 == 610 else x0 + 48, 1200,
             (0.95, 0.86, 0.50), 4, 5)
    if t < LIFT[0]:
        bag_shape(ctx, BAG_ON_COUNTER[0] - BAG_W * GIRL_S / 2, BAG_ON_COUNTER[1] - BAG_H * GIRL_S, GIRL_S)
    # a plant on the counter
    _box(ctx, 960, 870, 1040, 962, (0.86, 0.45, 0.32), 6, 6)
    for a, L in ((-40, 110), (-10, 130), (20, 120), (50, 95)):
        r = math.radians(a)
        ctx.save()
        ctx.translate(1000, 875)
        ctx.rotate(r)
        ctx.scale(0.32, 1)
        ctx.arc(0, -L / 2, L / 2, 0, 2 * math.pi)
        ctx.restore()
        ctx.set_source_rgb(0.42, 0.66, 0.38)
        ctx.fill_preserve()
        ctx.set_source_rgb(*INK)
        ctx.set_line_width(5)
        ctx.stroke()
    # floor: tiles
    ctx.rectangle(0, FLOOR_Y, W, H - FLOOR_Y)
    ctx.set_source_rgb(0.88, 0.80, 0.69)
    ctx.fill()
    ctx.set_source_rgb(0.82, 0.72, 0.60)
    rows = [FLOOR_Y, 1410, 1510, 1630, 1770, 1920]
    for i in range(len(rows) - 1):
        y0, y1 = rows[i], rows[i + 1]
        w = 150 + 40 * i
        off = (i % 2) * w / 2
        for k in range(-1, 12):
            x = k * w + off - 60
            if (k + i) % 2 == 0:
                ctx.rectangle(x, y0, w, y1 - y0)
        ctx.fill()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(7)
    ctx.move_to(0, FLOOR_Y)
    ctx.line_to(W, FLOOR_Y)
    ctx.stroke()


def shadow(ctx, x, y, rx, ry, a=0.16):
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(rx, ry)
    ctx.arc(0, 0, 1, 0, 2 * math.pi)
    ctx.restore()
    ctx.set_source_rgba(0.25, 0.15, 0.1, a)
    ctx.fill()


# ------------------------------------------------------------------ the bowl (side view)

BOWL_COL = (0.36, 0.62, 0.86)
KIBBLE = (0.66, 0.42, 0.22)
KIBBLE_DK = (0.50, 0.30, 0.15)


def bowl_side(ctx, t):
    x, y = BOWL
    # the nudge: a quick jolt to the right, a wobble
    d = t - TAP_HIT
    dx = 0.0
    rot = 0.0
    if d >= 0:
        dx = 22 * ease_out(d / 0.12) if d < 0.12 else 22
        rot = 6 * math.exp(-d * 7) * math.sin(d * 34)
    ctx.save()
    ctx.translate(x + dx, y)
    ctx.rotate(math.radians(rot))
    shadow(ctx, 0, 50, 120, 16, 0.22)
    rx, ry = 104, 26
    # kibble mound peeking over the rim
    rnd = random.Random(3)
    lvl = pour_level(t)
    heap = lvl > 0.85
    if heap:                                          # spilled pieces round the bowl
        for k in range(9):
            kx = rnd.choice([-1, 1]) * rnd.uniform(rx * 1.05, rx * 1.6)
            ky = rnd.uniform(30, 62)
            ctx.save()
            ctx.translate(kx, ky)
            ctx.rotate(rnd.uniform(0, 3))
            ctx.scale(1.0, 0.7)
            ctx.arc(0, 0, 11, 0, 2 * math.pi)
            ctx.restore()
            ctx.set_source_rgb(*KIBBLE)
            ctx.fill_preserve()
            ctx.set_source_rgb(*INK)
            ctx.set_line_width(3)
            ctx.stroke()
    for k in range(int(17 + 29 * lvl)):
        kx = rnd.uniform(-rx * 0.85, rx * 0.85)
        ky = -6 - rnd.uniform(0, 14 + 34 * lvl) * (1 - (kx / rx) ** 2)
        ctx.save()
        ctx.translate(kx, ky)
        ctx.rotate(rnd.uniform(0, 3))
        ctx.scale(1.0, 0.7)
        ctx.arc(0, 0, 11, 0, 2 * math.pi)
        ctx.restore()
        ctx.set_source_rgb(*(KIBBLE if k % 3 else KIBBLE_DK))
        ctx.fill_preserve()
        ctx.set_source_rgb(*INK)
        ctx.set_line_width(3)
        ctx.stroke()
    # bowl body
    ctx.move_to(-rx, 0)
    ctx.curve_to(-rx, 30, -rx * 0.8, 52, -rx * 0.72, 54)
    ctx.line_to(rx * 0.72, 54)
    ctx.curve_to(rx * 0.8, 52, rx, 30, rx, 0)
    ctx.save()
    ctx.scale(1, ry / rx)
    ctx.arc(0, 0, rx, 0, math.pi)
    ctx.restore()
    ctx.close_path()
    ctx.set_source_rgb(*BOWL_COL)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(6)
    ctx.stroke()
    # rim front lip + a shine + a little paw print
    ctx.save()
    ctx.scale(1, ry / rx)
    ctx.arc(0, 0, rx, 0, math.pi)
    ctx.restore()
    ctx.set_line_width(6)
    ctx.stroke()
    ctx.move_to(-rx * 0.62, 18)
    ctx.curve_to(-rx * 0.6, 34, -rx * 0.5, 42, -rx * 0.42, 44)
    ctx.set_source_rgba(1, 1, 1, 0.6)
    ctx.set_line_width(7)
    ctx.stroke()
    for (px, py, r) in ((14, 30, 9), (2, 18, 4), (12, 15, 4), (24, 17, 4), (32, 25, 4)):
        ctx.arc(px, py, r, 0, 2 * math.pi)
        ctx.set_source_rgb(0.96, 0.96, 1.0)
        ctx.fill()
    ctx.restore()


# ------------------------------------------------------------------ the bowl (top view)

def _kibble_layout(seed, hole, n=560):
    """Kibble positions in the bowl (unit disc), leaving a bare spot at `hole` (x, y, r)."""
    rnd = random.Random(seed)
    out = []
    while len(out) < n:
        a = rnd.uniform(0, 2 * math.pi)
        r = math.sqrt(rnd.uniform(0, 1)) * 0.95
        x, y = r * math.cos(a), r * math.sin(a)
        if hole and math.hypot(x - hole[0], y - hole[1]) < hole[2] + 0.055:   # + a piece's radius
            continue
        out.append((x, y, rnd.uniform(0, 3.1), rnd.random() < 0.3))
    return out


SPOT = (0.06, -0.05, 0.075)
BITE = (-0.12, 0.10, 0.07)
LAYOUT_SPOT = _kibble_layout(5, SPOT)


def _fill_in():
    """The nudge: pieces round the spot slide into it (same list order, so they animate)."""
    rnd = random.Random(9)
    start, end = [], []
    for (x, y, r, d) in LAYOUT_SPOT:
        start.append((x, y, r, d))
        end.append((x + rnd.uniform(-0.01, 0.01), y + rnd.uniform(-0.01, 0.01), r + rnd.uniform(-0.3, 0.3), d))
    hx, hy, hr = SPOT
    for k in range(9):
        a = k / 9 * 2 * math.pi
        sx, sy = hx + (hr + 0.05) * math.cos(a), hy + (hr + 0.05) * math.sin(a)
        ex, ey = hx + hr * 0.55 * math.cos(a + 0.4) * (k % 3) / 2, hy + hr * 0.55 * math.sin(a + 0.4) * (k % 3) / 2
        start.append((sx, sy, a, k % 4 == 0))
        end.append((ex, ey, a + 1.2, k % 4 == 0))
    return start, end


LAYOUT_SLIDE_A, LAYOUT_FULL = _fill_in()
LAYOUT_BITE = [p for p in LAYOUT_FULL if math.hypot(p[0] - BITE[0], p[1] - BITE[1]) >= BITE[2] + 0.055]


def bowl_top(ctx, t, layout, push=0.0, label=None, label_p=0.0, spot=None, extra=()):
    """Full-frame view from above. layout: list or (from, to, k) to slide between."""
    ctx.set_source_rgb(0.88, 0.80, 0.69)
    ctx.paint()
    ctx.set_source_rgb(0.82, 0.72, 0.60)
    for i in range(-1, 6):
        for j in range(-1, 9):
            if (i + j) % 2 == 0:
                ctx.rectangle(i * 260 - 40, j * 260 - 60, 260, 260)
    ctx.fill()
    cx, cy, R = 540, 1000, 500
    Rb = R * 0.82
    z = 1 + 1.4 * push
    sx_, sy_ = (spot[0] * Rb * 0.95, spot[1] * Rb * 0.95) if spot else (0.0, 0.0)
    ctx.save()
    ctx.translate(cx, cy)
    ctx.scale(z, z)
    ctx.translate(-sx_ * push, -sy_ * push)
    ctx.arc(16, 24, R, 0, 2 * math.pi)
    ctx.set_source_rgba(0.25, 0.15, 0.1, 0.2)
    ctx.fill()
    ctx.arc(0, 0, R, 0, 2 * math.pi)
    ctx.set_source_rgb(*BOWL_COL)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(9)
    ctx.stroke()
    ctx.arc(0, 0, Rb, 0, 2 * math.pi)
    ctx.set_source_rgb(0.74, 0.86, 0.95)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(6)
    ctx.stroke()
    ctx.arc(0, 0, Rb, 0, 2 * math.pi)
    ctx.clip()
    if isinstance(layout, tuple):
        a, b, k = layout
        pts = [(x0 + (x1 - x0) * k, y0 + (y1 - y0) * k, r0 + (r1 - r0) * k, d0)
               for (x0, y0, r0, d0), (x1, y1, r1, d1) in zip(a, b)]
    else:
        pts = layout
    for (x, y, r, dk) in pts:
        px, py = x * Rb * 0.95, y * Rb * 0.95
        ctx.save()
        ctx.translate(px, py)
        ctx.rotate(r)
        ctx.scale(1.0, 0.78)
        ctx.arc(0, 0, 24, 0, 2 * math.pi)
        ctx.restore()
        ctx.set_source_rgb(*(KIBBLE_DK if dk else KIBBLE))
        ctx.fill_preserve()
        ctx.set_source_rgb(*INK)
        ctx.set_line_width(3.5)
        ctx.stroke()
        ctx.arc(px - 6, py - 7, 5.5, 0, 2 * math.pi)
        ctx.set_source_rgba(1, 0.9, 0.7, 0.45)
        ctx.fill()
    ctx.reset_clip()
    for (x, y, r, dk, k) in extra:                    # poured on top: a heap, spilling over the rim
        px, py = x * Rb * 0.95, y * Rb * 0.95
        ctx.save()
        ctx.translate(px, py)
        ctx.rotate(r)
        ctx.scale(k, 0.78 * k)
        ctx.arc(0, 0, 24, 0, 2 * math.pi)
        ctx.restore()
        ctx.set_source_rgb(*(KIBBLE_DK if dk else KIBBLE))
        ctx.fill_preserve()
        ctx.set_source_rgb(*INK)
        ctx.set_line_width(3.5)
        ctx.stroke()
        ctx.arc(px - 6 * k, py - 7 * k, 5.5 * k, 0, 2 * math.pi)
        ctx.set_source_rgba(1, 0.9, 0.7, 0.45)
        ctx.fill()
    ctx.restore()
    if label and label_p > 0:
        # where the spot is on screen
        tx = cx + z * (sx_ - sx_ * push)
        ty = cy + z * (sy_ - sy_ * push)
        k = ease(label_p * 2)
        ax, ay = 300, 470
        ex, ey = ax + (tx - 95 - ax) * k, ay + (ty - 95 - ay) * k
        ctx.set_source_rgb(0.86, 0.12, 0.12)
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.set_line_width(16)
        ctx.move_to(ax, ay)
        ctx.curve_to(ax - 40, ay + 200, ex - 160, ey - 40, ex, ey)
        ctx.stroke()
        if k > 0.95:
            ang = math.atan2(40, 160)
            for sgn in (-1, 1):
                a = ang + math.pi + sgn * 0.5
                ctx.move_to(ex, ey)
                ctx.line_to(ex + 55 * math.cos(a), ey + 55 * math.sin(a))
            ctx.stroke()
            ctx.arc(tx, ty, (spot_r(spot) * Rb * 0.95 + 40) * z, 0, 2 * math.pi)
            ctx.set_line_width(11)
            ctx.stroke()
        caption(ctx, label, W / 2, 330, size=74, pop=min(1, label_p * 3), tilt=-3)


def spot_r(spot):
    return SPOT[2] if spot and abs(spot[0] - SPOT[0]) < 1e-6 else BITE[2]


# ------------------------------------------------------------------ the food bag

BAG_W, BAG_H = 96.0, 128.0             # src px (she holds it, so it scales with her)
BAG_GRIP = (14.0, 16.0)                # where her fingers hold it, from the bag's top-left
_bag_mouth = {}                        # screen point of the bag's open top, set while drawing


def bag_shape(ctx, x0, y0, k=1.0):
    """The kraft-paper bag with a paw-print label; top-left at (x0, y0), scale k."""
    ctx.save()
    ctx.translate(x0, y0)
    ctx.scale(k, k)
    _box(ctx, 0, 0, BAG_W, BAG_H, (0.84, 0.66, 0.44), 4, 8)
    _box(ctx, 0, 0, BAG_W, 18, (0.74, 0.55, 0.34), 4, 0)          # the rolled-open top
    ctx.arc(BAG_W / 2, 74, 26, 0, 2 * math.pi)
    ctx.set_source_rgb(0.98, 0.95, 0.88)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(3)
    ctx.stroke()
    for (px, py, r) in ((0, 80, 9), (-12, 64, 4.5), (-4, 58, 4.5), (5, 58, 4.5), (13, 64, 4.5)):
        ctx.arc(BAG_W / 2 + px, py, r, 0, 2 * math.pi)
        ctx.set_source_rgb(0.86, 0.30, 0.30)
        ctx.fill()
    ctx.restore()


def bag_prop(tilt):
    """Her hand's prop: the bag hanging from her grip, tipped by `tilt` degrees (+ = mouth
    toward +x, the bowl)."""
    def draw(ctx, Wr, ha):
        ctx.save()
        ctx.translate(Wr[0], Wr[1] + 30)
        ctx.rotate(math.radians(tilt))
        bag_shape(ctx, -BAG_GRIP[0], -BAG_GRIP[1])
        _bag_mouth['xy'] = ctx.user_to_device(BAG_W * 0.55, 2)
        ctx.restore()
    return draw


def pour_level(t):
    """0 = the bowl after one bite, 1 = heaped and spilling."""
    return ease((t - POUR[0] - 0.2) / (POUR[1] - POUR[0] - 0.2))


def stream(ctx, t):
    """Kibble falling from the bag's mouth into the bowl while she pours."""
    if not (POUR[0] + 0.12 <= t < POUR[1] - 0.05) or 'xy' not in _bag_mouth:
        return
    mx, my = _bag_mouth['xy']
    bx, by = BOWL[0] + 22, BOWL[1] - 18 - 30 * pour_level(t)
    rnd = random.Random(4)
    for i in range(22):
        ph = (t * 2.6 + i / 22) % 1.0
        jx = rnd.uniform(-16, 16)
        px = mx + (bx + jx - mx) * ph
        py = my + (by - my) * ph * ph
        ctx.save()
        ctx.translate(px, py)
        ctx.rotate(ph * 6 + i)
        ctx.scale(1.0, 0.7)
        ctx.arc(0, 0, 10, 0, 2 * math.pi)
        ctx.restore()
        ctx.set_source_rgb(*(KIBBLE if i % 3 else KIBBLE_DK))
        ctx.fill_preserve()
        ctx.set_source_rgb(*INK)
        ctx.set_line_width(2.5)
        ctx.stroke()


# ------------------------------------------------------------------ text

def _text_path(ctx, text, size, font='Segoe UI Black'):
    ctx.select_font_face(font, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(size)
    e = ctx.text_extents(text)
    return e


def caption(ctx, text, x, y, size=76, pop=1.0, tilt=-2.0):
    """The setup caption: a taped paper strip."""
    if pop <= 0:
        return
    s = 0.4 + 0.6 * ease_out(pop) + 0.08 * math.sin(min(1, pop) * math.pi)
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(math.radians(tilt))
    ctx.scale(s, s)
    ctx.select_font_face('Segoe Print', cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(size)
    e = ctx.text_extents(text)
    w, h = e.x_advance + 80, size * 1.75
    ctx.rectangle(-w / 2 + 8, -h / 2 + 10, w, h)
    ctx.set_source_rgba(0, 0, 0, 0.28)
    ctx.fill()
    ctx.rectangle(-w / 2, -h / 2, w, h)
    ctx.set_source_rgb(1, 1, 1)
    ctx.fill()
    ctx.move_to(-e.x_advance / 2, size * 0.36)
    ctx.set_source_rgb(*INK)
    ctx.show_text(text)
    for sx in (-1, 1):
        ctx.save()
        ctx.translate(sx * (w / 2 - 34), -h / 2)
        ctx.rotate(sx * 0.5)
        ctx.rectangle(-44, -15, 88, 30)
        ctx.set_source_rgba(0.96, 0.83, 0.15, 0.8)
        ctx.fill()
        ctx.restore()
    ctx.restore()


def shout(ctx, text, x, y, size, p, rot=-0.1):
    """A sound word that pops (white with an ink edge)."""
    if p <= 0:
        return
    s = 0.4 + 0.75 * min(1, p / 0.18) if p < 0.18 else 1 + 0.08 * math.exp(-(p - 0.18) * 10) * math.cos((p - 0.18) * 30)
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(rot)
    ctx.scale(s, s)
    e = _text_path(ctx, text, size)
    ctx.move_to(-e.x_advance / 2, e.height / 2)
    ctx.text_path(text)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.set_line_width(size * 0.17)
    ctx.set_source_rgb(*INK)
    ctx.stroke_preserve()
    ctx.set_source_rgb(1, 1, 1)
    ctx.fill()
    ctx.restore()


def bubble(ctx, lines, x, y, tail, p, shake=0.0):
    """Speech bubble with its tail toward `tail`."""
    if p <= 0:
        return
    s = 0.5 + 0.5 * ease_out(min(1, p * 4)) + 0.06 * math.sin(min(1, p * 4) * math.pi)
    ctx.save()
    ctx.translate(x + shake, y)
    ctx.scale(s, s)
    sizes = [l[1] for l in lines]
    widths = []
    for text, size in lines:
        e = _text_path(ctx, text, size)
        widths.append(e.x_advance)
    bw = max(widths) + 110
    bh = sum(sizes) * 1.15 + 70
    tx, ty = (tail[0] - x) / s, (tail[1] - y) / s
    ctx.new_path()
    ctx.save()
    ctx.scale(bw / 2, bh / 2)
    ctx.arc(0, 0, 1, 0, 2 * math.pi)
    ctx.restore()
    ctx.move_to(-34, bh / 2 - 14)
    ctx.line_to(tx, ty)
    ctx.line_to(30, bh / 2 - 20)
    ctx.close_path()
    ctx.set_line_width(9)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.set_source_rgb(*INK)
    ctx.stroke_preserve()
    ctx.set_source_rgb(1, 1, 1)
    ctx.fill()
    yy = -bh / 2 + 35
    for (text, size), wdt in zip(lines, widths):
        _text_path(ctx, text, size)
        yy += size * 1.0
        ctx.move_to(-wdt / 2, yy)
        ctx.set_source_rgb(*INK)
        ctx.show_text(text)
        yy += size * 0.15
    ctx.restore()


# ------------------------------------------------------------------ the cat

def cat_state(t):
    mood, mouth, crouch, roll, yaw = 'deadpan', 1.0, 0.0, 1.5 * math.sin(t * 1.1), 0.0
    look, nod, head_dy = [0.0, 0.0], 0.0, 0.0
    blink = 0.0
    for b, d in ((3.3, 0.18), (7.0, 0.55), (10.0, 0.18), (16.5, 0.5)):      # 7.0 = a slow stare-blink
        if b <= t < b + d:
            blink = math.sin((t - b) / d * math.pi) ** 0.7
    ear_l = ear_r = 0.0
    # 0-2: screaming at the bowl, head up toward the door she will come from
    yaw = -0.35
    # 2.0: hears her: an ear flicks, head turns toward her
    if 2.2 < t < 2.6:
        ear_l = -16 * math.sin((t - 2.2) / 0.4 * 2 * math.pi) * (1 - (t - 2.2) / 0.4)
    yaw = -0.35 - 0.45 * ease((t - 2.4) / 0.4) + 0.2 * ease((t - 4.6) / 0.4)
    look = [-0.6 * ease((t - 2.4) / 0.4), -0.5 * ease((t - 4.5) / 0.4)]
    # 7.55-8.05: looks down at the bowl and back up at her
    dn = ease((t - T_CAT_DOWN) / 0.18) * (1 - ease((t - T_CAT_UP) / 0.18))
    nod += 0.9 * dn
    look[1] += 1.5 * dn
    look[0] += 0.6 * dn
    # the nudge: the bowl moves -> ears up, eyes on it
    if TAP_HIT <= t < EAT[0]:
        mood = 'surprised' if t < TAP_HIT + 0.5 else 'smug'
        look = [0.2, 0.9]
        nod += 0.5
    # one bite
    e = pulse(t, *EAT)
    if e:
        mood = 'smug'
        head_dy += 250 * min(1.0, e * 1.6)
        nod += 1.0 * min(1.0, e * 1.6)
        crouch += 0.16 * e
        look = [0.0, 1.0]
        if 0.35 < (t - EAT[0]) / (EAT[1] - EAT[0]) < 0.65:
            mouth = 0.3
    if t >= EAT[1]:
        mood = 'deadpan'
        look = [-0.5, -0.4]
        yaw = -0.25
    if REACH[0] <= t < T_FEAST:                       # eyes on the bag, then on the food
        mood = 'surprised' if t < POUR[0] + 0.3 else 'smug'
        up = ease((t - REACH[0]) / 0.3) * (1 - ease((t - POUR[0]) / 0.4))
        look = [-0.2 + 0.4 * up, -1.0 * up + 0.8 * ease((t - POUR[0]) / 0.4)]
        nod = -0.6 * up + 0.4 * ease((t - POUR[0]) / 0.4)
        yaw = -0.2
    if t >= T_FEAST:                                  # the feast: head in the bowl, chewing
        f = t - T_FEAST
        if f < 1.3:
            dip = ease(f / 0.2)
            mood = 'smug'
            head_dy = 250 * dip + 18 * math.sin(f * 2 * math.pi * 3.2) * dip
            nod = 1.0 * dip
            crouch = 0.16 * dip
            look = [0.0, 1.0]
            yaw = 0.0
        else:                                         # looks up, eyes shut, purring
            up = ease((f - 1.3) / 0.25)
            mood = 'content'
            head_dy = 250 * (1 - up)
            nod = 1.0 * (1 - up)
            crouch = 0.16 * (1 - up)
            yaw = -0.3 * up
            roll += 6 * up
    m = meow_at(t)
    if m:
        i, u, _ = m
        if u < 0:                                     # anticipation: a little crouch
            crouch += 0.18 * ease((u * MEOWS[i][1] + 0.12) / 0.12)
        else:
            mood = 'meow'
            mouth = math.sin(min(1, u) * math.pi) ** 0.55
            crouch += 0.18 * (1 - ease(u * 3))
            roll += -7 * math.sin(min(1, u) * math.pi)
            if i < 3:
                yaw = -0.15
    breathe = math.sin(t * 2 * math.pi / 2.4)
    return dict(mood=mood, blink=blink, look=tuple(look), head_roll=roll, head_yaw=yaw, head_nod=nod,
                head_dy=head_dy, breathe=breathe, crouch=crouch, ear_l=ear_l, ear_r=ear_r, mouth_open=mouth)


# ------------------------------------------------------------------ the girl

WALKER = girl3.Walker(GIRL_X0 / GIRL_S, [(T_WALK, GIRL_STOP / GIRL_S)], speed=300.0, stride=150.0)


def girl_state(t):
    x = WALKER.x(t) * GIRL_S
    pose = WALKER.pose(t) if t >= T_WALK else girl3.walk_pose(0, 0)
    mv = WALKER.moving(t)
    expr, blink, look, talk = 'bored', 0.0, (0.0, 0.0), 0.0
    head, nod, turn = 0.0, 0.0, 0.0
    for b, d in ((3.0, 0.22), (6.9, 0.2), (9.0, 0.2), (14.2, 0.25), (20.2, 0.22)):
        if b <= t < b + d:
            blink = math.sin((t - b) / d * math.pi)
    # half asleep on the walk in: head droops, a yawn-sway
    head += 3 * math.sin(t * 1.3) + 2 * mv
    # 4.7: looks down at the bowl / the cat
    k = ease((t - T_LOOK) / 0.35)
    head += 6 * k
    nod += 0.9 * k
    look = (0.7 * k, 0.8 * k)
    # "It's FULL."
    if SAY[0] - 0.2 <= t < SAY[1] + 0.6:
        expr = 'annoyed'
    if SAY[0] <= t < SAY[0] + 0.9:
        talk = abs(math.sin((t - SAY[0]) * math.pi * 4.4))
        head += 2.5 * math.sin((t - SAY[0]) * 9)
    # the cat's MEOW: a flinch
    if 8.3 <= t < 9.2:
        expr = 'surprised'
        head -= 4 * ease((t - 8.3) / 0.1)
        nod -= 0.5
    # back from the close-up: a big sigh (eyes shut, head drops), then the nudge
    if T_SIGH <= t < TAP[0]:
        expr = 'sleep'
        nod += 0.6 * pulse(t, T_SIGH, TAP[0])
        head += 4 * pulse(t, T_SIGH, TAP[0])
    if TAP[0] <= t < EAT[1]:
        expr = 'annoyed' if t < TAP_HIT + 0.3 else 'bored'
    if t >= EAT[1]:
        expr = 'bored'
    if t >= 15.6:
        expr = 'bored'
        head += 3 * ease((t - 15.9) / 0.4)
    if SIGH2[0] <= t < SIGH2[1] + 0.3:
        expr = 'sleep'
        nod += 0.7 * pulse(t, SIGH2[0], SIGH2[1] + 0.3)
    if REACH[0] + 0.1 <= t < T_FEAST:                  # looks up at the bag, then down to pour
        expr = 'bored'
        upk = ease((t - REACH[0] - 0.1) / 0.3) * (1 - ease((t - LIFT[0]) / 0.4))
        nod -= 0.9 * upk
        head -= 5 * upk
        look = (0.9 * upk + 0.7 * (1 - upk), -0.7 * upk + 0.8 * (1 - upk))
    if t >= T_FEAST:
        expr = 'bored' if t < T_FEAST + 0.5 else 'smile'
        head += 2 * ease((t - T_FEAST - 0.5) / 0.4)
    # the foot tap
    tp = (t - TAP[0]) / (TAP[1] - TAP[0])
    if 0 <= tp <= 1:
        # lift back, swing forward to the bowl, tap, return
        if tp < 0.35:
            fx, fy = -30 * ease(tp / 0.35), -40 * ease(tp / 0.35)
        elif tp < 0.42:
            q = (tp - 0.35) / 0.07
            fx, fy = -30 + 165 * q, -40 + 30 * q
        elif tp < 0.6:
            fx, fy = 135, -10
        else:
            q = ease((tp - 0.6) / 0.4)
            fx, fy = 135 * (1 - q), -10 * (1 - q) - 25 * math.sin(q * math.pi)
        pose = girl3.foot_pose((fx, fy, 6 if 0.35 < tp < 0.6 else 0))
    breathe = math.sin(t * 2 * math.pi / 3.2)
    # hair: lags behind the walk, swings when she stops, bounces at the tap
    ph = 2 * math.pi * float(WALKER.ph[WALKER._i(t)])
    hl = -2.5 * mv + 2.5 * math.sin(ph * 2 - 0.9) * mv
    stop = 3.9 + 0.4
    if t > stop:
        d = t - stop
        hl += 4 * math.exp(-d * 2.4) * math.sin(d * 6.5)
    pose = dict(pose)
    pose['head'] = dict(rot=head + 1.2 * math.sin(ph * 2) * mv)
    pose['chest'] = dict(rot=1.0 * math.sin(ph * 2) * mv, sy=1 + 0.006 * breathe)
    pose['lockL'] = dict(rot=hl)
    pose['lockR'] = dict(rot=hl * 0.8)
    pose['lockF'] = dict(rot=hl * 0.9)
    pose['turn'] = turn
    pose['nod'] = nod
    return x, pose, expr, blink, look, talk


def girl_arms(t):
    """None (hands behind her back, as on the sheet) or the far arm reaching / pouring."""
    if t < REACH[0]:
        return None
    s = GIRL_S
    to_src = lambda X, Y: (165 + (X - GIRL_STOP) / s, 1180 - (GIRL_Y - Y) / s)  # noqa: E731
    rest = dict(girl3.ARMS_DOWN['f'])                     # hanging at her side
    def ik_low(target):
        # of the two IK solutions, the one with the elbow lower (a natural reach)
        best = None
        for b in (1, -1):
            a = girl3.arm_ik('f', target, bend=b)
            a['el'] = (a['el'] + 180) % 360 - 180
            a['sh'] = (a['sh'] + 180) % 360 - 180
            ey = math.cos(math.radians(a['sh']))
            if best is None or ey > best[0]:
                best = (ey, a)
        return best[1]
    grab = ik_low(to_src(BAG_ON_COUNTER[0] - BAG_W * s / 2 + 8, BAG_ON_COUNTER[1] - BAG_H * s * 0.55))
    over = girl3.arm_ik('f', to_src(BOWL[0] - 70, BOWL[1] - 570), bend=-1)
    down = dict(girl3.ARMS_DOWN['f'])

    def mix(a, b, k):
        return dict(sh=a['sh'] + (b['sh'] - a['sh']) * k, el=a['el'] + (b['el'] - a['el']) * k)
    if t < REACH[1]:
        k = ease((t - REACH[0]) / (REACH[1] - REACH[0]))
        arm = dict(mix(rest, grab, k), hand='open' if k < 0.85 else 'grip')
    elif t < LIFT[1]:
        k = ease((t - LIFT[0]) / (LIFT[1] - LIFT[0]))
        arm = dict(mix(grab, over, k), hand='grip', prop=bag_prop(0.0), prop_behind=True)
    elif t < PUT[0]:
        k = ease((t - POUR[0]) / 0.35)
        shake = 4 * math.sin((t - POUR[0]) * 28) if t < PUT[0] - 0.2 else 0.0
        arm = dict(over, hand='grip', prop=bag_prop(118 * k + shake), prop_behind=True)
    elif t < PUT[1]:
        k = ease((t - PUT[0]) / (PUT[1] - PUT[0]))
        arm = dict(mix(over, down, k), hand='grip', prop=bag_prop(118 * (1 - k)), prop_behind=True)
    else:
        arm = dict(down, hand='grip', prop=bag_prop(0.0), prop_behind=True)
    return {'f': arm}


# ------------------------------------------------------------------ frames

def frame(t):
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(s)
    if CLOSE1[0] <= t < CLOSE1[1]:
        u = (t - CLOSE1[0]) / (CLOSE1[1] - CLOSE1[0])
        bowl_top(ctx, t, LAYOUT_SPOT, push=ease(u * 1.3), label='THE BOTTOM. IS. VISIBLE.',
                 label_p=max(0, (u - 0.3) / 0.7), spot=SPOT[:2])
    elif CLOSE2[0] <= t < CLOSE2[1]:
        u = (t - CLOSE2[0]) / (CLOSE2[1] - CLOSE2[0])
        k = ease((u - 0.1) / 0.6)
        bowl_top(ctx, t, (LAYOUT_SLIDE_A, LAYOUT_FULL, k), push=0.5, spot=SPOT[:2])
    elif CLOSE3[0] <= t < CLOSE3[1]:
        u = (t - CLOSE3[0]) / (CLOSE3[1] - CLOSE3[0])
        bowl_top(ctx, t, LAYOUT_BITE, push=0.5 + 0.4 * ease(u * 2), label='...one bite later.',
                 label_p=max(0, (u - 0.15) / 0.85), spot=BITE[:2])
    else:
        # the meow beat pushes in on the two of them; the feast is framed a little closer
        z = Z0
        if CLOSE3[1] <= t < SIGH2[1]:
            z = Z0 + 0.22 * ease((t - CLOSE3[1]) / 1.2)
        elif t >= SIGH2[1]:                           # eases back out so the pour is in frame
            z = Z0 + 0.22 - 0.16 * ease((t - SIGH2[1]) / 0.6)
        wide_zoom(ctx, t, z)
        m = meow_at(t)
        if m and m[1] >= 0:
            i, u, word = m
            pos = [(880, 1150, 70), (840, 1110, 76), (885, 1140, 82), (860, 1130, 86), (780, 1150, 84)][i]
            px, py = to_screen(pos[0], pos[1], z)
            shout(ctx, word, px, py, pos[2] * z, u, rot=-0.12 if i % 2 else 0.1)
        if t < 4.4:
            caption(ctx, 'My cat at 7 AM:', W / 2, 200, 78, pop=min(1, t / 0.3))
        if SIGH2[1] <= t < POUR[1]:
            caption(ctx, '...FINE.', W / 2, 200, 90, pop=min(1, (t - SIGH2[1]) / 0.3), tilt=2)
        if SAY[0] <= t < SAY[1]:
            x, *_ = girl_state(t)
            mx, my = to_screen(x + 40, 860, z)
            bubble(ctx, [("It's FULL.", 96)], 360, 330, (mx - 30, my - 120), (t - SAY[0]) / (SAY[1] - SAY[0]))
    s.flush()
    return s


_Z = (560.0, 1660.0)                    # camera zoom centre (wide shot)
Z0 = 1.12


def to_screen(x, y, z):
    return _Z[0] + (x - _Z[0]) * z, _Z[1] + (y - _Z[1]) * z


def wide_zoom(ctx, t, z):
    ctx.save()
    ctx.translate(_Z[0], _Z[1])
    ctx.scale(z, z)
    ctx.translate(-_Z[0], -_Z[1])
    kitchen(ctx, t)
    shadow(ctx, CAT_X, CAT_Y + 4, 125, 17, 0.18)
    cat3.draw_cat_front(ctx, CAT_X, CAT_Y, CAT_S, **cat_state(t))
    bowl_side(ctx, t)
    x, pose, expr, blink, look, talk = girl_state(t)
    shadow(ctx, x + 8, GIRL_Y + 2, 150, 20, 0.16)
    _bag_mouth.clear()
    girl3.draw_girl(ctx, x, GIRL_Y, GIRL_S, pose, expr, blink, look, talk, arms=girl_arms(t))
    ctx.restore()
    stream(ctx, t)


# ------------------------------------------------------------------ outputs

STILL_TIMES = [0.4, 4.9, 8.5, 10.9, 12.2, 15.3, 16.7, 17.3, 17.8, 18.3, 18.8, 19.4,
               20.2, 21.3]


def stills():
    from PIL import Image, ImageDraw
    tw, th = 270, 480
    cols = 6
    rows = (len(STILL_TIMES) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * (tw + 8) + 8, rows * (th + 8) + 8), 'white')
    d = ImageDraw.Draw(sheet)
    for i, t in enumerate(STILL_TIMES):
        s = frame(t)
        a = np.ndarray((H, s.get_stride() // 4, 4), np.uint8, s.get_data())[:, :W]
        im = Image.fromarray(np.dstack([a[..., 2], a[..., 1], a[..., 0]]), 'RGB')
        x, y = 8 + (i % cols) * (tw + 8), 8 + (i // cols) * (th + 8)
        sheet.paste(im.resize((tw, th), Image.LANCZOS), (x, y))
        d.text((x + 6, y + th - 18), '%.1fs' % t, fill=(255, 0, 0))
    p = os.path.join(ROOT, 'output', 'full_bowl_stills.png')
    sheet.save(p)
    print(p)


def _bytes(i):
    return bytes(frame(i / FPS).get_data())


def video(path, workers=4):
    from multiprocessing import Pool
    n = int(DUR * FPS)
    cmd = ['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgra', '-s', '%dx%d' % (W, H),
           '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p',
           '-movflags', '+faststart', path]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool(workers) as pool:
        for i, data in enumerate(pool.imap(_bytes, range(n), chunksize=4)):
            pr.stdin.write(data)
            if i % 90 == 0:
                print('frame %d/%d' % (i, n), flush=True)
    pr.stdin.close()
    pr.wait()
    print(path)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'video':
        video(sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, 'output', 'full_bowl_silent.mp4'))
    else:
        stills()
