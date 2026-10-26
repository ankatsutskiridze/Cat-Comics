"""Never alone: everything she tries to do, the cat is ON it. "Me: trying to work": it jumps
onto the laptop keyboard (asdfjkl;;;;). "Me: working out": mid-crunch it lands on her belly and
loafs there. "Me: brushing my teeth": it jumps into the sink and meows up at her. Then the turn,
"Me: wanting ONE cuddle": she opens her arms, it looks at her, looks away and jumps up onto
the shelf. "Oh, NOW you need space?"

Both characters are drawn in code every frame (lib/girl3.py sitting / lying / standing,
lib/cat3.py jumping between spots); the four rooms too. Premise: the genre's "life with a
clingy cat" montage (research/reference-videos/ref_DeVH6yysZRj.mp4); our situations, our
characters, our reversal at the end.

Usage:
  python scenes/never_alone.py stills            -> output/never_alone_stills.png
  python scenes/never_alone.py still <t>         -> output/_na_<t>.png
  python scenes/never_alone.py video [out.mp4]   -> silent 1080x1920 30 fps render
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
sys.path.insert(0, os.path.join(ROOT, 'scenes'))
import cat3  # noqa: E402
import girl3  # noqa: E402
from full_bowl import INK, _box, bubble, caption, ease, ease_out, pulse, shadow, shout  # noqa: E402

W, H, FPS = 1080, 1920, 30
S = girl3.STATES

# ------------------------------------------------------------------ timeline (s)
CUTS = [0.0, 4.4, 8.6, 12.6]           # the four scenes
DUR = 19.8
CAPTIONS = ['Me: trying to work', 'Me: working out', 'Me: brushing my teeth', 'Me: wanting ONE cuddle']


# ------------------------------------------------------------------ shared helpers

def girl_pt(pose, part, p):
    """A model point (src px) after the pose's bones."""
    sk = girl3._Skin(pose)
    return tuple(sk(part, np.array([p], float), None)[0])


def to_screen(gx, gy, gs, p):
    return gx + (p[0] - girl3.FEET[0]) * gs, gy + (p[1] - girl3.FEET[1]) * gs


def to_src(gx, gy, gs, X, Y):
    return girl3.FEET[0] + (X - gx) / gs, girl3.FEET[1] + (Y - gy) / gs


def blinks(t, times, d=0.16):
    for b in times:
        if b <= t < b + d:
            return math.sin((t - b) / d * math.pi)
    return 0.0


def _arc(p0, p1, u, hgt):
    x = p0[0] + (p1[0] - p0[0]) * u
    y = p0[1] + (p1[1] - p0[1]) * u - hgt * 4 * u * (1 - u)
    s = p0[2] + (p1[2] - p0[2]) * u
    return x, y, s


PREP, LAND = 0.32, 0.3


def cat_place(t, start, jumps):
    """(x, y, scale, crouch, stretch, lean, airborne): sits at `start` until a jump
    (t0, t1, to, arc height) takes it on; crouches before, squashes after."""
    pos, cur = start, start
    for (t0, t1, b, hgt) in jumps:
        if t >= t1:
            pos = b
    crouch, stretch, lean, air = 0.0, 0.0, 0.0, False
    x, y, s = pos
    for (t0, t1, b, hgt) in jumps:
        a = cur
        cur = b
        d = 1 if b[0] > a[0] else -1
        if t0 - PREP <= t < t0:
            k = ease((t - (t0 - PREP)) / PREP)
            crouch = 0.45 * k
            lean = 6 * d * k
        elif t0 <= t < t1:
            u = (t - t0) / (t1 - t0)
            x, y, s = _arc(a, b, ease(u) * 0.3 + u * 0.7, hgt)
            air = True
            stretch = math.sin(u * math.pi) * 0.9 + (0.4 if u < 0.15 else 0)
            lean = 14 * d * math.cos(u * math.pi)
            crouch = 0.25 * max(0.0, (u - 0.8) / 0.2)
        elif t1 <= t < t1 + LAND:
            k = (t - t1) / LAND
            crouch = 0.5 * math.exp(-k * 3.5) * math.cos(k * 4)
    return x, y, s, crouch, stretch, lean, air


def draw_cat(ctx, place, st, ground=None):
    x, y, s, crouch, stretch, lean, air = place
    st = dict(st)
    st['crouch'] = st.get('crouch', 0.0) + crouch
    st['lean'] = st.get('lean', 0.0) + lean
    if air:
        st['mood'] = 'deadpan'
        st['ear_l'], st['ear_r'] = 18, -18                  # ears back in the air
    if ground is not None:
        shadow(ctx, x, ground + 4, 92 * s / 0.44, 13, 0.18 if not air else 0.10)
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(1 - 0.10 * stretch, 1 + 0.16 * stretch)
    cat3.draw_cat_front(ctx, 0, 0, s, **st)
    ctx.restore()


def cat_base(t):
    return dict(mood='deadpan', blink=0.0, look=(0.0, 0.0), head_roll=1.5 * math.sin(t * 1.1), head_yaw=0.0,
                head_nod=0.0, breathe=math.sin(t * 2 * math.pi / 2.4))


