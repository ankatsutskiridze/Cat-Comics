"""The girl, v3: drawn in code (cairo vectors) after the master sheet (characters/girl/
girl_master_red.png, its big standing figure = characters/rig/girl_src.png), as exactly as
possible, and redrawn every frame.

HEAD (this file, first part): shapes authored in "src space" = the big figure's pixel grid
(304 x 1187, feet at y 1180), measured off it: the hair silhouette (back hair, long locks, the
lock over the chest), the fringe that falls over the forehead (drawn over the eyes), the face,
ear and neck, the hair's shine and shadow shapes and strand lines; then the procedural face
(big dark eyes with lashes and highlights, brows, nose, mouth per expression, blush).

    draw_head(ctx, expr='smile', blink=0, look=(0, 0), talk=0, ...) in src space
"""
import math

import cairo

INK = (38 / 255, 14 / 255, 10 / 255)
HAIR = (178 / 255, 10 / 255, 4 / 255)
HAIR_DK = (125 / 255, 5 / 255, 2 / 255)
HAIR_LT = (214 / 255, 100 / 255, 84 / 255)
HAIR_LINE = (98 / 255, 6 / 255, 3 / 255)
SKIN = (248 / 255, 210 / 255, 186 / 255)
SKIN_SH = (232 / 255, 176 / 255, 156 / 255)
BLUSH = (240 / 255, 150 / 255, 140 / 255)
EAR_IN_COL = (225 / 255, 150 / 255, 140 / 255)
WHITE = (250 / 255, 247 / 255, 245 / 255)
IRIS = (58 / 255, 52 / 255, 60 / 255)
IRIS_LO = (122 / 255, 120 / 255, 132 / 255)
PUPIL = (26 / 255, 18 / 255, 20 / 255)
LASH = (28 / 255, 16 / 255, 14 / 255)
BROW = (104 / 255, 52 / 255, 40 / 255)
MOUTH = (150 / 255, 58 / 255, 58 / 255)
TONGUE = (226 / 255, 120 / 255, 120 / 255)
TEETH = (252 / 255, 250 / 255, 248 / 255)

NECK_PIVOT = (180.0, 262.0)

# ------------------------------------------------------------------ shapes (src px)
# hair silhouette, behind the face (outer contour of the master's hair, the face cut out)
HAIR_BACK = [(208, 12), (186, 6), (163, 5), (143, 9), (121, 10), (105, 15), (79, 30), (65, 44), (55, 58),
             (46, 77), (40, 96), (36, 122), (32, 259), (26, 331), (5, 476), (7, 500), (11, 510), (16, 514),
             (13, 489), (19, 486), (28, 508), (36, 517), (52, 523), (61, 519), (69, 523), (83, 520), (80, 479),
             (81, 429), (54, 415), (49, 406), (84, 301), (89, 291), (99, 281), (107, 277), (121, 274),
             (126, 278), (142, 323), (144, 339), (143, 372), (138, 395), (130, 407), (138, 405), (144, 408),
             (140, 434), (135, 445), (144, 442), (153, 431), (157, 431), (161, 439), (165, 440), (164, 429),
             (172, 406), (176, 385), (176, 346), (168, 297), (157, 263), (160, 238), (200, 238), (197, 263),
             (208, 267), (218, 277), (247, 291), (255, 299), (261, 312), (274, 424), (262, 430), (259, 434),
             (257, 467), (262, 472), (268, 471), (276, 463), (285, 444), (291, 447), (289, 461), (293, 457),
             (297, 441), (298, 414), (289, 335), (282, 239), (281, 171), (283, 136), (280, 111), (267, 66),
             (259, 53), (238, 30)]
# the fringe + the side hair framing the face: its lower edge is the jagged line over the face
FRINGE_EDGE = [(112, 176), (119, 170), (129, 159), (136, 157),
               (151, 137), (159, 131), (168, 129), (172, 132), (173, 144), (171, 151), (175, 155), (180, 154),
               (187, 141), (191, 141), (193, 144), (191, 156), (194, 157), (205, 139), (213, 140), (218, 118),
               (231, 111), (236, 112), (245, 119), (252, 120), (257, 125), (259, 140), (267, 148), (266, 162),
               (260, 170), (259, 188), (251, 201), (238, 214)]
