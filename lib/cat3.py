"""The cat, v3: drawn in code (cairo vectors) to match the Gemini reference sheet
(characters/cat/reference_sheet_gemini.jpg) as exactly as possible, and redrawn every frame.

Front sitting model. Shapes are authored in "sit space" = the pixel grid of the sheet's
Main Sitting Pose (329 x 669, feet at y 665): the head silhouette with its three cheek spikes
a side, two separate ears, the pear-shaped body with its shoulder and haunch tufts; then the
ink lines (inner ears, brows, chest tufts, legs, toes) and the face, which is procedural:
cream eyes with a lid and a slit pupil, a pink nose, mouths per mood. Nothing here is an
image: every part can move and every expression is drawn fresh.

    draw_cat_front(ctx, x, y, scale, **pose)   # (x, y) = screen point under the paws
"""
import math

import cairo

FUR = (40 / 255, 44 / 255, 47 / 255)
INK = (24 / 255, 13 / 255, 11 / 255)
EYE = (253 / 255, 239 / 255, 194 / 255)
NOSE = (237 / 255, 164 / 255, 155 / 255)
MOUTH_IN = (150 / 255, 52 / 255, 58 / 255)
TONGUE = (230 / 255, 128 / 255, 132 / 255)
TOOTH = (250 / 255, 246 / 255, 240 / 255)
LW = 2.6                       # outline width, sit px

FEET = (163.0, 665.0)
NECK = (163.0, 282.0)          # the head pivots here
HEAD_C = (163.0, 190.0)

# ------------------------------------------------------------------ shapes (sit px)
# (x, y, corner?) - corners stay sharp (spike tips, ear tips), the rest is smoothed
HEAD = [(52, 128, 0), (53, 147, 0), (46, 166, 0), (41, 186, 1), (3, 192, 1), (16, 201, 0), (34, 212, 1),
        (4, 235, 1), (24, 237, 0), (42, 239, 1), (26, 262, 1), (64, 254, 1), (90, 269, 0), (120, 279, 0),
        (163, 284, 0), (206, 279, 0), (240, 267, 0), (262, 255, 1), (300, 262, 1), (284, 239, 1),
        (323, 236, 1), (298, 218, 0), (292, 210, 1), (325, 192, 1), (287, 188, 1), (282, 168, 0),
        (274, 147, 0), (275, 128, 0), (262, 104, 0), (228, 91, 0), (163, 86, 0), (98, 91, 0), (64, 104, 0)]
EAR_L = [(58, 138, 0), (52, 112, 0), (55, 57, 0), (63, 18, 0), (71, 4, 1), (88, 20, 0), (110, 47, 0),
         (130, 80, 0), (140, 104, 0), (100, 116, 0)]
EAR_L_PIVOT = (95.0, 100.0)
BODY = [(112, 286, 0), (106, 306, 0), (95, 326, 0), (80, 345, 1), (91, 346, 1), (83, 362, 0), (79, 380, 0),
        (77, 396, 1), (83, 398, 1), (82, 412, 0), (74, 440, 0), (70, 458, 0), (40, 491, 1), (47, 494, 1),
        (38, 510, 0), (34, 524, 1), (38, 526, 1), (36, 552, 0), (42, 577, 0), (55, 600, 0), (72, 618, 0),
        (66, 632, 0), (70, 645, 0), (84, 651, 0), (100, 650, 0), (107, 660, 0), (120, 665, 0),
        (147, 664, 0), (159, 657, 0), (164, 648, 1), (171, 658, 0), (185, 665, 0), (207, 665, 0),
        (223, 659, 0), (230, 650, 0), (246, 651, 0), (259, 645, 0), (264, 633, 0), (257, 619, 0),
        (275, 598, 0), (287, 577, 0), (292, 552, 0), (291, 526, 0), (295, 524, 1), (288, 520, 1),
        (283, 494, 0), (290, 491, 1), (282, 488, 1), (257, 458, 0), (253, 440, 0), (245, 412, 0), (246, 398, 0),
        (251, 396, 1), (246, 393, 1), (249, 380, 0), (245, 362, 0), (238, 347, 0), (248, 345, 1), (238, 343, 1), (234, 327, 0),
        (224, 308, 0), (217, 286, 0), (214, 262, 0), (163, 250, 0), (113, 262, 0)]