def wall(ctx, col, stripe, floor_y, floor_col, plank_col):
    ctx.set_source_rgb(*col)
    ctx.paint()
    ctx.set_source_rgb(*stripe)
    for x in range(0, W, 120):
        ctx.rectangle(x, 0, 60, floor_y)
    ctx.fill()
    ctx.rectangle(0, floor_y, W, H - floor_y)
    ctx.set_source_rgb(*floor_col)
    ctx.fill()
    ctx.set_source_rgb(*plank_col)
    y, k = floor_y + 70, 0
    while y < H:
        ctx.rectangle(0, y, W, 6)
        for x in range(90 + 170 * (k % 2), W, 340):
            ctx.rectangle(x, y - 70 + 8 * (k > 0), 6, 64)
        y += 78 + 10 * k
        k += 1
    ctx.fill()
    _box(ctx, -10, floor_y - 34, W + 10, floor_y, (0.98, 0.97, 0.94), 6)          # skirting
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(7)
    ctx.move_to(0, floor_y)
    ctx.line_to(W, floor_y)
    ctx.stroke()


def window(ctx, x0, y0, x1, y1, t, night=False):
    _box(ctx, x0 - 16, y0 - 16, x1 + 16, y1 + 16, (0.98, 0.97, 0.94), 7, 8)
    g = cairo.LinearGradient(0, y0, 0, y1)
    g.add_color_stop_rgb(0, 0.55, 0.78, 0.96)
    g.add_color_stop_rgb(1, 0.82, 0.92, 0.98)
    ctx.rectangle(x0, y0, x1 - x0, y1 - y0)
    ctx.set_source(g)
    ctx.fill()
    # a cloud drifting by
    cx = x0 + ((t * 18) % (x1 - x0 + 200)) - 100
    ctx.save()
    ctx.rectangle(x0, y0, x1 - x0, y1 - y0)
    ctx.clip()
    for dx, dy, r in ((0, 0, 36), (40, -16, 44), (86, 0, 34)):
        ctx.arc(cx + dx, y0 + 90 + dy, r, 0, 2 * math.pi)
        ctx.close_path()
    ctx.set_source_rgb(1, 1, 1)
    ctx.fill()
    ctx.restore()
    ctx.set_source_rgb(0.98, 0.97, 0.94)
    ctx.rectangle(x0, (y0 + y1) / 2 - 7, x1 - x0, 14)
    ctx.rectangle((x0 + x1) / 2 - 7, y0, 14, y1 - y0)
    ctx.fill()
    ctx.rectangle(x0 - 16, y0 - 16, x1 - x0 + 32, y1 - y0 + 32)
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(7)
    ctx.stroke()
    _box(ctx, x0 - 40, y1 + 16, x1 + 40, y1 + 44, (0.98, 0.97, 0.94), 7)


def plant(ctx, x, y, k=1.0, t=0.0):
    """A potted plant standing at (x, y)."""
    sway = 2.5 * math.sin(t * 1.3)
    for ang, ln in ((-38, 110), (-12, 150), (14, 140), (40, 105), (-60, 80), (62, 80)):
        a = math.radians(ang + sway)
        bx, by = x + math.sin(a) * ln * k, y - 70 * k - math.cos(a) * ln * k
        ctx.move_to(x, y - 70 * k)
        ctx.curve_to(x + math.sin(a) * ln * 0.5 * k - 26 * k, y - 70 * k - math.cos(a) * ln * 0.6 * k, bx - 10 * k,
                     by + 10 * k, bx, by)
        ctx.curve_to(bx + 14 * k, by + 24 * k, x + math.sin(a) * ln * 0.5 * k + 26 * k,
                     y - 70 * k - math.cos(a) * ln * 0.4 * k, x, y - 70 * k)
        ctx.set_source_rgb(0.45, 0.72, 0.42)
        ctx.fill_preserve()
        ctx.set_source_rgb(*INK)
        ctx.set_line_width(5)
        ctx.stroke()
    ctx.move_to(x - 60 * k, y - 80 * k)
    ctx.line_to(x + 60 * k, y - 80 * k)
    ctx.line_to(x + 46 * k, y)
    ctx.line_to(x - 46 * k, y)
    ctx.close_path()
    ctx.set_source_rgb(0.86, 0.48, 0.36)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(6)
    ctx.stroke()


# ================================================================== 1. the laptop

GX1, GY1, GS1 = 300.0, 1640.0, 0.95
DESK_Y = 1196.0                          # desk top
DESK_X0, DESK_X1 = 440.0, 860.0
LAP_X0, LAP_X1 = 470.0, 705.0            # laptop base (side view)
C1_START = (935.0, 1615.0, 0.50)
C1_KEYS = (612.0, DESK_Y - 12, 0.42)
J1 = (1.0, 1.42)                         # the jump onto the keyboard
SMASH = 1.45                             # asdfjkl;;;
SIGH1 = 3.3


