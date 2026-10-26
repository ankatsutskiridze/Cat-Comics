"""Warm spot: all night the cat wakes her from a new spot, jumping from perch to perch (the
floor, her chest, the window sill, the pillow by her face) while the bedside clock runs from
1:12 to 3:38. At the pillow it screams into her face; she sits up: "WHAT DO YOU WANT?!"
The cat stares, hops into the warm dent her head left in the pillow, curls up and purrs.
"...my warm spot?!"

Both characters are drawn in code every frame (lib/girl3.py, lib/cat3.py); the bedroom too.
Premise: the genre's "the cat wakes you all night for nothing" moment; our characters, our
perches, our clock, and our own ending (it wanted the warm spot).

Usage:
  python scenes/warm_spot.py stills            -> output/warm_spot_stills.png
  python scenes/warm_spot.py video [out.mp4]   -> silent 1080x1920 30 fps render
"""
import math
import os
import subprocess
import sys

import cairo
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'lib'))
sys.path.insert(0, os.path.join(ROOT, 'scenes'))
import cat3  # noqa: E402
import girl3  # noqa: E402
import full_bowl as K  # noqa: E402  (caption, shout, bubble, shadow, easing)

W, H, FPS = 1080, 1920, 30
DUR = 19.2
INK = K.INK
ease, ease_out, pulse = K.ease, K.ease_out, K.pulse
S = girl3.STATES

FLOOR_Y = 1470
MAT_Y = 1235                           # mattress top = her root line
BED_X0 = 222                           # headboard (left end); the bed runs off the right edge
GX, GS = 770, 0.72                     # her root point (under the hips) and scale
CS = 0.5                               # cat scale

# ------------------------------------------------------------------ timeline (s)
# perches: (x, y) under the cat's paws
P_FLOOR = (640, 1660)
P_CHEST = (600, 1150)
P_SILL = (800, 868)
P_PILLOW = (318, 1168)
P_DENT = (455, 1178)
# jumps: (start, duration, from, to, apex height above the higher end)
JUMPS = [(3.0, 0.55, P_FLOOR, P_CHEST, 170),
         (6.55, 0.5, P_CHEST, P_SILL, 120),
         (9.75, 0.5, P_SILL, P_PILLOW, 90),
         (15.6, 0.34, P_PILLOW, P_DENT, 55)]
CLOCK = [(0.0, '1:12'), (3.25, '2:05'), (6.8, '2:51'), (10.0, '3:38')]
MEOWS = [(0.15, 0.5, 'MEOW!', 70), (0.95, 0.55, 'MEOW!', 74), (1.85, 0.6, 'MEOW!!', 80),
         (5.45, 0.75, 'MEOW.', 84),
         (7.3, 0.45, 'MEOW!', 70), (7.95, 0.45, 'MEOW!', 74), (8.6, 0.55, 'MEOW!!', 80),
         (11.75, 0.85, 'MEEEOOOW!!', 104)]
T_SIT = 12.55                          # she sits up
SAY = (12.85, 14.5)                    # "WHAT DO YOU WANT?!"
T_CURL = 15.95                         # in the dent: curls down
SAY2 = (16.9, 18.6)                    # "...my warm spot?!"


def meow_at(t):
    for i, (a, d, w, sz) in enumerate(MEOWS):
        if a - 0.12 <= t < a + d:
            return i, (t - a) / d, w, sz
    return None


# ------------------------------------------------------------------ the bedroom

WALL = (0.31, 0.36, 0.53)
WALL_DK = (0.29, 0.335, 0.50)
WOOD = (0.52, 0.38, 0.33)
WOOD_DK = (0.42, 0.30, 0.27)
SHEET = (0.80, 0.81, 0.88)
BLANKET = (0.36, 0.56, 0.60)
BLANKET_DK = (0.29, 0.46, 0.50)
CURTAIN = (0.55, 0.42, 0.55)
_box = K._box