# ink lines inside the body (sit px), each a polyline
BODY_INK = [
    [(84, 416), (90, 455), (101, 520), (113, 584), (121, 620)],          # left front leg, outer
    [(244, 416), (238, 455), (227, 520), (215, 584), (208, 620)],        # right front leg, outer
    [(156, 484), (158, 560), (161, 648)],                                 # between the front legs
    [(172, 484), (170, 560), (166, 648)],
    [(138, 460), (148, 474), (156, 486)], [(196, 448), (184, 470), (172, 486)],   # chest tufts
    [(123, 424), (127, 440), (131, 454)], [(130, 445), (134, 458)],
    [(102, 652), (104, 640), (112, 630), (122, 622)],                     # front paw tops
    [(226, 652), (224, 640), (216, 630), (207, 622)],
    [(124, 646), (124, 662)], [(141, 646), (142, 663)], [(186, 646), (186, 663)], [(203, 646), (203, 662)],
    [(81, 628), (82, 648)], [(93, 630), (94, 650)], [(237, 630), (236, 650)], [(249, 628), (248, 648)],
    [(72, 618), (90, 612), (103, 618)], [(256, 619), (238, 612), (225, 618)],    # back paws
]
HEAD_INK = [
    [(71, 127), (80, 113), (100, 101)], [(255, 127), (246, 113), (226, 101)],    # brows
]
EAR_INK_L = [[(72, 14), (86, 48), (99, 84)], [(96, 90), (110, 97)], [(99, 84), (113, 88)]]

EYE_L = (104.0, 196.0)        # eye-ball centres; ball half-size
EYE_R = (221.0, 196.0)
EYE_RX, EYE_RY = 39.0, 32.0

# expression presets: lid = how far the upper lid comes down (0 open .. 1 shut), slant =
# lid tilt (+ = inner corner lower: cross), pupil = slit width, mouth shape
MOODS = {
    'deadpan':   dict(lid=0.22, slant=0.75, pupil=0.08, mouth='frown'),
    'smug':      dict(lid=0.45, slant=0.45, pupil=0.08, mouth='smirk', brow_lift=0.3),
    'surprised': dict(lid=-0.12, slant=0.0, pupil=0.10, mouth='o', eye_scale=1.18, ears_up=1),
    'sleepy':    dict(lid=0.66, slant=-0.25, pupil=0.08, mouth='small', ears_flat=1.25),
    'angry':     dict(lid=0.34, slant=1.7, pupil=0.08, mouth='frown', ears_flat=0.55, spiky=1),
    'silly':     dict(lid=-0.1, slant=0.0, pupil=0.20, round_pupil=1, mouth='tongue', eye_scale=1.12,
                      look_split=1),
    'confused':  dict(lid=0.10, slant=0.0, pupil=0.08, mouth='wavy', asym=1, ear_droop=1),
    'meow':      dict(closed=1, mouth='meow', ears_flat=1.1, jaw=1),
    'content':   dict(closed=1, mouth='smirk'),                 # eyes shut ^ ^, purring
    'spooked':   dict(lid=-0.2, slant=-0.3, pupil=0.10, round_pupil=1, pupil_r=0.42, mouth='o', eye_scale=1.3,
                      ears_flat=0.7, spiky=1),                  # scared: huge round pupils, ears back
    'groom':     dict(closed=1, mouth='tongue'),                # eyes shut, tongue out: washing itself
}


# ------------------------------------------------------------------ path helpers

def _smooth(ctx, pts, closed=True, tension=0.5):
    """Catmull-Rom through pts; points flagged as corners stay sharp."""
    n = len(pts)
    P = [(p[0], p[1]) for p in pts]
    C = [bool(p[2]) if len(p) > 2 else False for p in pts]

    def tang(i):
        if C[i % n]:
            return (0.0, 0.0)
        a, b = P[(i - 1) % n], P[(i + 1) % n]
        if not closed and (i == 0 or i == n - 1):
            return (0.0, 0.0)
        return ((b[0] - a[0]) * tension / 2 * 0.66, (b[1] - a[1]) * tension / 2 * 0.66)
    ctx.move_to(*P[0])
    m = n if closed else n - 1
    for i in range(m):
        a, b = P[i], P[(i + 1) % n]
        ta, tb = tang(i), tang(i + 1)
        ctx.curve_to(a[0] + ta[0], a[1] + ta[1], b[0] - tb[0], b[1] - tb[1], b[0], b[1])
    if closed:
        ctx.close_path()