def chair1(ctx):
    seat_y = GY1 - (1180 - (640 + 185 + 45)) * GS1
    x0, x1 = GX1 - 120, GX1 + 110
    wood, wood_l = (0.62, 0.40, 0.24), (0.76, 0.52, 0.32)
    for lx in (x0 + 14, x1 - 34):
        _box(ctx, lx, seat_y + 20, lx + 22, GY1 - 4, wood, 6, 6)
    _box(ctx, x0 + 8, seat_y - 380, x0 + 30, seat_y + 10, wood, 6, 6)            # backrest post
    _box(ctx, x0 - 2, seat_y - 380, x0 + 40, seat_y - 260, (0.72, 0.48, 0.30), 6, 10)
    _box(ctx, x0, seat_y - 6, x1, seat_y + 26, wood_l, 6, 10)


def desk1(ctx):
    wood, wood_dk = (0.93, 0.80, 0.62), (0.80, 0.66, 0.48)
    for lx in (DESK_X0 + 22, DESK_X1 - 52):
        _box(ctx, lx, DESK_Y + 20, lx + 30, GY1 + 6, wood_dk, 6, 4)
    _box(ctx, DESK_X1 - 190, DESK_Y + 24, DESK_X1 - 22, DESK_Y + 120, wood_dk, 6, 6)    # drawer
    _box(ctx, DESK_X1 - 130, DESK_Y + 64, DESK_X1 - 82, DESK_Y + 78, (0.55, 0.42, 0.30), 4, 6)
    _box(ctx, DESK_X0, DESK_Y, DESK_X1, DESK_Y + 30, wood, 7, 6)
    # a mug
    mx = 800
    _box(ctx, mx - 30, DESK_Y - 76, mx + 30, DESK_Y, (0.95, 0.62, 0.62), 6, 8)
    ctx.arc(mx + 34, DESK_Y - 40, 18, -math.pi / 2, math.pi / 2)
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(7)
    ctx.stroke()


def laptop(ctx, t):
    # the lid: seen three-quarters, its lit screen toward her
    hx = LAP_X1 - 8
    pts = [(hx, DESK_Y - 14), (hx + 44, DESK_Y - 268), (hx + 4, DESK_Y - 290), (hx - 40, DESK_Y - 36)]
    ctx.move_to(*pts[0])
    for p in pts[1:]:
        ctx.line_to(*p)
    ctx.close_path()
    ctx.set_source_rgb(0.70, 0.73, 0.80)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(6)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.stroke()
    ins = [(hx - 6, DESK_Y - 30), (hx + 32, DESK_Y - 256), (hx + 6, DESK_Y - 270), (hx - 30, DESK_Y - 44)]
    ctx.move_to(*ins[0])
    for p in ins[1:]:
        ctx.line_to(*p)
    ctx.close_path()
    ctx.set_source_rgb(0.75, 0.90, 1.0)
    ctx.fill()
    # the base + keys
    _box(ctx, LAP_X0, DESK_Y - 16, LAP_X1, DESK_Y, (0.70, 0.73, 0.80), 6, 5)
    ctx.set_source_rgb(0.45, 0.48, 0.56)
    for k in range(9):
        ctx.rectangle(LAP_X0 + 20 + k * 21, DESK_Y - 22, 14, 6)
    ctx.fill()


def girl1(t):
    st = dict(S['sit_chair'], lean=16)
    if t > SIGH1:                                    # the sigh: shoulders and head drop
        k = pulse(t, SIGH1, SIGH1 + 0.9)
        st['lean'] = 16 + 6 * k
    pose, _ = girl3.body(st)
    pose['head'] = dict(rot=0.0)
    shn, shf = girl_pt(pose, 'shirt', girl3.SHOULDER['n']), girl_pt(pose, 'shirt', girl3.SHOULDER['f'])
    # typing: each hand taps on its own rhythm; after the landing they lift off and hover
    tn, tf = [350.0, 702.0], [372.0, 698.0]
    if t < J1[1] + 0.05:
        tn[1] -= 14 * abs(math.sin(t * math.pi * 6.5))
        tf[1] -= 14 * abs(math.sin(t * math.pi * 6.5 + 1.3))
        tn[0] += 6 * math.sin(t * 9)
    else:
        k = ease((t - J1[1] - 0.05) / 0.25)
        tn = [350 - 30 * k, 702 - 40 * k]
        tf = [372 - 30 * k, 698 - 34 * k]
        if t > SIGH1 + 0.2:                          # hands drop into her lap
            k2 = ease((t - SIGH1 - 0.2) / 0.5)
            tn = [tn[0] + (300 - tn[0]) * k2, tn[1] + (780 - tn[1]) * k2]
            tf = [tf[0] + (320 - tf[0]) * k2, tf[1] + (775 - tf[1]) * k2]
    arms = {'n': dict(girl3.arm_ik('n', tuple(tn), bend=-1, shoulder=shn), hand='relaxed'),
            'f': dict(girl3.arm_ik('f', tuple(tf), bend=-1, shoulder=shf), hand='relaxed')}
    for a in arms.values():
        a['wr'] = 75 - (a['sh'] + a['el'])           # fingers forward over the keys
    expr, look, blink, talk = 'smile', (0.6, 0.15), blinks(t, (0.6, 2.4, 3.9)), 0.0
    if J1[1] <= t < J1[1] + 0.5:
        expr = 'surprised'
        look = (0.8, 0.0)
    elif t >= J1[1] + 0.5:
        expr = 'bored'
        look = (1.0, 0.1)
    if t >= SIGH1:
        expr = 'annoyed'
        k = pulse(t, SIGH1, SIGH1 + 0.9)
        pose['head'] = dict(rot=6 * k)
        pose['nod'] = 0.4 * k
    return pose, expr, blink, look, talk, arms