FRINGE_TOP = [(270, 210), (280, 150), (272, 92), (240, 54), (180, 44), (126, 52), (96, 84), (90, 130), (100, 168)]
# the lock over the chest, in front of the neck and the shirt
FRONT_LOCK = [(118, 214), (128, 222), (142, 236), (152, 262), (166, 300), (176, 346), (176, 385), (172, 406),
              (164, 429), (165, 440), (161, 439), (157, 431), (153, 431), (144, 442), (135, 445), (140, 434),
              (144, 408), (138, 405), (130, 407), (138, 395), (143, 372), (144, 339), (142, 323), (126, 278),
              (112, 236)]
FACE = [(116, 172), (128, 140), (160, 112), (205, 100), (245, 110), (265, 135), (266, 158), (262, 176), (254, 194),
        (238, 211), (215, 225), (194, 231), (172, 230), (150, 225), (132, 218), (120, 206)]
NECK = [(160, 214), (198, 220), (197, 272), (160, 272)]
NECK_SHADOW = [(160, 224), (184, 232), (198, 232), (197, 252), (182, 246), (166, 240), (160, 236)]
EAR = [(117, 190), (110, 183), (100, 182), (92, 187), (88, 197), (90, 208), (96, 216), (106, 222), (118, 224),
       (126, 220), (124, 205)]
EAR_IN = [(102, 192), (96, 197), (97, 207), (104, 214), (112, 215), (108, 206), (110, 197)]
# shine on the crown
SHINE = [
    [(32, 116), (36, 96), (46, 78), (56, 70), (66, 64), (78, 58), (92, 56), (96, 62), (88, 66), (90, 74), (80, 72),
     (76, 80), (68, 76), (62, 86), (56, 82), (50, 96), (44, 92), (38, 112)],
    [(214, 44), (228, 34), (242, 34), (256, 44), (266, 62), (270, 82), (262, 74), (258, 80), (252, 66), (246, 70),
     (240, 58), (232, 62), (226, 52), (218, 54)],
    [(120, 50), (134, 42), (150, 41), (146, 47), (138, 46), (132, 52), (126, 50)],
]
# hair shadow: behind the neck, inside the left lock
SHADE = [
    [(198, 238), (230, 244), (256, 262), (262, 300), (250, 292), (220, 280), (200, 268)],
    [(84, 236), (108, 226), (118, 250), (112, 280), (96, 286), (86, 300), (80, 270)],
    [(36, 300), (44, 230), (52, 300), (40, 420), (30, 430)],
]
# strand lines (each a polyline, drawn thin in deep red)
STRANDS = [
    [(150, 40), (140, 80), (130, 120), (124, 150)], [(176, 40), (174, 90), (170, 128)],
    [(196, 46), (200, 90), (204, 136)], [(222, 60), (226, 90), (232, 110)],
    [(118, 60), (100, 100), (92, 150), (90, 182)], [(70, 110), (62, 200), (58, 300), (46, 410)],
    [(52, 160), (46, 260), (36, 360), (20, 470)], [(88, 300), (76, 380), (64, 470)],
    [(266, 150), (272, 260), (282, 380), (290, 440)], [(250, 120), (260, 200)],
    [(150, 300), (160, 360), (160, 420)], [(134, 290), (150, 380)],
]


# ------------------------------------------------------------------ path helpers

def _path(ctx, pts, closed=True, tension=0.5):
    n = len(pts)
    P = [(p[0], p[1]) for p in pts]

    def tang(i):
        if not closed and (i <= 0 or i >= n - 1):
            return (0.0, 0.0)
        a, b = P[(i - 1) % n], P[(i + 1) % n]
        return ((b[0] - a[0]) * tension / 3, (b[1] - a[1]) * tension / 3)
    ctx.move_to(*P[0])
    for i in range(n if closed else n - 1):
        a, b = P[i], P[(i + 1) % n]
        ta, tb = tang(i), tang(i + 1)
        ctx.curve_to(a[0] + ta[0], a[1] + ta[1], b[0] - tb[0], b[1] - tb[1], b[0], b[1])
    if closed:
        ctx.close_path()


def _fill(ctx, pts, col, outline=None, lw=2.4, tension=0.5):
    _path(ctx, pts, True, tension)
    ctx.set_source_rgb(*col)
    if outline:
        ctx.fill_preserve()
        ctx.set_source_rgb(*outline)
        ctx.set_line_width(lw)
        ctx.stroke()
    else:
        ctx.fill()


def _line(ctx, pts, col, w, tension=0.5):
    ctx.save()
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    _path(ctx, pts, False, tension)
    ctx.set_source_rgb(*col)
    ctx.set_line_width(w)
    ctx.stroke()
    ctx.restore()


