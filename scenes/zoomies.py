"""Zoomies: Sunday, 4 PM, peace. She sips tea in her armchair; the cat sleeps in a patch of
sun. Its eyes snap open. For no reason at all it tears round the room: over her head (her
tea goes everywhere), onto the curtain, off screen (CRASH), back in, out the other side,
and skids into its sun patch. It sits. It calmly washes itself, as if nothing happened.
She stares at it, soaked: "...WHY?" The cat stops mid-lick. Its pupils go huge again.
"No. NO—"

Both characters are drawn in code every frame (lib/girl3.py sitting in the armchair with a
mug, lib/cat3.py); the living room, the armchair, the curtains, the tea too. Idea: the
genre's "cats panic for no reason" moment; our characters, our room, our zoomies run, the
spilt tea and the round-two ending.

Usage:
  python scenes/zoomies.py stills            -> output/zoomies_stills.png
  python scenes/zoomies.py still <t>         -> output/_zm_<t>.png
  python scenes/zoomies.py video [out.mp4]   -> silent 1080x1920 30 fps render
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
DUR = 14.6

FLOOR_Y = 1470
GX, GY, GS = 300.0, 1640.0, 0.85       # her feet point (sitting: the rig's FEET) and scale
SEAT_Y = GY - (1180 - (640 + 185 + 45)) * GS

# ------------------------------------------------------------------ timeline (s)
SIP = (0.0, 1.9)                       # mug up to her lips and down
SNAP = 2.45                            # the cat's eyes snap open
WIGGLE = (3.0, 3.75)                   # the butt wiggle before the launch
T_GO = 3.85                            # cut to wide: it goes
SPLASH = 4.05                          # over her head: the tea flies
CRASH = 6.75                           # off screen left
T_SKID = 8.95                          # skids into its sun patch
GROOM = (9.7, 11.9)
T_MED = 9.3                            # medium on her, soaked
SAY = (10.0, 11.2)                     # "...WHY?"
T_CLOSE = 11.5                         # close on the cat
FREEZE = 11.95                         # it stops mid-lick
AGAIN = 12.45                          # pupils huge again
T_FACE = 12.95                         # close on her: "No. NO-"
SAY2 = (13.05, 13.75)
T_WIDE2 = 13.8                         # wide: it launches again
LAUNCH2 = 14.05

# the cat's spots: (x, y, scale) = screen point under its paws
P_SUN = (830.0, 1650.0, 0.50)
P_BACK = (112.0, 1004.0, 0.40)         # top of the armchair's backrest
P_CURT = (628.0, 980.0, 0.42)          # hanging on the left curtain
P_FLOOR_A = (520.0, 1720.0, 0.52)
P_OFF_L = (-260.0, 1720.0, 0.52)
P_FLOOR_B = (470.0, 1760.0, 0.54)
P_OFF_R = (1360.0, 1700.0, 0.52)
P_SKID = (930.0, 1655.0, 0.50)         # where it lands before the skid
P_UP = (560.0, 900.0, 0.50)
# jumps: (t0, t1, from, to, arc height)
JUMPS = [(T_GO, 4.3, P_SUN, P_BACK, 420), (4.6, 4.95, P_BACK, P_CURT, 260), (5.7, 5.95, P_CURT, P_FLOOR_A, 40),
         (6.05, 6.35, P_FLOOR_A, P_OFF_L, 70), (7.35, 7.7, P_OFF_L, P_FLOOR_B, 70),
         (7.78, 8.12, P_FLOOR_B, P_OFF_R, 80), (8.55, 8.85, P_OFF_R, P_SKID, 120),
         (LAUNCH2, 14.45, P_SUN, P_UP, 300)]
PREP = 0.12                            # zoomies: barely any wind-up
LAND = 0.25


# ------------------------------------------------------------------ the living room

WALL = (0.96, 0.78, 0.64)
WALL_DK = (0.92, 0.72, 0.58)
SKY = (0.62, 0.82, 0.96)
FRAME = (0.98, 0.96, 0.92)
CURTAIN = (0.36, 0.62, 0.60)
CURTAIN_DK = (0.29, 0.52, 0.50)
FLOOR = (0.72, 0.50, 0.34)
FLOOR_DK = (0.64, 0.43, 0.29)
SUN = (1.0, 0.93, 0.60)
CHAIR = (0.86, 0.52, 0.30)
CHAIR_DK = (0.74, 0.42, 0.24)
TEA = (0.62, 0.36, 0.18)
MUG = (0.97, 0.96, 0.93)

WIN = (680, 470, 960, 960)


def curtain(ctx, x0, x1, sway=0.0):
    """A curtain hanging from the rod, its hem swinging by `sway` px."""
    top, bot = 420, 1440
    ctx.new_path()
    ctx.move_to(x0, top)
    ctx.line_to(x1, top)
    ctx.curve_to(x1 + 4, 800, x1 + sway * 0.6, 1100, x1 + sway + 6, bot)
    ctx.curve_to((x0 + x1) / 2 + sway, bot + 10, (x0 + x1) / 2 + sway, bot - 6, x0 + sway - 6, bot)
    ctx.curve_to(x0 + sway * 0.6, 1100, x0 - 4, 800, x0, top)
    ctx.close_path()
    ctx.set_source_rgb(*CURTAIN)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(6)
    ctx.stroke()
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_source_rgb(*CURTAIN_DK)
    ctx.set_line_width(6)
    for f in (0.33, 0.66):
        x = x0 + (x1 - x0) * f
        ctx.move_to(x, top + 20)
        ctx.curve_to(x, 800, x + sway * 0.5, 1100, x + sway, bot - 20)
        ctx.stroke()


def room(ctx, t, sway):
    ctx.set_source_rgb(*WALL)
    ctx.paint()
    # wallpaper: little dots in rows
    ctx.set_source_rgb(*WALL_DK)
    for j, y in enumerate(range(60, FLOOR_Y, 90)):
        for x in range(30 + 45 * (j % 2), W, 90):
            ctx.arc(x, y, 7, 0, 2 * math.pi)
            ctx.fill()
    # skirting board + floor boards
    ctx.rectangle(0, FLOOR_Y, W, H - FLOOR_Y)
    ctx.set_source_rgb(*FLOOR)
    ctx.fill()
    ctx.set_source_rgb(*FLOOR_DK)
    for y in (1560, 1680, 1820):
        ctx.rectangle(0, y, W, 6)
    ctx.fill()
    for x, y0, y1 in ((240, 1476, 1560), (700, 1566, 1680), (380, 1686, 1820), (900, 1826, H)):
        ctx.rectangle(x, y0, 6, y1 - y0)
    ctx.fill()
    _box(ctx, -10, FLOOR_Y - 40, W + 10, FLOOR_Y + 6, (0.98, 0.94, 0.88), 6)
    # the window: blue sky, a cloud drifting
    x0, y0, x1, y1 = WIN
    _box(ctx, x0 - 16, y0 - 16, x1 + 16, y1 + 16, FRAME, 7, 10)
    ctx.rectangle(x0, y0, x1 - x0, y1 - y0)
    ctx.set_source_rgb(*SKY)
    ctx.fill()
    ctx.save()
    ctx.rectangle(x0, y0, x1 - x0, y1 - y0)
    ctx.clip()
    cx = x0 + 60 + (t * 9) % 320
    for dx, dy, r in ((0, 0, 38), (40, -18, 44), (85, 0, 36), (42, 14, 38)):
        ctx.arc(cx + dx, 610 + dy, r, 0, 2 * math.pi)
        ctx.new_sub_path()
    ctx.set_source_rgb(1, 1, 1)
    ctx.fill()
    ctx.restore()
    ctx.set_source_rgb(*FRAME)
    ctx.rectangle(x0, (y0 + y1) / 2 - 7, x1 - x0, 14)
    ctx.rectangle((x0 + x1) / 2 - 7, y0, 14, y1 - y0)
    ctx.fill()
    ctx.rectangle(x0 - 16, y0 - 16, x1 - x0 + 32, y1 - y0 + 32)
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(7)
    ctx.stroke()
    _box(ctx, x0 - 44, y1 + 16, x1 + 44, y1 + 46, FRAME, 7)
    # the sunbeam onto the floor, with dust motes drifting in it
    ctx.move_to(x0, y1 + 46)
    ctx.line_to(x1, y1 + 46)
    ctx.line_to(1060, 1720)
    ctx.line_to(600, 1720)
    ctx.close_path()
    ctx.set_source_rgba(*SUN, 0.28)
    ctx.fill()
    ctx.save()
    ctx.translate(830, 1660)
    ctx.scale(250, 60)
    ctx.arc(0, 0, 1, 0, 2 * math.pi)
    ctx.restore()
    ctx.set_source_rgba(*SUN, 0.55)
    ctx.fill()
    rnd = random.Random(5)
    for k in range(16):
        u = (rnd.random() + t * rnd.uniform(0.02, 0.05)) % 1.0
        x = 700 + 260 * u + rnd.uniform(-60, 60) + 18 * math.sin(t * 0.8 + k)
        y = 1030 + 600 * ((rnd.random() + t * 0.03) % 1.0)
        ctx.arc(x, y, rnd.uniform(2.5, 4.5), 0, 2 * math.pi)
        ctx.set_source_rgba(1, 1, 0.9, 0.7)
        ctx.fill()
    # a picture: hills and a sun
    _box(ctx, 190, 600, 420, 800, FRAME, 7, 6)
    ctx.rectangle(206, 616, 198, 168)
    ctx.set_source_rgb(0.80, 0.92, 0.96)
    ctx.fill()
    ctx.arc(350, 670, 26, 0, 2 * math.pi)
    ctx.set_source_rgb(1.0, 0.80, 0.30)
    ctx.fill()
    ctx.move_to(206, 784)
    ctx.curve_to(260, 700, 320, 700, 404, 770)
    ctx.line_to(404, 784)
    ctx.close_path()
    ctx.set_source_rgb(0.50, 0.74, 0.44)
    ctx.fill()
    ctx.rectangle(190, 600, 230, 200)
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(7)
    ctx.stroke()
    # the curtains + rod
    curtain(ctx, 590, 668, sway)
    curtain(ctx, 972, 1050, 0.0)
    _box(ctx, 560, 404, 1075, 424, (0.55, 0.37, 0.25), 6, 8)


def armchair_back(ctx):
    """Backrest, seat cushion and base (she sits on it, side view, facing right)."""
    _box(ctx, 52, 1000, 172, SEAT_Y + 40, CHAIR, 7, 40)              # backrest
    _box(ctx, 68, 1030, 150, SEAT_Y + 10, CHAIR_DK, 0, 30)
    _box(ctx, 60, SEAT_Y + 30, 500, GY - 70, CHAIR_DK, 7, 22)       # base
    for lx in (84, 456):
        _box(ctx, lx, GY - 74, lx + 24, GY - 10, (0.44, 0.29, 0.20), 6, 6)
    _box(ctx, 120, SEAT_Y - 14, 500, SEAT_Y + 52, CHAIR, 7, 26)      # seat cushion


def armrest(ctx):
    """The armrest, drawn over her far side so she sits IN the chair."""
    _box(ctx, 150, SEAT_Y - 120, 470, SEAT_Y - 60, CHAIR, 7, 30)
    _box(ctx, 420, SEAT_Y - 120, 478, GY - 70, CHAIR, 7, 24)


# ------------------------------------------------------------------ the cat

def _arc(p0, p1, u, hgt):
    x = p0[0] + (p1[0] - p0[0]) * u
    y = p0[1] + (p1[1] - p0[1]) * u - hgt * 4 * u * (1 - u)
    s = p0[2] + (p1[2] - p0[2]) * u
    return x, y, s


def cat_place(t):
    """(x, y, scale, crouch, stretch, lean, airborne) from the jump list."""
    pos = P_SUN
    for (t0, t1, a, b, hgt) in JUMPS:
        if t >= t1:
            pos = b
    crouch, stretch, lean, air = 0.0, 0.0, 0.0, False
    x, y, s = pos
    for (t0, t1, a, b, hgt) in JUMPS:
        d = 1 if b[0] > a[0] else -1
        if t0 - PREP <= t < t0:
            k = ease((t - (t0 - PREP)) / PREP)
            crouch = 0.4 * k
            lean = 6 * d * k
        elif t0 <= t < t1:
            u = (t - t0) / (t1 - t0)
            x, y, s = _arc(a, b, ease(u) * 0.3 + u * 0.7, hgt)
            air = True
            stretch = math.sin(u * math.pi) * 0.9 + (0.4 if u < 0.15 else 0)
            lean = 18 * d * math.cos(u * math.pi)
            crouch = 0.25 * max(0.0, (u - 0.8) / 0.2)
        elif t1 <= t < t1 + LAND:
            k = (t - t1) / LAND
            crouch = 0.5 * math.exp(-k * 3.5) * math.cos(k * 4)
    # hanging on the curtain: long, swinging
    if JUMPS[1][1] <= t < JUMPS[2][0]:
        u = t - JUMPS[1][1]
        stretch = 0.55
        lean = 10 * math.sin(u * 9) * math.exp(-u * 2.5)
        x += 14 * math.sin(u * 9) * math.exp(-u * 2.5)
    # the skid into the sun patch: slides left, leaning back
    if JUMPS[6][1] <= t < T_SKID + 0.35:
        k = ease_out((t - JUMPS[6][1]) / (T_SKID + 0.35 - JUMPS[6][1]))
        x = P_SKID[0] + (P_SUN[0] - P_SKID[0]) * k
        lean = 16 * (1 - k)
        crouch = 0.35 * (1 - k)
    return x, y, s, crouch, stretch, lean, air


def curtain_sway(t):
    t0 = JUMPS[1][1]
    if t < t0:
        return 0.0
    u = t - t0
    return 40 * math.sin(u * 6) * math.exp(-u * 1.2) + (-30 * pulse(t, JUMPS[2][0], JUMPS[2][0] + 0.6))


def cat_state(t):
    mood, yaw, nod, mouth = 'deadpan', 0.0, 0.0, 1.0
    roll = 1.5 * math.sin(t * 1.1)
    look = [0.0, 0.0]
    ear_l = ear_r = 0.0
    blink = 0.0
    x, y, s, crouch, stretch, lean, air = cat_place(t)
    # asleep in the sun: a loaf, eyes shut, an ear twitch
    if t < SNAP:
        mood = 'content'
        crouch += 0.3
        nod = 0.2
        if 1.2 < t < 1.55:
            ear_r = 16 * math.sin((t - 1.2) / 0.35 * 2 * math.pi) * (1 - (t - 1.2) / 0.35)
    # eyes snap open: huge pupils; it rises a little, stares at nothing, wiggles its butt
    elif t < T_GO - PREP:
        k = ease_out((t - SNAP) / 0.1)
        mood = 'spooked' if t > SNAP + 0.04 else 'surprised'
        crouch += 0.3 * (1 - k) + 0.2 * k
        yaw = -0.3
        look = [-0.4, -0.2]
        if WIGGLE[0] <= t < WIGGLE[1]:
            u = t - WIGGLE[0]
            lean += 5 * math.sin(u * 2 * math.pi * 4.5)
            crouch += 0.12 + 0.05 * math.sin(u * 2 * math.pi * 9)
    # the run: wild eyes, ears back
    elif t < T_SKID:
        mood = 'spooked'
        yaw = 0.6 if x > 600 else -0.6
        look = [1.0 if yaw > 0 else -1.0, 0.0]
    # it sits. A beat. Then it washes, calm as anything
    elif t < FREEZE:
        mood = 'deadpan'
        yaw = -0.2
        if GROOM[0] <= t:
            u = t - GROOM[0]
            mood = 'groom'
            nod = 0.55 + 0.25 * math.sin(u * 2 * math.pi * 1.6)
            roll += -8 + 4 * math.sin(u * 2 * math.pi * 1.6)
            yaw = -0.35
            lean += -2
    # frozen mid-lick: the tongue still out, eyes open...
    elif t < AGAIN:
        mood = 'silly'
        nod, roll, yaw = 0.55, -8, -0.35
        look = [-0.2, 0.0]
    # ...and the pupils go huge again
    elif t < LAUNCH2 - PREP:
        k = ease_out((t - AGAIN) / 0.12)
        mood = 'spooked'
        nod = 0.55 * (1 - k)
        roll += -8 * (1 - k)
        yaw = -0.3
        look = [-0.4, -0.2]
        if t > AGAIN + 0.3:
            u = t - AGAIN - 0.3
            lean += 5 * math.sin(u * 2 * math.pi * 4.5)
            crouch += 0.14 + 0.05 * math.sin(u * 2 * math.pi * 9)
    else:
        mood = 'spooked'
    if air:
        ear_l, ear_r = 18, -18
    for b, d in ((9.1, 0.16),):
        if b <= t < b + d:
            blink = math.sin((t - b) / d * math.pi)
    breathe = math.sin(t * 2 * math.pi / (2.6 if t < SNAP else 1.0))
    return (x, y, s, stretch), dict(mood=mood, blink=blink, look=tuple(look), head_roll=roll, head_yaw=yaw,
                                    head_nod=nod, lean=lean, breathe=breathe, crouch=crouch,
                                    ear_l=ear_l, ear_r=ear_r, mouth_open=mouth)


def speed_lines(ctx, t):
    """Streaks trailing the cat while it flies."""
    (x, y, s, _), _st = cat_state(t)
    _, _, _, _, _, _, air = cat_place(t)
    if not air:
        return
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    for i, off in enumerate((-60, 0, 60)):
        pts = []
        for k in range(6):
            tt = t - 0.025 * k
            (px, py, ps, _), _ = cat_state(tt)
            pts.append((px, py - 250 * ps + off * ps))
        ctx.move_to(*pts[1])
        for p in pts[2:]:
            ctx.line_to(*p)
        ctx.set_source_rgba(1, 1, 1, 0.75)
        ctx.set_line_width(9)
        ctx.stroke()


def draw_cat(ctx, t):
    (x, y, s, stretch), st = cat_state(t)
    if x < -200 or x > W + 200:
        return
    if y > 1400:
        shadow(ctx, x, y + 2, 100 * s / 0.44, 14, 0.18)
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(1 - 0.10 * stretch, 1 + 0.16 * stretch)
    cat3.draw_cat_front(ctx, 0, 0, s, **st)
    ctx.restore()


def cat_head(t):
    (x, y, s, _), _st = cat_state(t)
    return x, y - (665 - 190) * s


# ------------------------------------------------------------------ the girl + her tea

def to_src(X, Y):
    return 165 + (X - GX) / GS, 1180 - (GY - Y) / GS


def to_screen(px, py):
    return GX + (px - 165) * GS, GY - (1180 - py) * GS


def tea_level(t):
    """0..1 how full the mug is: it empties in the splash."""
    return 1.0 - 0.85 * ease((t - SPLASH) / 0.25)


def mug_prop(tilt, level):
    def draw(ctx, Wr, ha):
        ctx.save()
        ctx.translate(Wr[0] + 6, Wr[1] + 4)
        ctx.rotate(math.radians(tilt))
        w, h = 58, 66
        # the handle (towards her)
        ctx.arc(-w / 2 - 4, h * 0.45, 16, 0, 2 * math.pi)
        ctx.set_source_rgb(*INK)
        ctx.set_line_width(13)
        ctx.stroke()
        ctx.arc(-w / 2 - 4, h * 0.45, 16, 0, 2 * math.pi)
        ctx.set_source_rgb(*MUG)
        ctx.set_line_width(6)
        ctx.stroke()
        _box(ctx, -w / 2, 0, w / 2, h, MUG, 4, 8)
        ctx.rectangle(-w / 2 + 4, h * 0.38, w - 8, 12)
        ctx.set_source_rgb(0.94, 0.48, 0.42)
        ctx.fill()
        if level > 0.05:
            ctx.save()
            ctx.translate(0, 4)
            ctx.scale(1, 0.32)
            ctx.arc(0, 0, w / 2 - 5, 0, 2 * math.pi)
            ctx.restore()
            ctx.set_source_rgb(*TEA)
            ctx.fill()
        ctx.restore()
    return draw


ARM_LAP = (0.0, 60.0)                  # far arm (sh, el): the mug resting on her lap
ARM_SIP = (70.0, 150.0)                # the mug at her lips
MUG_LAP = (505.0, 1265.0)              # the mug on screen while it rests on her lap


def girl_state(t):
    st = dict(girl3.STATES['sit_chair'])
    st['turn'] = 0.0
    expr, blink, look, talk = 'smile', 0.0, (0.0, 0.0), 0.0
    head = 0.0
    # where her eyes and head go: the sip, the stare at the cat, then following the run
    if t < SNAP:
        look = (0.8, 0.6)
    elif t < T_GO:
        look = (1.0, 0.8)                              # at the cat in the sun
        expr = 'neutral'
    elif t < SPLASH + 0.6:
        k = ease((t - T_GO) / 0.2)
        look = (1.0 - 2.0 * k, 0.8 - 1.8 * k)          # up and back: it flies over her
        st['turn'] = -0.7 * k
        head = -8 * k
        expr = 'surprised'
    elif t < 6.2:
        look = (1.0, -0.7)                             # the curtain
        expr = 'surprised'
        head = -6
    elif t < 7.35:
        k = ease((t - 6.2) / 0.3)
        look = (-1.0, 0.4)                             # off left: CRASH
        st['turn'] = -0.8 * k
        expr = 'surprised'
        head = 4 * pulse(t, CRASH, CRASH + 0.3)
    elif t < 8.4:
        u = (t - 7.35) / 1.05
        look = (-1.0 + 2.0 * ease(u), 0.6)             # it streaks past her feet
        st['turn'] = -0.8 * (1 - ease(u))
        expr = 'surprised'
    else:
        look = (1.0, 0.7)                              # at the cat, back in the sun
        expr = 'annoyed' if t < T_FACE else 'surprised'
        if t > T_SKID + 0.4:
            expr = 'bored' if t < T_FACE else 'surprised'
    for b, d in ((2.0, 0.16), (9.6, 0.2), (11.4, 0.16)):
        if b <= t < b + d:
            blink = math.sin((t - b) / d * math.pi)
    if SAY[0] <= t < SAY[1]:
        talk = abs(math.sin((t - SAY[0]) * math.pi * 3.0)) * 0.9
    if SAY2[0] <= t < SAY2[1]:
        talk = abs(math.sin((t - SAY2[0]) * math.pi * 5.0))
    # the splash: she flinches
    fl = pulse(t, SPLASH, SPLASH + 0.35)
    st['lean'] = st.get('lean', 0.0) - 10 * fl
    # the end: she ducks as it comes again
    if t >= LAUNCH2:
        st['lean'] = st.get('lean', 0.0) + 14 * ease((t - LAUNCH2) / 0.2)
        expr = 'surprised'
    st['head'] = head
    pose, _ = girl3.body(st)
    # the mug (far hand): a sip at the start, held on her lap after, flung up in the splash
    sip = math.sin(math.pi * min(1.0, max(0.0, (t - SIP[0]) / (SIP[1] - SIP[0]))))
    sip = ease(min(1.0, sip * 1.6))
    if t < SIP[1]:
        expr = 'happy' if sip > 0.8 else expr
    sh = ARM_LAP[0] + (ARM_SIP[0] - ARM_LAP[0]) * sip
    el = ARM_LAP[1] + (ARM_SIP[1] - ARM_LAP[1]) * sip
    tilt = -38 * sip
    jolt = pulse(t, SPLASH - 0.05, SPLASH + 0.5)
    if jolt:
        sh += 70 * jolt
        el += 20 * jolt
        tilt += 80 * jolt                              # tea out over the top
    arms = {'n': dict(sh=20, el=42, hand='relaxed'),
            'f': dict(sh=sh, el=el, hand='grip', prop=mug_prop(tilt, tea_level(t)))}
    # hair: blown by the fly-over, then stays a bit wild
    hl = 0.0
    if t > SPLASH - 0.1:
        d = t - SPLASH + 0.1
        hl = 14 * math.exp(-d * 2.2) * math.sin(d * 9) + 6 * min(1, d * 4)
    pose['lockL'] = dict(rot=hl)
    pose['lockR'] = dict(rot=-hl * 0.7)
    pose['lockF'] = dict(rot=hl * 1.2)
    return pose, expr, blink, look, talk, arms


def head_screen(t):
    return to_screen(175.0, 239.0)


def steam(ctx, t):
    if t > SPLASH:
        return
    x, y = MUG_LAP[0], MUG_LAP[1] - 30
    if t < SIP[1]:
        return
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    for i in range(2):
        ph = (t * 0.7 + i * 0.5) % 1.0
        ctx.move_to(x - 10 + 22 * i, y)
        for k in range(1, 6):
            ctx.line_to(x - 10 + 22 * i + 9 * math.sin(k * 1.4 + t * 3 + i), y - 18 * k - 30 * ph)
        ctx.set_source_rgba(1, 1, 1, 0.75 * math.sin(ph * math.pi))
        ctx.set_line_width(6)
        ctx.stroke()


def tea_splash(ctx, t):
    """Drops flying out of the mug, then a stain on her shirt and a puddle on the floor."""
    u = (t - SPLASH) / 0.55
    rnd = random.Random(9)
    ox, oy = MUG_LAP[0] + 40, MUG_LAP[1] - 150
    if 0 <= u < 1:
        for i in range(16):
            vx, vy = rnd.uniform(-160, 260), rnd.uniform(-420, -160)
            x = ox + vx * u
            y = oy + vy * u + 900 * u * u
            r = rnd.uniform(8, 15) * (1 - 0.4 * u)
            ctx.arc(x, y, r, 0, 2 * math.pi)
            ctx.set_source_rgb(*TEA)
            ctx.fill_preserve()
            ctx.set_source_rgb(*INK)
            ctx.set_line_width(3)
            ctx.stroke()
    if t >= SPLASH + 0.3:
        k = ease((t - SPLASH - 0.3) / 0.3)
        # the puddle in front of the chair
        ctx.save()
        ctx.translate(560, 1690)
        ctx.scale(90 * k, 18 * k)
        ctx.arc(0, 0, 1, 0, 2 * math.pi)
        ctx.restore()
        ctx.set_source_rgba(*TEA, 0.9)
        ctx.fill()


def shirt_stain(ctx, t):
    if t < SPLASH + 0.15:
        return
    k = ease((t - SPLASH - 0.15) / 0.25)
    x, y = to_screen(214.0, 576.0)
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(k, k)
    ctx.move_to(-34, -10)
    ctx.curve_to(-30, -40, 20, -44, 32, -14)
    ctx.curve_to(44, 10, 20, 40, 4, 30)
    ctx.curve_to(-6, 50, -24, 44, -20, 22)
    ctx.curve_to(-44, 20, -44, 0, -34, -10)
    ctx.close_path()
    ctx.set_source_rgba(*TEA, 0.75)
    ctx.fill()
    ctx.restore()


# ------------------------------------------------------------------ camera

def _clamp(z, cx, cy):
    hw, hh = W / (2 * z), H / (2 * z)
    return z, min(max(cx, hw), W - hw), min(max(cy, hh), H - hh)


def camera(t):
    wide = (1.0, W / 2, H / 2)
    if SNAP - 0.05 <= t < T_GO:
        hx, hy = cat_head(SNAP + 0.5)
        k = ease_out((t - SNAP + 0.05) / 0.2)          # a fast snap-zoom with its eyes
        z = 1 + 1.4 * k + 0.15 * ease((t - SNAP) / 1.3)
        cam = (z, W / 2 + (hx - W / 2) * k, H / 2 + (hy + 60 - H / 2) * k)
    elif T_MED <= t < T_CLOSE:
        hx, hy = head_screen(t)
        cam = (1.75, hx + 160, hy + 230)
    elif T_CLOSE <= t < T_FACE:
        hx, hy = cat_head(t)
        z = 2.4 + 0.35 * ease_out((t - AGAIN) / 0.15) if t >= AGAIN else 2.4
        cam = (z, hx, hy + 80)
    elif T_FACE <= t < T_WIDE2:
        hx, hy = head_screen(t)
        cam = (2.3 + 0.1 * (t - T_FACE), hx + 60, hy + 70)
    else:
        cam = wide
    j = pulse(t, CRASH, CRASH + 0.35)
    if j:
        cam = (cam[0] + 0.03 * j, cam[1] + 8 * math.sin(t * 90) * j, cam[2])
    return _clamp(*cam)


# ------------------------------------------------------------------ frames

def scene(ctx, t):
    room(ctx, t, curtain_sway(t))
    armchair_back(ctx)
    tea_splash_floor = t >= SPLASH + 0.3
    if tea_splash_floor:
        tea_splash(ctx, t)
    shadow(ctx, GX + 140, GY + 2, 170, 18, 0.16)
    pose, expr, blink, look, talk, arms = girl_state(t)
    girl3.draw_girl(ctx, GX, GY, GS, pose, expr, blink, look, talk, arms=arms)
    shirt_stain(ctx, t)
    steam(ctx, t)
    speed_lines(ctx, t)
    draw_cat(ctx, t)
    if not tea_splash_floor:
        tea_splash(ctx, t)


def frame(t):
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(s)
    z, cx, cy = camera(t)
    ctx.save()
    ctx.translate(W / 2, H / 2)
    ctx.scale(z, z)
    ctx.translate(-cx, -cy)
    scene(ctx, t)
    ctx.restore()
    # the words
    if SNAP <= t < T_GO:
        shout(ctx, '!', 790, 520, 220, (t - SNAP) / 1.0, rot=0.1)
    if T_GO <= t < T_GO + 1.0:
        shout(ctx, 'ZOOM', 560, 760, 130, (t - T_GO) / 1.0, rot=-0.14)
    if CRASH <= t < CRASH + 0.9:
        shout(ctx, 'CRASH!', 250, 900, 128, (t - CRASH) / 0.9, rot=0.1)
    if SAY[0] <= t < SAY[1] + 0.1:
        bubble(ctx, [('...WHY?', 110)], W / 2 + 60, 430, (W / 2 - 40, 760), (t - SAY[0]) / (SAY[1] - SAY[0]))
    if AGAIN <= t < T_FACE:
        shout(ctx, '!', 790, 520, 240, (t - AGAIN) / 0.6, rot=0.1)
    if SAY2[0] <= t < SAY2[1] + 0.05:
        bubble(ctx, [('No. NO—', 110)], W / 2, 430, (W / 2 - 60, 760), (t - SAY2[0]) / (SAY2[1] - SAY2[0]),
               shake=4 * math.sin(t * 60))
    if t < SNAP:
        caption(ctx, 'Sunday. 4 PM. Peace.', W / 2, 220, 78, pop=min(1, t / 0.3))
    s.flush()
    return s


# ------------------------------------------------------------------ outputs

STILL_TIMES = [0.2, 0.95, 2.2, 2.7, 3.4, 4.05, 4.5, 5.3, 5.85, 6.9, 7.55, 8.0, 9.05, 9.5, 10.5, 11.7,
               12.2, 12.7, 13.3, 14.3]


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
        d.text((x + 6, y + th - 18), '%.2fs' % t, fill=(255, 0, 0))
    p = os.path.join(ROOT, 'output', 'zoomies_stills.png')
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
        video(sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, 'output', 'zoomies_silent.mp4'))
    elif len(sys.argv) > 2 and sys.argv[1] == 'still':
        still(float(sys.argv[2]), os.path.join(ROOT, 'output', '_zm_%s.png' % sys.argv[2]))
    else:
        stills()