def cat1(t):
    place = cat_place(t, C1_START, [(J1[0], J1[1], C1_KEYS, 230)])
    st = cat_base(t)
    st['blink'] = blinks(t, (0.3,), 0.18)
    if t < J1[0]:                                    # on the floor: eyes on her, then on the desk
        st['head_yaw'], st['look'] = -0.6, (-0.8, -0.5)
    else:
        st['head_yaw'], st['look'] = -0.7, (-0.9, -0.1)
        if 2.6 <= t < 3.2:                           # the slow blink
            st['blink'] = math.sin((t - 2.6) / 0.6 * math.pi) ** 0.6
        if t >= 3.5:
            st['mood'] = 'smug'
    return place, st


def scene1(ctx, t):
    wall(ctx, (0.80, 0.90, 0.86), (0.76, 0.87, 0.83), 1260, (0.78, 0.62, 0.48), (0.70, 0.55, 0.42))
    window(ctx, 560, 470, 940, 860, t)
    plant(ctx, 160, 1226, 0.9, t)
    chair1(ctx)
    desk1(ctx)
    laptop(ctx, t)
    shadow(ctx, GX1 + 60, GY1 + 2, 190, 22, 0.16)
    pose, expr, blink, look, talk, arms = girl1(t)
    girl3.draw_girl(ctx, GX1, GY1, GS1, pose, expr, blink, look, talk, arms=arms)
    place, st = cat1(t)
    draw_cat(ctx, place, st, GY1 if place[1] > 1500 else DESK_Y)
    p = (t - SMASH) / 0.9
    if 0 <= p < 1:
        shout(ctx, 'asdfjkl;;;;;', 740, DESK_Y - 420, 72, p, rot=-0.08)


# ================================================================== 2. the crunches

GX2, GY2, GS2 = 567.0, 1450.0, 0.85
C2_START = (965.0, 1300.0, 0.42)
J2 = (1.55, 1.95)                        # the jump onto her belly
CRUNCH_T = 0.9                           # one crunch
TRY = (2.7, 3.25)                        # she tries to sit up, can't


def crunch_k(t):
    """0 lying .. 1 up (the half sit-up)."""
    if t < 2 * CRUNCH_T:
        return math.sin(math.pi * t / CRUNCH_T) ** 2
    if TRY[0] <= t < TRY[1] + 0.25:
        u = (t - TRY[0]) / (TRY[1] - TRY[0])
        return 0.14 * math.sin(min(1.0, u) * math.pi) + 0.02 * math.sin(t * 60) * (u < 1)
    return 0.0


def girl2(t):
    k = crunch_k(t)
    up = girl3.blend(S['sit_floor'], S['lie_back'], 0.5)
    st = girl3.blend(S['lie_back'], up, k)
    pose, arms = girl3.body(st)
    expr, look, blink, talk = 'neutral', (0.9, 0.1), blinks(t, (3.9,)), 0.0
    if t < J2[1]:
        look = (0.9, 0.2 + 0.3 * k)
    elif t < J2[1] + 0.5:
        expr, look = 'surprised', (0.3, 1.0)
    else:
        expr, look = 'annoyed', (0.3, 1.0)
        if TRY[0] <= t < TRY[1]:
            expr = 'angry'
        if t > TRY[1] + 0.4:
            expr = 'bored'
    return pose, expr, blink, look, talk, arms


def belly2(t):
    pose, _ = girl3.body(S['lie_back'])
    p = girl_pt(pose, 'shirt', (168.0, 560.0))
    x, y = to_screen(GX2, GY2, GS2, p)
    return (x, y - 112, 0.40)


def cat2(t):
    land = belly2(t)
    place = cat_place(t, C2_START, [(J2[0], J2[1], land, 260)])
    st = cat_base(t)
    if t < J2[0]:                                    # its head bobs with her crunches
        k = crunch_k(t)
        st['head_yaw'], st['look'] = -0.7, (-0.9, 0.3 - 0.7 * k)
        st['head_nod'] = 0.3 - 0.5 * k
    else:
        st['head_yaw'], st['look'] = -0.3, (-0.6, 0.4)
        x, y, s, crouch, stretch, lean, air = place
        if t > J2[1] + 0.45:                         # settles into a loaf, eyes shut
            kk = ease((t - J2[1] - 0.45) / 0.5)
            place = (x, y + 10 * kk, s, crouch + 0.3 * kk, stretch, lean, air)
            st['mood'] = 'content' if t > J2[1] + 0.7 else 'smug'
            st['head_yaw'] = -0.3 * (1 - kk)
            st['head_roll'] += 6 * kk
        if TRY[0] <= t < TRY[1] + 0.2:               # rides her attempt
            u = crunch_k(t)
            place = (place[0] - 30 * u, place[1] - 120 * u, *place[2:])
    return place, st