def _stroke_line(ctx, pts, w, color=INK):
    ctx.save()
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.set_line_width(w)
    ctx.set_source_rgb(*color)
    _smooth(ctx, [(p[0], p[1], 0) for p in pts], closed=False)
    ctx.stroke()
    ctx.restore()


def _tapered(ctx, pts, w, color=INK):
    """An ink stroke that thins toward both ends (brush line)."""
    n = len(pts)
    if n < 2:
        return
    # resample
    seg = []
    for i in range(n - 1):
        a, b = pts[i], pts[i + 1]
        k = max(2, int(math.hypot(b[0] - a[0], b[1] - a[1]) / 3))
        for j in range(k):
            u = j / k
            seg.append((a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u))
    seg.append(pts[-1])
    L, R = [], []
    m = len(seg)
    for i, p in enumerate(seg):
        q0, q1 = seg[max(0, i - 1)], seg[min(m - 1, i + 1)]
        dx, dy = q1[0] - q0[0], q1[1] - q0[1]
        d = math.hypot(dx, dy) or 1
        u = i / (m - 1)
        hw = w / 2 * (0.25 + 0.75 * math.sin(math.pi * min(1, max(0, u))) ** 0.6)
        L.append((p[0] - dy / d * hw, p[1] + dx / d * hw))
        R.append((p[0] + dy / d * hw, p[1] - dx / d * hw))
    ctx.save()
    ctx.set_source_rgb(*color)
    ctx.move_to(*L[0])
    for p in L[1:]:
        ctx.line_to(*p)
    for p in reversed(R):
        ctx.line_to(*p)
    ctx.close_path()
    ctx.fill()
    ctx.restore()


def _xf(pts, fn):
    return [(*fn(p[0], p[1]), p[2] if len(p) > 2 else 0) for p in pts]


def _rot(px, py, deg, x, y):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    dx, dy = x - px, y - py
    return px + dx * c - dy * s, py + dx * s + dy * c


# ------------------------------------------------------------------ the face