def room(ctx, t):
    ctx.set_source_rgb(*WALL)
    ctx.paint()
    ctx.set_source_rgb(*WALL_DK)
    for x in range(0, W, 120):
        ctx.rectangle(x, 0, 60, FLOOR_Y)
    ctx.fill()
    # the window: night sky, stars, a crescent moon
    wx0, wy0, wx1, wy1 = 470, 360, 930, 845
    _box(ctx, wx0, wy0, wx1, wy1, (0.80, 0.78, 0.86), 8, 10)
    g = cairo.LinearGradient(0, wy0, 0, wy1)
    g.add_color_stop_rgb(0, 0.08, 0.10, 0.25)
    g.add_color_stop_rgb(1, 0.18, 0.20, 0.42)
    ctx.rectangle(wx0 + 9, wy0 + 9, wx1 - wx0 - 18, wy1 - wy0 - 18)
    ctx.set_source(g)
    ctx.fill()
    for i, (sx, sy) in enumerate(((530, 420), (640, 470), (870, 430), (560, 640), (820, 700), (900, 560),
                                  (610, 760), (750, 400))):
        tw = 0.6 + 0.4 * math.sin(t * 2.3 + i * 1.7)
        ctx.arc(sx, sy, 3.5 + 1.5 * tw, 0, 2 * math.pi)
        ctx.set_source_rgba(1, 0.97, 0.85, 0.5 + 0.5 * tw)
        ctx.fill()
    ctx.save()
    ctx.arc(805, 505, 58, 0, 2 * math.pi)
    ctx.arc_negative(780, 488, 52, 2 * math.pi, 0)
    ctx.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
    ctx.set_source_rgb(1.0, 0.95, 0.72)
    ctx.fill()
    ctx.restore()
    _box(ctx, (wx0 + wx1) / 2 - 9, wy0, (wx0 + wx1) / 2 + 9, wy1, (0.80, 0.78, 0.86), 6)
    _box(ctx, wx0, 595, wx1, 613, (0.80, 0.78, 0.86), 6)
    _box(ctx, wx0 - 30, wy1, wx1 + 30, wy1 + 28, (0.74, 0.70, 0.80), 7)       # the sill
    # curtains, tied back
    for side in (-1, 1):
        x0 = wx0 - 70 if side < 0 else wx1 + 70
        ctx.move_to(x0, 330)
        ctx.line_to(x0 + side * -120, 330)
        ctx.curve_to(x0 + side * -60, 520, x0 + side * -40, 640, x0 + side * -10, 760)
        ctx.curve_to(x0 + side * -40, 860, x0 + side * -70, 930, x0 + side * -55, 990)
        ctx.line_to(x0, 990)
        ctx.close_path()
        ctx.set_source_rgb(*CURTAIN)
        ctx.fill_preserve()
        ctx.set_source_rgb(*INK)
        ctx.set_line_width(6)
        ctx.stroke()
    _box(ctx, wx0 - 110, 318, wx1 + 110, 336, WOOD, 6, 6)                     # the rod
    # moonlight on the bed
    ctx.move_to(wx0 + 20, wy1)
    ctx.line_to(wx1 - 20, wy1)
    ctx.line_to(wx1 + 160, MAT_Y + 60)
    ctx.line_to(wx0 - 120, MAT_Y + 60)
    ctx.close_path()
    ctx.set_source_rgba(0.85, 0.88, 1.0, 0.07)
    ctx.fill()
    # floor: dark planks
    ctx.rectangle(-200, FLOOR_Y, W + 400, H - FLOOR_Y + 600)     # past the frame: the camera sees below 1920
    ctx.set_source_rgb(0.33, 0.28, 0.34)
    ctx.fill()
    ctx.set_source_rgb(0.29, 0.245, 0.30)
    for i, y in enumerate(range(FLOOR_Y + 40, H, 95)):
        ctx.rectangle(0, y, W, 6)
        for x in range(-200 + (i % 3) * 140, W, 420):
            ctx.rectangle(x, y - 95 + 40 if y > FLOOR_Y + 40 else FLOOR_Y, 5, 95)
    ctx.fill()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(7)
    ctx.move_to(0, FLOOR_Y)
    ctx.line_to(W, FLOOR_Y)
    ctx.stroke()
    # the nightstand with the clock
    _box(ctx, 12, MAT_Y - 30, 212, FLOOR_Y, WOOD, 7, 6)
    _box(ctx, 28, MAT_Y + 20, 196, MAT_Y + 110, WOOD_DK, 5, 5)
    _box(ctx, 28, MAT_Y + 128, 196, MAT_Y + 218, WOOD_DK, 5, 5)
    for y in (MAT_Y + 65, MAT_Y + 173):
        ctx.arc(112, y, 9, 0, 2 * math.pi)
        ctx.set_source_rgb(0.86, 0.74, 0.42)
        ctx.fill_preserve()
        ctx.set_source_rgb(*INK)
        ctx.set_line_width(4)
        ctx.stroke()
    clock(ctx, t)