def mat2(ctx):
    pts = [(40, 1395), (1000, 1395), (1060, 1640), (-20, 1640)]
    ctx.move_to(*pts[0])
    for p in pts[1:]:
        ctx.line_to(*p)
    ctx.close_path()
    ctx.set_source_rgb(0.62, 0.55, 0.85)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(7)
    ctx.stroke()
    ctx.set_source_rgb(0.55, 0.48, 0.78)
    ctx.rectangle(0, 1600, W, 14)
    ctx.fill()


def sofa(ctx, x0, x1, y_floor, col=(0.42, 0.62, 0.66), dk=(0.35, 0.53, 0.57)):
    top = y_floor - 330
    _box(ctx, x0 + 20, y_floor - 30, x0 + 60, y_floor + 6, (0.45, 0.32, 0.24), 6)
    _box(ctx, x1 - 60, y_floor - 30, x1 - 20, y_floor + 6, (0.45, 0.32, 0.24), 6)
    _box(ctx, x0 + 40, top, x1 - 40, y_floor - 150, col, 7, 40)                      # back
    _box(ctx, x0 + 40, y_floor - 175, x1 - 40, y_floor - 28, dk, 7, 18)              # seat
    mid = (x0 + x1) / 2
    _box(ctx, x0 + 60, y_floor - 200, mid - 4, y_floor - 120, col, 7, 22)            # cushions
    _box(ctx, mid + 4, y_floor - 200, x1 - 60, y_floor - 120, col, 7, 22)
    _box(ctx, x0, top + 110, x0 + 90, y_floor - 28, col, 7, 30)                      # arms
    _box(ctx, x1 - 90, top + 110, x1, y_floor - 28, col, 7, 30)
    # a throw pillow
    _box(ctx, x1 - 230, y_floor - 290, x1 - 110, y_floor - 180, (0.98, 0.80, 0.42), 7, 30)


def shelf(ctx, x0, x1, y, t, books=True):
    _box(ctx, x0, y, x1, y + 26, (0.86, 0.68, 0.50), 7, 4)
    for bx in (x0 + 40, x1 - 60):
        ctx.move_to(bx, y + 26)
        ctx.line_to(bx + 22, y + 70)
        ctx.set_source_rgb(*INK)
        ctx.set_line_width(7)
        ctx.stroke()
    if books:
        bx = x1 - 30
        for wdt, hgt, col in ((26, 120, (0.85, 0.40, 0.38)), (30, 140, (0.36, 0.55, 0.78)),
                              (24, 110, (0.95, 0.80, 0.40))):
            _box(ctx, bx - wdt, y - hgt, bx, y, col, 6, 3)
            bx -= wdt + 2


def living(ctx, t):
    wall(ctx, (0.99, 0.87, 0.80), (0.97, 0.83, 0.76), 1190, (0.80, 0.64, 0.50), (0.72, 0.56, 0.43))
    # a framed picture: a fish
    _box(ctx, 140, 520, 400, 720, (0.96, 0.94, 0.88), 7, 6)
    ctx.save()
    ctx.translate(255, 620)
    ctx.scale(1.0, 0.55)
    ctx.arc(0, 0, 70, 0, 2 * math.pi)
    ctx.restore()
    ctx.move_to(320, 620)
    ctx.line_to(370, 580)
    ctx.line_to(370, 660)
    ctx.close_path()
    ctx.set_source_rgb(0.40, 0.70, 0.85)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(5)
    ctx.stroke()
    ctx.arc(215, 610, 7, 0, 2 * math.pi)
    ctx.fill()
    shelf(ctx, 700, 1040, 905, t)
    plant(ctx, 760, 905, 0.55, t)


def scene2(ctx, t):
    living(ctx, t)
    sofa(ctx, 60, 1020, 1190)
    mat2(ctx)
    place, st = cat2(t)
    if place[1] < 1340 and t < J2[0]:                # waiting behind her, on the floor
        draw_cat(ctx, place, st, place[1])
    pose, expr, blink, look, talk, arms = girl2(t)
    girl3.draw_girl(ctx, GX2, GY2, GS2, pose, expr, blink, look, talk, arms=arms)
    if t >= J2[0]:
        draw_cat(ctx, place, st)
    p = (t - J2[1]) / 0.8
    if 0 <= p < 1:
        shout(ctx, 'OOF!', 330, 1060, 110, p, rot=-0.12)


# ================================================================== 3. the sink

GX3, GY3, GS3 = 330.0, 1690.0, 0.98
RIM_Y = 1130.0                            # the basin's rim
SINK_X0, SINK_X1 = 560.0, 920.0
C3_START = (975.0, 1735.0, 0.48)
C3_SINK = (742.0, RIM_Y + 92, 0.42)
J3 = (1.3, 1.72)
MEOW3 = (2.55, 0.65)
MOUTH = (226.0, 198.0)                    # her mouth (src px, standing)


def brush_prop(ctx, Wr, ha):
    """The toothbrush in her fist: the handle from the fist straight back into her mouth."""
    dx, dy = math.sin(math.radians(ha)), math.cos(math.radians(ha))
    fx, fy = Wr[0] + dx * 30, Wr[1] + dy * 30                  # the fist's middle
    mx, my = MOUTH[0] + 4, MOUTH[1] + 6
    ctx.save()
    ctx.translate(fx, fy)
    ctx.rotate(math.atan2(my - fy, mx - fx))
    L = math.hypot(mx - fx, my - fy)
    _box(ctx, -26, -7, L, 7, (0.40, 0.75, 0.95), 4, 7)
    _box(ctx, L - 26, -20, L + 2, -6, (0.98, 0.98, 1.0), 3, 3)
    ctx.restore()