def _eye(ctx, cx, cy, side, m, look, blink, k_scale):
    """One eye at (cx, cy). side -1 = viewer's left. Drawn: cream ball clipped by the lid,
    an ink outline heavier on the lid, a slit pupil."""
    s = m.get('eye_scale', 1.0) * k_scale
    rx, ry = EYE_RX * s, EYE_RY * s
    if m.get('asym') and side > 0:
        rx, ry = rx * 1.12, ry * 1.2
    lid = m.get('lid', 0.3)
    if m.get('asym') and side < 0:
        lid += 0.42
    lid = lid + (1 - lid) * blink
    if m.get('closed') or lid >= 0.97:
        # closed: a curved lash arc (happy ^ for meow, a flat line for sleepy)
        ctx.save()
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.set_line_width(3.2)
        ctx.set_source_rgb(*INK)
        if m.get('closed'):
            ctx.move_to(cx - rx * 0.75, cy + 4)
            ctx.curve_to(cx - rx * 0.3, cy - 9, cx + rx * 0.3, cy - 9, cx + rx * 0.75, cy + 4)
        else:
            ctx.move_to(cx - rx * 0.8, cy + ry * 0.35)
            ctx.curve_to(cx - rx * 0.3, cy + ry * 0.62, cx + rx * 0.3, cy + ry * 0.62, cx + rx * 0.8, cy + ry * 0.35)
        ctx.stroke()
        ctx.restore()
        return
    slant = (m.get('slant', 0.0) + (0.9 if (m.get('asym') and side < 0) else 0)) * (-side)
    ctx.save()
    # the eye ball: a rounded shape, fuller at the bottom
    def ball():
        # round at the bottom, squarer at the top (the lid line crosses the full width)
        ctx.new_path()
        n = 48
        for i in range(n + 1):
            t = 2 * math.pi * i / n
            c, sn = math.cos(t), math.sin(t)
            e = 2.0 if sn > 0 else 3.6
            X = math.copysign(abs(c) ** (2 / e), c)
            Y = math.copysign(abs(sn) ** (2 / e), sn)
            (ctx.move_to if i == 0 else ctx.line_to)(cx + rx * X, cy + ry * Y)
        ctx.close_path()

    def lid_path():
        # everything above the lid line (in eye-local coords)
        top = -ry * 1.4
        ly = -ry + 2 * ry * max(-0.2, lid)
        ctx.new_path()
        ctx.move_to(cx - rx * 1.3, top)
        ctx.line_to(cx + rx * 1.3, top)
        ctx.line_to(cx + rx * 1.3, cy + ly + slant * ry * 0.45)
        ctx.line_to(cx - rx * 1.3, cy + ly - slant * ry * 0.45)
        ctx.close_path()

    # fill the visible part of the eye (ball minus lid)
    ball()
    ctx.clip()
    ctx.set_source_rgb(*EYE)
    ctx.paint()
    # pupil: a vertical slit (or round for silly)
    lx, ly = look
    if m.get('look_split'):
        lx = 0.35 * side
    px = cx + rx * 0.21 * (-side) + lx * rx * 0.35
    lid_y = cy - ry + 2 * ry * max(-0.2, lid) + slant * ry * 0.45 * (px - cx) / (rx * 1.3)
    py = max(lid_y, cy - ry * 0.9) + ry * 0.40 - 3 + ly * ry * 0.25
    ctx.set_source_rgb(*INK)
    if m.get('round_pupil'):
        ctx.arc(px, py + 2, rx * m.get('pupil_r', 0.2), 0, 2 * math.pi)
        ctx.fill()
    else:
        pw, ph = rx * m.get('pupil', 0.08) * 1.25, ry * 0.44
        ctx.move_to(px, py - ph)
        ctx.curve_to(px + pw, py - ph * 0.4, px + pw, py + ph * 0.4, px, py + ph)
        ctx.curve_to(px - pw, py + ph * 0.4, px - pw, py - ph * 0.4, px, py - ph)
        ctx.fill()
    # the lid (fur) over the eye
    lid_path()
    ctx.set_source_rgb(*FUR)
    ctx.fill()
    ctx.restore()
    # outline: the ball's visible rim (below the lid), heavy along the lid
    ctx.save()
    ly0 = -ry + 2 * ry * max(-0.2, lid)
    ctx.new_path()
    ctx.move_to(cx - rx * 1.4, cy + ly0 - slant * ry * 0.45)
    ctx.line_to(cx + rx * 1.4, cy + ly0 + slant * ry * 0.45)
    ctx.line_to(cx + rx * 1.4, cy + ry * 1.5)
    ctx.line_to(cx - rx * 1.4, cy + ry * 1.5)
    ctx.close_path()
    ctx.clip()
    ball()
    ctx.set_line_width(3.0)
    ctx.set_source_rgb(*INK)
    ctx.stroke()
    ctx.restore()
    ctx.save()
    ball()
    ctx.clip()
    ly = -ry + 2 * ry * max(-0.2, lid)
    ctx.move_to(cx - rx * 1.3, cy + ly - slant * ry * 0.45)
    ctx.line_to(cx + rx * 1.3, cy + ly + slant * ry * 0.45)
    ctx.set_line_width(5.0)
    ctx.set_source_rgb(*INK)
    ctx.stroke()
    ctx.restore()
    # hide the cream fringe the clip leaves along the ball above the lid
    ctx.save()
    ctx.new_path()
    ctx.move_to(cx - rx * 1.4, cy + ly0 - slant * ry * 0.45)
    ctx.line_to(cx + rx * 1.4, cy + ly0 + slant * ry * 0.45)
    ctx.line_to(cx + rx * 1.4, cy - ry * 1.6)
    ctx.line_to(cx - rx * 1.4, cy - ry * 1.6)
    ctx.close_path()
    ctx.clip()
    ball()
    ctx.set_line_width(2.4)
    ctx.set_source_rgb(*FUR)
    ctx.stroke()
    ctx.restore()
    # the lid line runs a little past the eye at the outer corner (as drawn on the sheet)
    if False:
        ctx.save()
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.set_line_width(3.0)
        ctx.set_source_rgb(*INK)
        ox = cx + rx * 1.02 * side
        oy = cy + ly + slant * ry * 0.45 * side * (1 if side > 0 else -1) * (-1 if side < 0 else 1)
        oy = cy + ly + (slant * ry * 0.45 if side > 0 else -slant * ry * 0.45)
        ctx.move_to(ox - side * 6, oy)
        ctx.line_to(ox + side * 4, oy - 1)
        ctx.stroke()
        ctx.restore()