def _taper(ctx, pts, w, col, start=0.3, end=0.3):
    """A brush stroke thinning toward its ends."""
    seg = []
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        k = max(2, int(math.hypot(b[0] - a[0], b[1] - a[1]) / 2))
        for j in range(k):
            u = j / k
            seg.append((a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u))
    seg.append(pts[-1])
    m = len(seg)
    L, R = [], []
    for i, p in enumerate(seg):
        q0, q1 = seg[max(0, i - 1)], seg[min(m - 1, i + 1)]
        dx, dy = q1[0] - q0[0], q1[1] - q0[1]
        d = math.hypot(dx, dy) or 1
        u = i / (m - 1)
        k = min(1.0, u / start if start else 1.0, (1 - u) / end if end else 1.0)
        hw = w / 2 * (0.15 + 0.85 * max(0.0, k))
        L.append((p[0] - dy / d * hw, p[1] + dx / d * hw))
        R.append((p[0] + dy / d * hw, p[1] - dx / d * hw))
    ctx.move_to(*L[0])
    for p in L[1:]:
        ctx.line_to(*p)
    for p in reversed(R):
        ctx.line_to(*p)
    ctx.close_path()
    ctx.set_source_rgb(*col)
    ctx.fill()


# ------------------------------------------------------------------ the face

# eyes (src px), measured: near eye (viewer's left) and far eye
EYE_N = dict(c=(171.0, 178.0), w=(122, 188), lash=[(121, 178), (127, 171), (140, 164), (157, 159), (174, 157),
             (187, 160)], low=[(136, 187), (152, 192), (170, 192), (183, 186)], iris_r=15.0, flick=-1)
EYE_F = dict(c=(243.0, 153.0), w=(216, 260), lash=[(215, 155), (225, 147), (237, 141), (249, 137), (260, 134)],
             low=[(225, 166), (238, 169), (252, 165)], iris_r=12.5, flick=1)
EXPR = {
    'smile':     dict(open=1.0, mouth='smile'),
    'neutral':   dict(open=1.0, mouth='flat'),
    'talk':      dict(open=1.0, mouth='talk'),
    'happy':     dict(closed='happy', mouth='laugh', blush=1.4),
    'bored':     dict(open=0.55, mouth='flat'),
    'annoyed':   dict(open=0.5, mouth='frown', brow=-1),
    'angry':     dict(open=0.7, mouth='shout', brow=-2),
    'surprised': dict(open=1.15, mouth='o', iris=0.8, brow=1.5),
    'sleep':     dict(closed='sleep', mouth='flat'),
    'tired':     dict(open=0.45, mouth='flat', bags=1),
}