def girl3_state(t):
    pose, _ = girl3.body(S['stand'])
    shn = girl_pt(pose, 'shirt', girl3.SHOULDER['n'])
    scrub = 0.0 if t >= J3[1] + 0.1 else 9 * math.sin(t * 2 * math.pi * 4.2)
    target = (MOUTH[0] + 62 + scrub, MOUTH[1] + 92 + scrub * 0.2)
    arm = dict(girl3.arm_ik('n', target, bend=1, shoulder=shn), hand='grip')
    arm['wr'] = 180 - (arm['sh'] + arm['el'])           # the fist upright under her chin
    arm['prop'] = brush_prop
    arm['prop_behind'] = True
    arms = {'n': arm}
    expr, look, blink, talk = 'bored', (1.0, 0.0), blinks(t, (0.5, 3.4)), 0.0
    if J3[1] <= t < J3[1] + 0.5:
        expr, look = 'surprised', (0.8, 0.9)
    elif t >= J3[1] + 0.5:
        expr, look = 'bored', (0.8, 0.9)
        if t >= MEOW3[0] + 0.4:
            expr = 'annoyed'
    pose['head'] = dict(rot=4 * ease((t - J3[1]) / 0.3) if t > J3[1] else 0.0)
    return pose, expr, blink, look, talk, arms


def cat3_state(t):
    place = cat_place(t, C3_START, [(J3[0], J3[1], C3_SINK, 320)])
    st = cat_base(t)
    if t < J3[0]:
        st['head_yaw'], st['look'] = -0.4, (-0.5, -0.8)
    else:
        st['head_yaw'], st['look'] = -0.5, (-0.8, -0.9)
        st['head_nod'] = -0.4
        a, d = MEOW3
        if a <= t < a + d:
            u = (t - a) / d
            st['mood'] = 'meow'
            st['mouth_open'] = math.sin(u * math.pi) ** 0.6
            st['head_roll'] += -6 * math.sin(u * math.pi)
        elif t >= a + d + 0.3:
            st['mood'] = 'smug'
    return place, st


def bathroom(ctx, t):
    ctx.set_source_rgb(0.82, 0.90, 0.96)
    ctx.paint()
    ctx.set_source_rgb(0.74, 0.84, 0.92)
    for x in range(0, W, 108):
        ctx.rectangle(x, 0, 5, 1300)
    for y in range(0, 1300, 108):
        ctx.rectangle(0, y, W, 5)
    ctx.fill()
    ctx.rectangle(0, 1300, W, H - 1300)
    ctx.set_source_rgb(0.60, 0.66, 0.78)
    ctx.fill()
    ctx.set_source_rgb(0.54, 0.60, 0.72)
    for k, y in enumerate((1380, 1480, 1600, 1750)):
        ctx.rectangle(0, y, W, 6)
    ctx.fill()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(7)
    ctx.move_to(0, 1300)
    ctx.line_to(W, 1300)
    ctx.stroke()
    # the mirror over the sink, with its shine
    mx, my, rx, ry = (SINK_X0 + SINK_X1) / 2, 720, 150, 200
    ctx.save()
    ctx.translate(mx, my)
    ctx.scale(rx + 16, ry + 16)
    ctx.arc(0, 0, 1, 0, 2 * math.pi)
    ctx.restore()
    ctx.set_source_rgb(0.98, 0.97, 0.94)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(7)
    ctx.stroke()
    ctx.save()
    ctx.translate(mx, my)
    ctx.scale(rx, ry)
    ctx.arc(0, 0, 1, 0, 2 * math.pi)
    ctx.restore()
    ctx.set_source_rgb(0.70, 0.86, 0.94)
    ctx.fill()
    ctx.set_source_rgba(1, 1, 1, 0.7)
    ctx.set_line_width(14)
    for d in (0, 40):
        ctx.move_to(mx - 80 + d, my - 60 + d)
        ctx.line_to(mx - 20 + d, my - 120 + d)
    ctx.stroke()
    # a towel on a hook
    _box(ctx, 20, 760, 150, 1040, (0.98, 0.72, 0.70), 7, 14)
    _box(ctx, 20, 980, 150, 1010, (0.92, 0.60, 0.60), 0)
    ctx.arc(85, 742, 14, 0, 2 * math.pi)
    ctx.set_source_rgb(*INK)
    ctx.fill()