def clock(ctx, t):
    x0, y0, x1, y1 = 22, MAT_Y - 142, 202, MAT_Y - 30
    _box(ctx, x0, y0, x1, y1, (0.20, 0.18, 0.22), 7, 16)
    _box(ctx, x0 + 14, y0 + 14, x1 - 14, y1 - 14, (0.08, 0.05, 0.06), 4, 8)
    txt, flip = CLOCK[0][1], 1.0
    for a, s in CLOCK:
        if t >= a:
            txt, flip = s, (t - a) / 0.25
    ctx.select_font_face('Consolas', cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(64)
    e = ctx.text_extents(txt)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    glow = 1.0 if flip >= 1 else 0.35 + 0.65 * ease(flip)
    ctx.save()
    ctx.rectangle(x0 + 16, y0 + 16, x1 - x0 - 32, y1 - y0 - 32)
    ctx.clip()
    dy = 0 if flip >= 1 else 40 * (1 - ease_out(flip))      # the new time rolls in from below
    ctx.move_to(cx - e.x_advance / 2, cy + e.height / 2 + dy)
    ctx.text_path(txt)
    ctx.set_source_rgba(1.0, 0.22, 0.20, glow)
    ctx.fill()
    ctx.restore()
    rg = cairo.RadialGradient(cx, cy, 10, cx, cy, 150)       # its red glow on the wall
    rg.add_color_stop_rgba(0, 1.0, 0.25, 0.2, 0.10 * glow)
    rg.add_color_stop_rgba(1, 1.0, 0.25, 0.2, 0.0)
    ctx.arc(cx, cy, 150, 0, 2 * math.pi)
    ctx.set_source(rg)
    ctx.fill()


def bed_back(ctx, t):
    """Headboard, mattress, pillow (behind her)."""
    _box(ctx, BED_X0, 995, BED_X0 + 42, FLOOR_Y, WOOD, 7, 14)                   # headboard post
    ctx.move_to(BED_X0 + 20, 1020)
    _box(ctx, BED_X0 + 30, 1040, BED_X0 + 70, MAT_Y + 10, WOOD_DK, 6, 10)
    shadow(ctx, 680, FLOOR_Y + 6, 520, 22, 0.25)
    _box(ctx, BED_X0 + 20, MAT_Y + 92, W + 40, MAT_Y + 190, WOOD, 7, 8)        # bed frame
    _box(ctx, BED_X0 + 50, MAT_Y + 190, BED_X0 + 82, FLOOR_Y, WOOD_DK, 6)      # a leg
    _box(ctx, BED_X0 + 20, MAT_Y - 6, W + 40, MAT_Y + 92, SHEET, 7, 18)        # mattress side
    # the pillow: a soft lump, dented where her head lies (the dent shows once she is up)
    k = sit_k(t)
    ctx.move_to(BED_X0 + 48, MAT_Y)
    ctx.curve_to(BED_X0 + 30, MAT_Y - 70, BED_X0 + 70, MAT_Y - 108, BED_X0 + 130, MAT_Y - 104)
    dent = 34 * k
    ctx.curve_to(BED_X0 + 200, MAT_Y - 100 + dent, BED_X0 + 270, MAT_Y - 90 + dent, BED_X0 + 330, MAT_Y - 98)
    ctx.curve_to(BED_X0 + 380, MAT_Y - 104, BED_X0 + 420, MAT_Y - 60, BED_X0 + 400, MAT_Y)
    ctx.close_path()
    ctx.set_source_rgb(0.90, 0.90, 0.95)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(7)
    ctx.stroke()
    ctx.move_to(BED_X0 + 120, MAT_Y - 30)
    ctx.curve_to(BED_X0 + 160, MAT_Y - 50, BED_X0 + 220, MAT_Y - 52, BED_X0 + 260, MAT_Y - 34)
    ctx.set_line_width(4)
    ctx.stroke()


def shadow(ctx, x, y, rx, ry, a=0.16):
    K.shadow(ctx, x, y, rx, ry, a)


# ------------------------------------------------------------------ the blanket (over her)

def _pt(G, bone, x, y):
    v = G[bone] @ np.array([x, y, 1.0])
    return GX + (v[0] - girl3.FEET[0]) * GS, MAT_Y + (v[1] - girl3.FEET[1]) * GS


def blanket(ctx, pose, k):
    G = girl3.transforms(pose)
    sh = _pt(G, 'chest', 190, 360)
    hip = _pt(G, 'hips', 160, 600)
    knee = _pt(G, 'shin_n', 130, 830)
    ankle = _pt(G, 'foot_n', 140, 1040)
    # where the blanket starts: at her shoulders lying, at her waist sitting
    ax = sh[0] + (hip[0] - 70 - sh[0]) * k
    ay = sh[1] + (hip[1] - 40 - sh[1]) * k
    top = [(ax - 12, MAT_Y + 4, 1), (ax - 30, ay + 26, 0), (ax + 10, ay - 22, 0),
           ((ax + knee[0]) / 2, min(ay, knee[1]) - 30 + 18 * k, 0),
           (knee[0], knee[1] - 44 - 16 * k, 0), (knee[0] + 70, knee[1] - 20 + 10 * k, 0),
           (ankle[0] + 30, ankle[1] - 40, 0), (ankle[0] + 120, MAT_Y - 26, 0), (W + 60, MAT_Y - 20, 1),
           (W + 60, MAT_Y + 120, 1)]
    hem = [(W + 60, MAT_Y + 120), (900, MAT_Y + 132), (760, MAT_Y + 112), (620, MAT_Y + 134), (ax + 20, MAT_Y + 116)]
    pts = top + [(x, y, 0) for x, y in hem[1:]] + [(ax - 12, MAT_Y + 100, 1)]
    cat3._smooth(ctx, pts, closed=True, tension=0.45)
    ctx.set_source_rgb(*BLANKET)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(7)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.stroke()
    # folds
    ctx.set_source_rgb(*BLANKET_DK)
    ctx.set_line_width(5)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    for fx in (ax + 60, (ax + knee[0]) / 2 + 30, knee[0] + 110):
        ctx.move_to(fx, MAT_Y - 10)
        ctx.curve_to(fx + 10, MAT_Y + 30, fx - 6, MAT_Y + 70, fx + 4, MAT_Y + 108)
    ctx.stroke()
    ctx.move_to(ax + 10, MAT_Y + 8)
    ctx.line_to(W + 60, MAT_Y + 8)
    ctx.set_line_width(4)
    ctx.set_source_rgba(*INK, 0.5)
    ctx.stroke()


# ------------------------------------------------------------------ the cat

def cat_motion(t):
    """(x, y, crouch, lean) from the perch / jump list."""
    pos = JUMPS[0][2]
    crouch, lean = 0.0, 0.0
    for a, d, p0, p1, hgt in JUMPS:
        if t < a - 0.25:
            break
        if t < a:                                   # anticipation: sink
            pos = p0
            crouch = 0.5 * ease((t - a + 0.25) / 0.25)
            lean = -6 * math.copysign(1, p1[0] - p0[0] or 1) * ease((t - a + 0.25) / 0.25)
            break
        if t < a + d:                               # in the air: an arc, stretched
            u = (t - a) / d
            top = min(p0[1], p1[1]) - hgt
            # quadratic through p0 -> apex -> p1
            x = p0[0] + (p1[0] - p0[0]) * u
            y0, y1 = p0[1], p1[1]
            ym = top
            y = (1 - u) ** 2 * y0 + 2 * u * (1 - u) * (2 * ym - (y0 + y1) / 2) + u ** 2 * y1
            crouch = -0.4 * math.sin(math.pi * u)
            lean = 14 * math.copysign(1, p1[0] - p0[0] or 1) * math.sin(math.pi * u)
            return x, y, crouch, lean
        pos = p1
        land = t - (a + d)
        crouch = 0.55 * math.exp(-land * 9) * math.cos(land * 14) if land < 0.6 else 0.0
    return pos[0], pos[1], crouch, lean


def cat_state(t):
    x, y, crouch, lean = cat_motion(t)
    mood, mouth, roll, yaw, nod, head_dy = 'deadpan', 1.0, 1.5 * math.sin(t * 1.1), 0.0, 0.0, 0.0
    look = [0.0, 0.0]
    blink = 0.0
    for b, d in ((2.5, 0.18), (4.6, 0.6), (9.2, 0.18), (14.8, 0.6)):         # 4.6, 14.8: slow stare-blinks
        if b <= t < b + d:
            blink = math.sin((t - b) / d * math.pi) ** 0.7
    ear_l = ear_r = 0.0
    if t < 3.0:                                     # on the floor: head up toward her face
        yaw, look, nod = -0.35, [-0.6, -0.7], -0.4
    elif t < 6.55:                                  # on her chest: staring down into her face
        k = ease((t - 3.7) / 0.35)
        yaw, look, nod = -0.45 * k, [-0.8 * k, 0.6 * k], 0.7 * k
        roll += 6 * k
    elif t < 9.75:                                  # on the sill: looking down at her
        yaw, look, nod = -0.5, [-0.7, 0.8], 0.6
    elif t < T_SIT:                                 # on the pillow: leans into her face
        k = ease((t - 10.6) / 0.5)
        yaw, look, nod = 0.55 * k, [0.8 * k, 0.4 * k], 0.4 * k
        lean += 10 * k
        roll -= 8 * k
    elif t < 15.6:                                  # she is up: it stares at her, then at the dent
        up = ease((t - T_SIT) / 0.3)
        yaw, look, nod = 0.45 * up, [0.7 * up, -0.8 * up], -0.5 * up
        if t >= 15.1:
            d = ease((t - 15.1) / 0.25)
            look = [0.7 - 0.1 * d, -0.8 + 1.6 * d]
            nod = -0.5 + 1.0 * d
        if T_SIT <= t < T_SIT + 0.5:
            mood = 'surprised'
    if 3.0 <= t < 3.7 or 6.55 <= t < 7.2:
        ear_l = -10 * math.sin((t * 7) % (2 * math.pi))
    if t >= T_CURL:                                 # curls up in the dent, eyes shut, purring
        c = ease((t - T_CURL) / 0.45)
        mood = 'content' if c > 0.4 else 'smug'
        crouch = max(crouch, 2.2 * c)            # a loaf
        yaw, look, nod = -0.15 * c, [0.0, 0.0], 0.3 * c
        head_dy = 40 * c
        roll = 4 * c + 2.5 * math.sin(t * 5) * c    # purring wobble
    m = meow_at(t)
    if m:
        i, u, _, _ = m
        if u < 0:
            crouch += 0.15 * ease((u * MEOWS[i][1] + 0.12) / 0.12)
        else:
            mood = 'meow'
            mouth = math.sin(min(1, u) * math.pi) ** 0.55
            crouch += 0.16 * (1 - ease(u * 3))
            roll += -7 * math.sin(min(1, u) * math.pi)
            if i == len(MEOWS) - 1:                 # the big one: leans right into her face
                lean += 6 * math.sin(min(1, u) * math.pi)
                head_dy -= 10
    breathe = math.sin(t * 2 * math.pi / 2.2)
    return x, y, dict(mood=mood, blink=blink, look=tuple(look), head_roll=roll, head_yaw=yaw, head_nod=nod,
                      head_dy=head_dy, lean=lean, breathe=breathe, crouch=crouch, ear_l=ear_l, ear_r=ear_r,
                      mouth_open=mouth)


# ------------------------------------------------------------------ the girl

def sit_k(t):
    """0 lying .. 1 sitting up (a fast jolt with a little overshoot in the lean)."""
    return ease_out((t - T_SIT) / 0.38)


def _mix_arm(a, b, k):
    return dict(sh=a.get('sh', 0) + (b.get('sh', 0) - a.get('sh', 0)) * k,
                el=a.get('el', 0) + (b.get('el', 0) - a.get('el', 0)) * k,
                wr=a.get('wr', 0) + (b.get('wr', 0) - a.get('wr', 0)) * k,
                hand=b.get('hand', 'relaxed') if k > 0.5 else a.get('hand', 'relaxed'))


SHOUT_ARMS = {'n': dict(sh=-110, el=-60, hand='open'), 'f': dict(sh=110, el=60, hand='open')}   # both up: "WHAT?!"
# lying: arms along her sides, under the blanket (the sheet's lie_back arms float above her)
LIE = dict(S['lie_back'], arm_n=dict(sh=72, el=0, hand='relaxed'), arm_f=dict(sh=70, el=0))


def girl_state(t):
    k = sit_k(t)
    st = girl3.blend(LIE, S['sit_floor'], k)
    expr, blink, look, talk = 'sleep', 0.0, (0.0, 0.0), 0.0
    head, nod = 0.0, 0.0
    breathe = math.sin(t * 2 * math.pi / 3.6)
    if t < T_SIT:
        head += 2 * breathe                          # slow sleepy breathing, head rocks a touch
    # floor meows: she frowns in her sleep, peeks, gives up
    if 2.0 <= t < 2.9:
        expr, blink = 'bored', 0.72 + 0.2 * pulse(t, 2.0, 2.9)
        look = (0.6, 0.3)
    # the cat lands on her: oof, eyes open; it stares; she shuts them tight
    if 3.55 <= t < 4.5:
        expr = 'surprised'
        head -= 4 * pulse(t, 3.55, 3.9)
        look = (0.5, -0.4)
    elif 4.5 <= t < 5.4:
        expr = 'annoyed'
        look = (0.5, -0.4)
    elif 5.4 <= t < 6.6:
        expr = 'sleep'
        head += 8 * ease((t - 5.5) / 0.25)            # turns her face away from the meow
    # the sill concert: eyes stay shut, she flinches at each meow
    if 6.6 <= t < 9.8:
        head += 8 * (1 - ease((t - 9.2) / 0.4))
        for a, d, *_ in MEOWS[4:7]:
            head -= 3 * pulse(t, a, a + 0.25)
    # the pillow: she feels it there, peeks: a cat face right at hers
    if 10.9 <= t < 11.7:
        expr, look = 'bored', (-0.8, -0.2)
        blink = 0.5 * (1 - ease((t - 10.9) / 0.3))
    elif 11.7 <= t < T_SIT:
        expr, look = 'surprised', (-0.8, -0.3)
        head -= 3 * math.sin((t - 11.7) * 40)        # the scream shakes her
    if t >= T_SIT:
        expr = 'angry'
        look = (-0.6, 0.2)
        head += -6 * (1 - ease((t - T_SIT) / 0.5))
    if SAY[0] <= t < SAY[1]:
        talk = abs(math.sin((t - SAY[0]) * math.pi * 4.2)) if t < SAY[1] - 0.4 else 0.0
        head += 3 * math.sin((t - SAY[0]) * 10)
    if SAY[1] <= t < 16.0:
        expr = 'annoyed'
        look = (-0.7, 0.5) if t >= 15.4 else (-0.6, 0.2)
    if t >= 16.0:                                    # it took her spot
        expr = 'surprised' if t < SAY2[0] else 'annoyed'
        look = (-0.8, 0.8)
        nod += 0.5 * ease((t - 16.0) / 0.3)
    if SAY2[0] <= t < SAY2[1] - 0.6:
        talk = abs(math.sin((t - SAY2[0]) * math.pi * 3.6))
    for b, d in ((14.9, 0.2), (17.9, 0.22)):
        if b <= t < b + d:
            blink = math.sin((t - b) / d * math.pi)
    # arms: up and open for the shout, back down to the blanket after
    sa = ease((t - SAY[0] + 0.15) / 0.25) * (1 - ease((t - SAY[1]) / 0.35))
    for side in ('n', 'f'):
        base = st.get('arm_' + side) or dict(girl3.ARMS_DOWN[side])
        st['arm_' + side] = _mix_arm(base, SHOUT_ARMS[side], sa)
    st['head'] = st.get('head', 0.0) + head
    st['nod'] = st.get('nod', 0.0) + nod
    pose, arms = girl3.body(st)
    # hair whips as she jolts up, then settles
    hl = 0.0
    if t >= T_SIT:
        d = t - T_SIT
        hl = 9 * math.exp(-d * 3.2) * math.sin(d * 9)
    for b, f in (('lockL', 1.0), ('lockR', 0.8), ('lockF', 0.9)):
        q = dict(pose.get(b, {}))
        q['rot'] = q.get('rot', 0.0) + hl * f
        pose[b] = q
    pose['chest'] = dict(pose.get('chest', {}), sy=1 + 0.008 * breathe)
    return pose, arms, expr, blink, look, talk, k


# ------------------------------------------------------------------ camera + frames

def camera(t):
    """(centre x, centre y, zoom)."""
    base = (480.0, 1150.0, 1.15)
    pill = (430.0, 1060.0, 1.32)
    up = (560.0, 1010.0, 1.24)
    end = (520.0, 1040.0, 1.34)
    if t < 10.0:
        a, b, k = base, base, 0.0
    elif t < T_SIT:
        a, b, k = base, pill, ease((t - 10.0) / 1.6)
    elif t < 15.4:
        a, b, k = pill, up, ease((t - T_SIT) / 0.4)
    else:
        a, b, k = up, end, ease((t - 15.4) / 1.4)
    c = [a[i] + (b[i] - a[i]) * k for i in range(3)]
    m = meow_at(t)
    if m and m[0] == len(MEOWS) - 1 and 0 <= m[1] <= 1:
        c[0] += 9 * math.sin(m[1] * 70) * (1 - m[1])
        c[1] += 6 * math.cos(m[1] * 55) * (1 - m[1])
    return c


def to_screen(x, y, cam):
    cx, cy, z = cam
    return W / 2 + (x - cx) * z, H / 2 + (y - cy) * z


def frame(t):
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(s)
    cam = camera(t)
    ctx.save()
    ctx.translate(W / 2, H / 2)
    ctx.scale(cam[2], cam[2])
    ctx.translate(-cam[0], -cam[1])
    room(ctx, t)
    bed_back(ctx, t)
    pose, arms, expr, blink, look, talk, k = girl_state(t)
    girl3.draw_girl(ctx, GX, MAT_Y, GS, pose, expr, blink, look, talk, arms=arms)
    blanket(ctx, pose, k)
    heat(ctx, t)
    cx, cy, cpose = cat_state(t)
    if cy > FLOOR_Y:
        shadow(ctx, cx, cy + 4, 95, 13, 0.25)
    cat3.draw_cat_front(ctx, cx, cy, CS, **cpose)
    # the night: everything a little bluer and dimmer (text stays bright)
    ctx.set_operator(cairo.OPERATOR_MULTIPLY)
    ctx.rectangle(-W, -H, 3 * W, 3 * H)
    ctx.set_source_rgb(0.90, 0.92, 1.0)
    ctx.fill()
    ctx.set_operator(cairo.OPERATOR_OVER)
    ctx.restore()

    m = meow_at(t)
    if m and m[1] >= 0:
        i, u, word, size = m
        hx, hy = cx, cy - 470 * CS
        off = [(150, -190), (-150, -200), (140, -230), (-190, -170),
               (-250, 60), (250, 20), (-310, -40), (210, -150)][i]
        px, py = to_screen(hx + off[0], hy + off[1], cam)
        shout(ctx, word, px, py, size * cam[2], u, rot=-0.12 if i % 2 else 0.1)
    if t < 3.2:
        K.caption(ctx, 'My cat at night:', W / 2, 190, 80, pop=min(1, t / 0.3))
    if SAY[0] <= t < SAY[1]:
        hx, hy = to_screen(GX - 30, MAT_Y - 560, cam)
        K.bubble(ctx, [('WHAT DO YOU', 92), ('WANT?!', 116)], 600, 330, (hx + 40, hy - 40),
                 (t - SAY[0]) / (SAY[1] - SAY[0]), shake=4 * math.sin(t * 60) if t < SAY[0] + 0.5 else 0)
    if t >= T_CURL + 0.35:                         # purr
        u = t - T_CURL - 0.35
        for j in range(3):
            if u * 0.7 < j / 3:                     # the next "prrr" has not started yet
                continue
            q = (u * 0.7 - j / 3) % 1.0
            px, py = to_screen(P_DENT[0] - 250 - 30 * q + 50 * (j % 2), P_DENT[1] - 200 - 140 * q, cam)
            ctx.save()
            ctx.select_font_face('Segoe Print', cairo.FONT_SLANT_ITALIC, cairo.FONT_WEIGHT_BOLD)
            ctx.set_font_size(62 * cam[2])
            ctx.move_to(px, py)
            ctx.text_path('prrr')
            ctx.set_source_rgba(*INK, (1 - q) * 0.9)
            ctx.set_line_width(9)
            ctx.stroke_preserve()
            ctx.set_source_rgba(1, 1, 1, 1 - q)
            ctx.fill()
            ctx.restore()
    if SAY2[0] <= t:
        hx, hy = to_screen(GX - 30, MAT_Y - 560, cam)
        K.bubble(ctx, [('...my warm', 84), ('spot?!', 104)], 640, 330, (hx + 40, hy - 40),
                 min(1.0, (t - SAY2[0]) / (SAY2[1] - SAY2[0])))
    s.flush()
    return s


def heat(ctx, t):
    """Warm wavy lines rising from the dent her head left, until the cat sits in it."""
    a = ease((t - T_SIT - 0.4) / 0.5) * (1 - ease((t - JUMPS[-1][0] - 0.1) / 0.3))
    if a <= 0:
        return
    ctx.save()
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    for j, dx in enumerate((-55, 0, 55)):
        ph = t * 2.2 + j * 1.3
        x0, y0 = P_DENT[0] + dx, P_DENT[1] - 40
        ctx.move_to(x0, y0)
        for s in range(1, 13):
            yy = y0 - s * 12
            ctx.line_to(x0 + 9 * math.sin(ph * 2 + s * 0.7), yy)
        ctx.set_source_rgba(1.0, 0.62, 0.35, 0.85 * a)
        ctx.set_line_width(8)
        ctx.stroke()
    ctx.restore()


def shout(ctx, word, x, y, size, u, rot):
    K.shout(ctx, word, x, y, size, u, rot)


# ------------------------------------------------------------------ outputs

STILL_TIMES = [0.4, 2.3, 3.25, 4.2, 5.7, 6.8, 8.7, 10.0, 11.3, 12.1, 12.75, 13.6, 15.2, 15.75, 16.6, 18.2]


def stills():
    from PIL import Image, ImageDraw
    tw, th = 270, 480
    cols = 8
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
        if len(sys.argv) > 2 and sys.argv[2] == 'full':
            im.save(os.path.join(ROOT, 'output', 'warm_spot_%04.1f.png' % t))
    p = os.path.join(ROOT, 'output', 'warm_spot_stills.png')
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
        video(sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, 'output', 'warm_spot_silent.mp4'))
    else:
        stills()