def _nose(ctx, x, y, k=1.0):
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(k, k)
    ctx.move_to(-9, -4)
    ctx.curve_to(-9, -7, 9, -7, 9, -4)
    ctx.curve_to(8, 0, 2, 6, 0, 7)
    ctx.curve_to(-2, 6, -8, 0, -9, -4)
    ctx.close_path()
    ctx.set_source_rgb(*NOSE)
    ctx.fill_preserve()
    ctx.set_line_width(1.6)
    ctx.set_source_rgb(*INK)
    ctx.stroke()
    ctx.restore()


def _mouth(ctx, x, y, shape, open_k=1.0):
    """(x, y) = just under the nose."""
    ctx.save()
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    pinkline = (0.80, 0.55, 0.52)

    def line(pts, w=2.4, col=INK):
        ctx.set_line_width(w)
        ctx.set_source_rgb(*col)
        _smooth(ctx, [(p[0] + x, p[1] + y, 0) for p in pts], closed=False)
        ctx.stroke()
    if shape == 'frown':                     # the sheet's deadpan "^"
        for col, w in ((INK, 4.2), (pinkline, 2.0)):
            line([(0, 0), (0, 3)], w, col)
            line([(0, 4), (-7, 9), (-13, 15)], w, col)
            line([(0, 4), (7, 9), (13, 15)], w, col)
    elif shape == 'smirk':                   # a little "w" with a curl at one end
        for col, w in ((INK, 4.0), (pinkline, 1.8)):
            line([(0, 0), (0, 4)], w, col)
            line([(0, 4), (-5, 9), (-11, 7)], w, col)
            line([(0, 4), (6, 9), (13, 6), (16, 2)], w, col)
    elif shape == 'small':
        for col, w in ((INK, 4.0), (pinkline, 1.8)):
            line([(0, 0), (0, 3)], w, col)
            line([(-6, 7), (0, 4), (6, 7)], w, col)
    elif shape == 'wavy':
        for col, w in ((INK, 4.0), (pinkline, 1.8)):
            line([(-10, 10), (-4, 7), (2, 11), (9, 8)], w, col)
    elif shape in ('o', 'meow', 'tongue'):
        if shape == 'o':
            w, h = 8 * open_k, 10 * open_k
            cy = y + 9 + h / 2
        elif shape == 'meow':
            w, h = 36 * open_k, 33 * open_k
            cy = y + 4 + h
        else:
            w, h = 0, 0
            cy = y + 8
        if shape == 'tongue':
            for col, wd in ((INK, 4.0), (pinkline, 1.8)):
                line([(-10, 6), (0, 9), (10, 6)], wd, col)
            ctx.move_to(x - 10, y + 8)
            ctx.curve_to(x - 12, y + 36, x + 12, y + 36, x + 10, y + 8)
            ctx.close_path()
            ctx.set_source_rgb(*TONGUE)
            ctx.fill_preserve()
            ctx.set_line_width(2.0)
            ctx.set_source_rgb(*INK)
            ctx.stroke()
            ctx.move_to(x, y + 12)
            ctx.line_to(x, y + 24)
            ctx.set_line_width(1.2)
            ctx.stroke()
        else:
            ctx.save()
            ctx.translate(x, cy)
            ctx.scale(max(1, w), max(1, h))
            ctx.arc(0, 0, 1, 0, 2 * math.pi)
            ctx.restore()
            ctx.set_source_rgb(*MOUTH_IN)
            ctx.fill_preserve()
            ctx.set_line_width(2.6)
            ctx.set_source_rgb(*INK)
            ctx.stroke()
            if shape == 'meow' and h > 8:
                # tongue at the bottom, two fangs at the top
                ctx.save()
                ctx.translate(x, cy)
                ctx.scale(w, h)
                ctx.arc(0, 0, 0.97, 0, 2 * math.pi)
                ctx.restore()
                ctx.clip()
                ctx.save()
                ctx.translate(x, cy + h * 0.75)
                ctx.scale(w * 0.75, h * 0.55)
                ctx.arc(0, 0, 1, 0, 2 * math.pi)
                ctx.restore()
                ctx.set_source_rgb(*TONGUE)
                ctx.fill()
                for sx in (-1, 1):
                    fx = x + sx * w * 0.55
                    fy = cy - h * 0.70
                    ctx.move_to(fx - 4, fy - 4)
                    ctx.line_to(fx + 4, fy - 4)
                    ctx.line_to(fx + sx * 1.0, fy + 9 * open_k)
                    ctx.close_path()
                    ctx.set_source_rgb(*TOOTH)
                    ctx.fill_preserve()
                    ctx.set_line_width(1.0)
                    ctx.set_source_rgb(*INK)
                    ctx.stroke()
                ctx.reset_clip()
    ctx.restore()