def sink_back(ctx):
    cx, rx = (SINK_X0 + SINK_X1) / 2, (SINK_X1 - SINK_X0) / 2
    _box(ctx, cx - 40, RIM_Y + 100, cx + 40, GY3 + 6, (0.98, 0.98, 1.0), 7, 8)      # pedestal
    # the faucet on the back of the rim
    _box(ctx, cx - 16, RIM_Y - 90, cx + 16, RIM_Y - 8, (0.80, 0.82, 0.88), 6, 6)
    _box(ctx, cx - 16, RIM_Y - 90, cx + 70, RIM_Y - 64, (0.80, 0.82, 0.88), 6, 10)
    # the rim: an ellipse seen from above, the bowl inside it
    ctx.save()
    ctx.translate(cx, RIM_Y)
    ctx.scale(rx, 46)
    ctx.arc(0, 0, 1, 0, 2 * math.pi)
    ctx.restore()
    ctx.set_source_rgb(0.98, 0.98, 1.0)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(7)
    ctx.stroke()
    ctx.save()
    ctx.translate(cx, RIM_Y + 4)
    ctx.scale(rx - 26, 30)
    ctx.arc(0, 0, 1, 0, 2 * math.pi)
    ctx.restore()
    ctx.set_source_rgb(0.80, 0.86, 0.92)
    ctx.fill()


def sink_front(ctx):
    """The basin's front, drawn over whatever sits in the bowl."""
    cx, rx = (SINK_X0 + SINK_X1) / 2, (SINK_X1 - SINK_X0) / 2
    ctx.new_path()
    ctx.move_to(cx - rx, RIM_Y)
    ctx.curve_to(cx - rx, RIM_Y + 120, cx - 60, RIM_Y + 140, cx, RIM_Y + 140)
    ctx.curve_to(cx + 60, RIM_Y + 140, cx + rx, RIM_Y + 120, cx + rx, RIM_Y)
    # back along the rim's front edge
    ctx.save()
    ctx.translate(cx, RIM_Y + 4)
    ctx.scale(rx - 26, 30)
    ctx.arc(0, 0, 1, 0, math.pi)
    ctx.restore()
    ctx.close_path()
    ctx.set_source_rgb(0.98, 0.98, 1.0)
    ctx.fill()
    ctx.new_path()
    ctx.move_to(cx - rx, RIM_Y)
    ctx.curve_to(cx - rx, RIM_Y + 120, cx - 60, RIM_Y + 140, cx, RIM_Y + 140)
    ctx.curve_to(cx + 60, RIM_Y + 140, cx + rx, RIM_Y + 120, cx + rx, RIM_Y)
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(7)
    ctx.stroke()
    ctx.save()
    ctx.translate(cx, RIM_Y + 4)
    ctx.scale(rx - 26, 30)
    ctx.arc(0, 0, 1, 0, math.pi)
    ctx.restore()
    ctx.set_line_width(5)
    ctx.stroke()


def foam(ctx, t):
    """Toothpaste foam at her mouth corner."""
    x, y = to_screen(GX3, GY3, GS3, (MOUTH[0] - 2, MOUTH[1] + 8))
    rnd = random.Random(4)
    for k in range(5):
        dx, dy, r = rnd.uniform(-10, 14), rnd.uniform(-6, 12), rnd.uniform(5, 9)
        r *= 1 + 0.15 * math.sin(t * 9 + k)
        ctx.arc(x + dx, y + dy, r, 0, 2 * math.pi)
        ctx.close_path()
    ctx.set_source_rgb(1, 1, 1)
    ctx.fill_preserve()
    ctx.set_source_rgb(0.62, 0.66, 0.74)
    ctx.set_line_width(2.0)
    ctx.stroke()


def scene3(ctx, t):
    bathroom(ctx, t)
    sink_back(ctx)
    place, st = cat3_state(t)
    in_sink = t >= J3[1] - 0.05
    if not in_sink:
        sink_front(ctx)
    shadow(ctx, GX3 + 10, GY3 + 2, 150, 20, 0.16)
    pose, expr, blink, look, talk, arms = girl3_state(t)
    girl3.draw_girl(ctx, GX3, GY3, GS3, pose, expr, blink, look, talk, arms=arms)
    foam(ctx, t)
    draw_cat(ctx, place, st, GY3 + 45 if place[1] > 1500 else None)
    if in_sink:
        sink_front(ctx)
    p = (t - MEOW3[0]) / 1.0
    if 0 <= p < 1:
        shout(ctx, 'MEOW.', 860, 860, 92, p, rot=0.1)


# ================================================================== 4. the cuddle

GX4, GY4, GS4 = 240.0, 1500.0, 0.9
C4_START = (840.0, 1520.0, 0.50)
C4_SHELF = (905.0, 905.0, 0.40)
J4 = (3.45, 3.95)
ASK = (0.35, 2.0)                         # "Toby! Cuddle time!"
AWAY = 2.6                                # it looks away
DROP = (4.5, 5.3)                         # her arms come down
SAY4 = (5.3, 7.0)                         # "Oh, NOW you need space?"