def _eye(ctx, E, e, blink, look):
    """One eye. open = lid opening 0..1.15; the lid comes down from the lash line."""
    op = e.get('open', 1.0) * (1 - blink)
    lash = E['lash']
    low = E['low']
    x0, x1 = E['w']
    cx, cy = E['c']
    if e.get('closed') or op < 0.12:
        # a closed eye: the lash line curves down (sleep) or up (happy ^)
        mid = len(lash) // 2
        if e.get('closed') == 'happy':
            pts = [(lash[0][0] + 2, cy + 3), ((x0 + x1) / 2, cy - 9), (lash[-1][0] - 2, cy + 3)]
        else:
            pts = [(lash[0][0] + 2, cy + 4), ((x0 + x1) / 2, cy + 10), (lash[-1][0] - 2, cy + 4)]
        _taper(ctx, pts, 4.5, LASH, 0.2, 0.3)
        return
    # the white: between the lash line (moved down by the lid) and the lower lid
    drop = (1 - min(1.0, op)) * (low[1][1] - lash[len(lash) // 2][1]) * 0.9
    up = max(0.0, op - 1) * 8
    top = [(p[0], p[1] + drop * (1 - abs(p[0] - cx) / (x1 - x0) * 0.6) - up) for p in lash]
    ctx.save()
    _path(ctx, top + list(reversed(low)), True, 0.4)
    ctx.set_source_rgb(*WHITE)
    ctx.fill_preserve()
    ctx.clip()
    # iris + pupil + highlights
    ir = E['iris_r'] * e.get('iris', 1.0)
    ix = cx + look[0] * 5
    iy = cy + look[1] * 3
    ctx.arc(ix, iy, ir, 0, 2 * math.pi)
    g = cairo.LinearGradient(ix, iy - ir, ix, iy + ir)
    g.add_color_stop_rgb(0.0, *IRIS)
    g.add_color_stop_rgb(0.55, *IRIS)
    g.add_color_stop_rgb(1.0, *IRIS_LO)
    ctx.set_source(g)
    ctx.fill_preserve()
    ctx.set_source_rgb(*PUPIL)
    ctx.set_line_width(1.6)
    ctx.stroke()
    ctx.arc(ix, iy - 1, ir * 0.45, 0, 2 * math.pi)
    ctx.set_source_rgb(*PUPIL)
    ctx.fill()
    ctx.arc(ix + ir * 0.42, iy - ir * 0.5, ir * 0.24, 0, 2 * math.pi)
    ctx.set_source_rgb(1, 1, 1)
    ctx.fill()
    ctx.arc(ix - ir * 0.35, iy + ir * 0.45, ir * 0.1, 0, 2 * math.pi)
    ctx.fill()
    # a soft shadow under the upper lid
    _path(ctx, [(p[0], p[1] + 3) for p in top], False)
    ctx.set_source_rgba(0.35, 0.25, 0.25, 0.25)
    ctx.set_line_width(6)
    ctx.stroke()
    ctx.restore()
    # lash line (thick, heavier at the outer corner) with a flick
    _taper(ctx, top, 5.0, LASH, 0.08, 0.35)
    f = E['flick']
    o = top[0] if f < 0 else top[-1]
    ctx.save()
    _taper(ctx, [o, (o[0] + 7 * f, o[1] - 4)], 3.2, LASH, 0.0, 1.0)
    _taper(ctx, [(o[0] - 2 * f, o[1] + 1), (o[0] + 8 * f, o[1] + 4)], 3.0, LASH, 0.0, 1.0)
    ctx.restore()
    # the lower lid: a thin short line
    _taper(ctx, low, 1.6, LASH, 0.4, 0.4)


def _brows(ctx, e):
    lift = e.get('brow', 0)
    # near brow (mostly under the fringe), far brow
    for pts, k in (([(148, 128), (160, 124), (175, 124)], -1), ([(220, 128), (234, 122), (252, 118)], 1)):
        if lift < 0:      # angry: inner ends pull down
            pts = [(x, y + (abs(lift) * 4 if (k < 0 and i == 2) or (k > 0 and i == 0) else 0))
                   for i, (x, y) in enumerate(pts)]
        else:
            pts = [(x, y - lift * 4) for x, y in pts]
        _taper(ctx, pts, 2.6, BROW, 0.3, 0.3)


def _mouth(ctx, e, talk):
    shape = e.get('mouth', 'smile')
    if talk > 0 and shape in ('smile', 'flat'):
        shape = 'talk'
    if shape == 'smile':
        _taper(ctx, [(195, 203), (205, 205), (214, 203), (222, 197)], 2.2, LASH, 0.3, 0.3)
    elif shape == 'flat':
        _taper(ctx, [(198, 205), (208, 205), (218, 202)], 2.0, LASH, 0.3, 0.3)
    elif shape == 'frown':
        _taper(ctx, [(198, 207), (207, 203), (217, 205)], 2.0, LASH, 0.3, 0.3)
    elif shape in ('talk', 'o', 'laugh', 'shout'):
        k = {'talk': 0.5 + 0.5 * talk, 'o': 0.8, 'laugh': 1.0, 'shout': 1.2}[shape]
        w = {'talk': 10, 'o': 6, 'laugh': 13, 'shout': 15}[shape]
        cx, cy = 207, 203 + 4 * k
        hgt = 5 + 9 * k
        if shape == 'o':
            ctx.save()
            ctx.translate(cx, cy)
            ctx.scale(w, hgt / 1.6)
            ctx.arc(0, 0, 1, 0, 2 * math.pi)
            ctx.restore()
        else:
            ctx.move_to(cx - w, cy - hgt * 0.35)
            ctx.curve_to(cx - w * 0.5, cy - hgt * 0.55, cx + w * 0.5, cy - hgt * 0.55, cx + w, cy - hgt * 0.4)
            ctx.curve_to(cx + w * 0.8, cy + hgt * 0.6, cx - w * 0.8, cy + hgt * 0.6, cx - w, cy - hgt * 0.35)
            ctx.close_path()
        ctx.set_source_rgb(*MOUTH)
        ctx.fill_preserve()
        ctx.save()
        ctx.clip_preserve()
        ctx.new_path()
        ctx.save()
        ctx.translate(cx, cy + hgt * 0.45)
        ctx.scale(w * 0.7, hgt * 0.35)
        ctx.arc(0, 0, 1, 0, 2 * math.pi)
        ctx.restore()
        ctx.set_source_rgb(*TONGUE)
        ctx.fill()
        if shape == 'shout':
            ctx.rectangle(cx - w, cy - hgt, 2 * w, hgt * 0.42)
            ctx.set_source_rgb(*TEETH)
            ctx.fill()
        ctx.restore()
        ctx.set_source_rgb(*LASH)
        ctx.set_line_width(1.8)
        ctx.stroke()


def draw_head(ctx, expr='smile', blink=0.0, look=(0.0, 0.0), talk=0.0, lock_rot=(0.0, 0.0, 0.0)):
    """The head and hair in src space (the caller sets the transform). lock_rot: sway of
    (left mass, front lock, right mass) in degrees about their roots."""
    e = EXPR.get(expr, EXPR['smile'])
    ctx.save()
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    # back hair (+ shadow, shine, strands)
    _fill(ctx, HAIR_BACK, HAIR, INK, 2.6)
    _path(ctx, HAIR_BACK, True)
    ctx.save()
    ctx.clip()
    for s in SHADE:
        _fill(ctx, s, HAIR_DK)
    for s in SHINE:
        _fill(ctx, s, HAIR_LT, tension=0.0)
    for st in STRANDS:
        _taper(ctx, st, 1.8, HAIR_LINE, 0.3, 0.3)
    ctx.restore()
    # neck, the lock over the chest (in front of the neck, behind the jaw), ear, face
    _fill(ctx, NECK, SKIN, INK, 2.2)
    _fill(ctx, NECK_SHADOW, SKIN_SH)
    _fill(ctx, FRONT_LOCK, HAIR, INK, 2.4)
    _path(ctx, FRONT_LOCK, True)
    ctx.save()
    ctx.clip()
    for st in STRANDS[10:]:
        _taper(ctx, st, 1.6, HAIR_LINE, 0.3, 0.3)
    _fill(ctx, [(122, 222), (140, 236), (150, 262), (136, 262)], HAIR_DK)
    ctx.restore()
    _fill(ctx, EAR, SKIN, INK, 2.2)
    _fill(ctx, EAR_IN, EAR_IN_COL)
    _taper(ctx, [(104, 196), (99, 203), (104, 212), (112, 214)], 1.6, INK, 0.3, 0.3)
    _fill(ctx, FACE, SKIN)
    # jaw line from under the ear to the chin to the far cheek
    _taper(ctx, [(122, 214), (140, 221), (165, 228), (192, 231), (218, 224), (240, 210), (256, 192), (263, 172)],
           2.6, INK, 0.08, 0.15)
    # blush
    for (bx, by, rx, ry) in ((150, 206, 15, 7), (248, 186, 10, 6)):
        g = cairo.RadialGradient(bx, by, 0, bx, by, rx)
        a = 0.35 * e.get('blush', 1.0)
        g.add_color_stop_rgba(0, *BLUSH, a)
        g.add_color_stop_rgba(1, *BLUSH, 0)
        ctx.save()
        ctx.translate(bx, by)
        ctx.scale(1, ry / rx)
        ctx.translate(-bx, -by)
        ctx.arc(bx, by, rx, 0, 2 * math.pi)
        ctx.set_source(g)
        ctx.fill()
        ctx.restore()
    _brows(ctx, e)
    _eye(ctx, EYE_N, e, blink, look)
    _eye(ctx, EYE_F, e, blink, look)
    # nose: a small "<"
    _taper(ctx, [(211, 170), (218, 176), (215, 181)], 1.8, INK, 0.2, 0.4)
    _mouth(ctx, e, talk)
    # the fringe over the forehead and the side hair framing the face
    edge = FRINGE_EDGE
    _path(ctx, edge + FRINGE_TOP, True, 0.0)
    ctx.set_source_rgb(*HAIR)
    ctx.fill()
    _path(ctx, edge + FRINGE_TOP, True, 0.0)
    ctx.save()
    ctx.clip()
    for s in SHINE:
        _fill(ctx, s, HAIR_LT, tension=0.0)
    for st in STRANDS[:5]:
        _taper(ctx, st, 1.8, HAIR_LINE, 0.3, 0.3)
    ctx.restore()
    _line(ctx, edge, INK, 2.2, 0.0)
    ctx.restore()