# ------------------------------------------------------------------ the whole cat

def draw_cat_front(ctx, x, y, scale, mood='deadpan', blink=0.0, look=(0.0, 0.0), head_roll=0.0,
                   head_yaw=0.0, head_nod=0.0, head_dy=0.0, lean=0.0, breathe=0.0, crouch=0.0,
                   ear_l=0.0, ear_r=0.0, mouth_open=1.0, meow=None):
    """Draw the sitting cat (front view). Angles in degrees; yaw/nod -1..1; crouch 0..1
    (squash down); breathe -1..1. mood: a key of MOODS (meow = the loud open-mouth meow)."""
    m = dict(MOODS.get(mood, MOODS['deadpan']))
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(scale, scale)
    ctx.translate(-FEET[0], -FEET[1])
    # whole body: lean about the feet, squash for crouch, breathe the chest
    sy = (1 - 0.16 * crouch) * (1 + 0.010 * breathe)
    sx = (1 + 0.07 * crouch) * (1 + 0.006 * breathe)

    def body_xf(px, py):
        px, py = FEET[0] + (px - FEET[0]) * sx, FEET[1] + (py - FEET[1]) * sy
        return _rot(FEET[0], FEET[1], lean, px, py)
    neck = body_xf(*NECK)
    hx, hy = neck[0] - NECK[0], neck[1] - NECK[1] + head_dy

    yaw = max(-1.0, min(1.0, head_yaw))

    def head_xf(px, py, feature=0.0):
        """Head space -> sit space: yaw shifts features more than the silhouette."""
        dx = px - HEAD_C[0]
        if feature:
            px = px + yaw * 20 * feature * (1 - min(1, abs(dx) / 160))
            py = py + head_nod * 10 * feature
        else:
            px = HEAD_C[0] + dx * (1 - 0.10 * abs(yaw) * (1 if dx * yaw < 0 else 0.3)) + yaw * 7
        px, py = _rot(NECK[0], NECK[1], head_roll + lean, px, py)
        return px + hx, py + hy

    ears_flat = m.get('ears_flat', 0.0)
    ears_up = m.get('ears_up', 0)

    def ear_pts(side):
        pts = EAR_L if side < 0 else [(2 * HEAD_C[0] - p[0], p[1], p[2]) for p in reversed(EAR_L)]
        piv = EAR_L_PIVOT if side < 0 else (2 * HEAD_C[0] - EAR_L_PIVOT[0], EAR_L_PIVOT[1])
        a = (ear_l if side < 0 else ear_r) + side * 62 * ears_flat - side * 4 * ears_up
        if m.get('ear_droop') and side < 0:
            a -= 28
        out = []
        for p in pts:
            px, py = _rot(piv[0], piv[1], a, p[0], p[1])
            if ears_flat:                       # flattened ears also shorten
                py = piv[1] + (py - piv[1]) * (1 - 0.3 * ears_flat)
            out.append((px + yaw * 6, py - 3 * ears_up, p[2]))
        return out, piv, a

    # ---- silhouettes: stroke everything twice as wide, then fill: outlines only on the union
    body = _xf(BODY, body_xf)
    ears = [ear_pts(-1), ear_pts(1)]
    jaw = m.get('jaw', 0) * mouth_open
    jaw_head = [(p[0], p[1] + jaw * 26 * max(0.0, min(1.0, (p[1] - 215) / 60)), p[2]) for p in HEAD]
    head = _xf(jaw_head, lambda a, b: head_xf(a, b))
    if m.get('spiky'):                          # angry: a few spikes on the head top
        top = [(120, 88, 0), (128, 74, 1), (136, 87, 0), (150, 86, 0), (158, 70, 1), (166, 86, 0),
               (180, 87, 0), (190, 74, 1), (198, 89, 0)]
        i = [k for k, p in enumerate(HEAD) if p[1] == 86][0]
        head = _xf(HEAD[:i] + list(reversed(top)) + HEAD[i + 1:], lambda a, b: head_xf(a, b))
    ears_t = [(_xf(e[0], lambda a, b: head_xf(a, b)), e) for e in ears]
    for pts in [body]:
        _smooth(ctx, pts)
        ctx.set_source_rgb(*INK)
        ctx.set_line_width(LW * 2)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.stroke_preserve()
        ctx.set_source_rgb(*FUR)
        ctx.fill()
    for pts in [head] + [e[0] for e in ears_t]:
        _smooth(ctx, pts)
        ctx.set_source_rgb(*INK)
        ctx.set_line_width(LW * 2)
        ctx.stroke()
    for pts in [head] + [e[0] for e in ears_t]:
        _smooth(ctx, pts)
        ctx.set_source_rgb(*FUR)
        ctx.fill()

    # ---- ink inside
    for line in BODY_INK:
        _tapered(ctx, [body_xf(*p) for p in line], 3.8)
    for (pts, (raw, piv, a)) in ears_t:
        side = -1 if raw[0][0] < HEAD_C[0] else 1
        for line in EAR_INK_L:
            q = []
            for p in line:
                px, py = (p if side < 0 else (2 * HEAD_C[0] - p[0], p[1]))
                px, py = _rot(piv[0], piv[1], a, px, py)
                if ears_flat:
                    py = piv[1] + (py - piv[1]) * (1 - 0.3 * ears_flat)
                q.append(head_xf(px + yaw * 6, py - 3 * ears_up))
            _tapered(ctx, q, 3.0)
    brow = m.get('brow_lift', 0.0)
    for k, line in enumerate(HEAD_INK):
        side = -1 if k == 0 else 1
        lift = brow * 8 if side > 0 else 0
        if m.get('asym') and side > 0:
            lift = 10
        _tapered(ctx, [head_xf(p[0], p[1] - lift, 0.5) for p in line], 3.0)

    # ---- face (drawn in head space, with the head's transform)
    ctx.save()
    # map head space to sit space: translate/rotate like head_xf (features ride the yaw)
    nx, ny = head_xf(*NECK)
    ctx.translate(nx, ny)
    ctx.rotate(math.radians(head_roll + lean))
    ctx.translate(-NECK[0] + yaw * 16, -NECK[1] + head_nod * 10)
    k_scale = 1.0
    for side, (ex, ey) in ((-1, EYE_L), (1, EYE_R)):
        # the eye on the far side of a turned head narrows
        ctx.save()
        squeeze = 1 - 0.22 * max(0, -yaw * side) + 0.05 * max(0, yaw * side)
        ctx.translate(ex, ey)
        ctx.scale(squeeze, 1)
        ctx.translate(-ex, -ey)
        _eye(ctx, ex, ey, side, m, look, blink if mood != 'meow' else 0, k_scale)
        ctx.restore()
    _nose(ctx, 164, 225)
    _mouth(ctx, 164, 233, m.get('mouth', 'frown'), mouth_open)
    if mood == 'angry':                         # little anger lines by the brow
        _tapered(ctx, [(250, 120), (262, 112)], 2.2)
    ctx.restore()
    ctx.restore()