def girl4(t):
    st = dict(S['sit_floor'])
    pose, _ = girl3.body(st)
    lap = {'n': dict(sh=-12, el=10, hand='open'), 'f': dict(sh=-22, el=0, hand='open')}
    hug = {'n': dict(sh=118, el=-28, wr=-12, hand='open'), 'f': dict(sh=132, el=-22, wr=-12, hand='open')}
    k = ease((t - 0.05) / 0.35) * (1 - 0.75 * ease((t - DROP[0]) / (DROP[1] - DROP[0])))
    wig = 4 * math.sin(t * 7) * (t < ASK[1])           # eager little wiggle
    arms = {}
    for s_ in ('n', 'f'):
        a, b = lap[s_], hug[s_]
        arms[s_] = dict(sh=a['sh'] + (b['sh'] - a['sh']) * k + wig, el=a['el'] + (b['el'] - a['el']) * k,
                        wr=b['wr'] * k, hand='open')
    expr, look, blink, talk = 'happy', (1.0, 0.2), blinks(t, (2.3, 6.0)), 0.0
    if ASK[0] <= t < ASK[1]:
        talk = abs(math.sin((t - ASK[0]) * math.pi * 4.2)) if t < ASK[1] - 0.3 else 0.0
        expr = 'smile' if talk > 0.05 else 'happy'
    if t >= AWAY + 0.2:
        expr = 'neutral'
    if t >= J4[0]:                                       # eyes follow it up to the shelf
        kk = ease((t - J4[0]) / (J4[1] - J4[0]))
        look = (1.0, 0.2 - 1.0 * kk)
        pose['head'] = dict(rot=-8 * kk)
    if t >= DROP[0]:
        expr = 'bored'
    if SAY4[0] <= t < SAY4[1]:
        talk = abs(math.sin((t - SAY4[0]) * math.pi * 4.0)) if t < SAY4[1] - 0.35 else 0.0
        expr = 'annoyed'
    return pose, expr, blink, look, talk, arms


def cat4(t):
    place = cat_place(t, C4_START, [(J4[0], J4[1], C4_SHELF, 200)])
    st = cat_base(t)
    st['blink'] = blinks(t, (0.9,), 0.18)
    if t < AWAY:
        st['head_yaw'], st['look'] = -0.6, (-0.9, -0.2)
        if 1.7 <= t < 2.3:                               # a long look...
            st['blink'] = 0.5 * math.sin((t - 1.7) / 0.6 * math.pi)
    elif t < J4[0] - PREP:                               # ...and it turns its head away
        k = ease((t - AWAY) / 0.3)
        st['head_yaw'], st['look'] = -0.6 + 1.4 * k, (-0.9 + 1.9 * k, -0.2 - 0.3 * k)
        st['mood'] = 'smug'
        st['head_roll'] += 5 * k
    else:
        st['head_yaw'], st['look'] = 0.8, (1.0, -0.2)
        st['mood'] = 'smug'
        if t > J4[1] + 0.5:                              # on the shelf: aloof, eyes half shut
            st['mood'] = 'sleepy'
            st['head_yaw'] = 0.6
    return place, st


def scene4(ctx, t):
    living(ctx, t)
    sofa(ctx, 60, 760, 1190)
    rug_c = (560, 1560)
    ctx.save()
    ctx.translate(*rug_c)
    ctx.scale(470, 120)
    ctx.arc(0, 0, 1, 0, 2 * math.pi)
    ctx.restore()
    ctx.set_source_rgb(0.93, 0.80, 0.55)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(6)
    ctx.stroke()
    place, st = cat4(t)
    shadow(ctx, GX4 + 40, 1480, 200, 24, 0.16)
    pose, expr, blink, look, talk, arms = girl4(t)
    girl3.draw_girl(ctx, GX4, GY4, GS4, pose, expr, blink, look, talk, arms=arms)
    draw_cat(ctx, place, st, C4_START[1] if place[1] > 1200 else None)
    hx, hy = to_screen(GX4, GY4, GS4, girl_pt(pose, 'face', MOUTH))
    if ASK[0] <= t < ASK[1] + 0.2:
        bubble(ctx, [('TOBY!', 96), ('Cuddle time!', 66)], 470, 760, (hx + 20, hy - 60),
               (t - ASK[0]) / (ASK[1] - ASK[0]))
    if SAY4[0] <= t:
        bubble(ctx, [('Oh, NOW', 84), ('you need space?', 66)], 480, 760, (hx + 20, hy - 60),
               min(1.0, (t - SAY4[0]) / 1.2))


# ------------------------------------------------------------------ frames

SCENES = [scene1, scene2, scene3, scene4]


def which(t):
    i = max(k for k, c in enumerate(CUTS) if t >= c)
    return i, t - CUTS[i]


def frame(t):
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(s)
    i, u = which(t)
    SCENES[i](ctx, u)
    caption(ctx, CAPTIONS[i], W / 2, 240, 74, pop=min(1, u / 0.3 + (0.34 if i == 0 else 0)))
    s.flush()
    return s


# ------------------------------------------------------------------ outputs

STILL_TIMES = [0.3, 1.2, 1.6, 2.6, 3.8, 4.8, 5.5, 6.1, 7.0, 7.9, 9.2, 10.0, 10.5, 11.3, 13.2, 15.0, 16.0,
               16.8, 18.0, 19.5]


def stills():
    from PIL import Image, ImageDraw
    tw, th = 270, 480
    cols = 10
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
    p = os.path.join(ROOT, 'output', 'never_alone_stills.png')
    sheet.save(p)
    print(p)


def still(t, path):
    s = frame(t)
    s.write_to_png(path)
    print(path)


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
        video(sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, 'output', 'never_alone_silent.mp4'))
    elif len(sys.argv) > 2 and sys.argv[1] == 'still':
        still(float(sys.argv[2]), os.path.join(ROOT, 'output', '_na_%s.png' % sys.argv[2]))
    else:
        stills()
