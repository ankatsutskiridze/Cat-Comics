"""The girl: the cat's human, drawn from Anka's reference sheet
(characters/girl/reference_sheet_anka.jpeg, 2026-10-26).

Long straight red-brown hair to the waist with a side-swept fringe, ears showing; big dark
eyes set low in the face, thick upper lash line with an outer flick; tiny nose and mouth;
soft blush; sage-green crew-neck tee; dusty-pink cuffed shorts; white crew socks; chunky
white sneakers. Dark-brown outline, flat colour, a little shading.

How it works
- Figure units: 1 = standing height; (x, y, z), y up from the floor, +x = her left (screen
  right when she faces us), +z = the way she faces. `yaw` turns the figure (0 front, 90 faces
  screen-right, 180 back, negative faces screen-left).
- A part is a GROUP of shapes drawn "stroke all, then fill all", so overlapping shapes of one
  group merge into one outlined silhouette. Parts are depth-sorted for the yaw.
- Head units: 1 = face width, origin on the eye line. The face region, eyes, nose, mouth and
  fringe slide on a sphere with the head's yaw (cartoon turn); the hair dome stays put.
- `draw_girl(ctx, ox, oy, H, pose, face, yaw)` uses ctx's current transform, so a scene can
  rotate the whole figure (lying in bed) by transforming ctx first.
"""
import math

import cairo
import numpy as np


def rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


LINE = rgb('#3b2623')
HAIR = rgb('#9e4330')
HAIR_HI = rgb('#c46a50')
HAIR_DK = rgb('#7e3123')
SKIN = rgb('#f3cdb3')
SKIN_SH = rgb('#e6b39b')
BLUSH = rgb('#f19c8f')
SHIRT = rgb('#bbb985')
SHIRT_SH = rgb('#a5a473')
SHORTS = rgb('#d68f89')
SHORTS_SH = rgb('#c27873')
WHITE = rgb('#f7f3ee')
WHITE_SH = rgb('#ddd5ce')
IRIS = rgb('#2f2526')
IRIS_LO = rgb('#6a5e60')
EYE_W = rgb('#fffdfb')
LASH = rgb('#1f1716')
BROW = rgb('#6e2a1f')
MOUTH = rgb('#9b3b3b')
TONGUE = rgb('#e5787a')
PALETTE = [HAIR, SKIN, SHIRT, SHORTS, rgb('#403231')]

LW = 0.0042          # outline width, figure units
FW = 0.159           # face width, figure units
EYE_Y = 0.837        # eye line height, figure units (the head pivot)
CHIN_V = 0.42        # chin below the eye line, head units

FACES = {
    'smile':     dict(eyes='open', look=(0.2, 0.1), mouth='smile'),
    'look':      dict(eyes='open', look=(0.6, 0.0), mouth='flat'),
    'laugh':     dict(eyes='happy', mouth='laugh'),
    'bored':     dict(eyes='half', lid=0.42, look=(0.45, 0.15), mouth='flat'),
    'surprised': dict(eyes='open', iris=0.068, look=(0, 0), mouth='o', extra='lines'),
    'grumpy':    dict(eyes='half', lid=0.38, look=(0.25, 0.15), mouth='frown', brows='down'),
    'sleep':     dict(eyes='closed', mouth='flat'),
    'tired':     dict(eyes='open', iris=0.034, look=(0, 0), mouth='flat', bags=True, brows='down'),
    'annoyed':   dict(eyes='half', lid=0.5, look=(0, 0.15), mouth='frown', bags=True, brows='down'),
    'angry':     dict(eyes='half', lid=0.28, look=(0, 0.1), mouth='shout', brows='angry', extra='vein'),
}


# ------------------------------------------------------------------ geometry helpers

def _catmull(pts, n=8, closed=False):
    pts = [np.array(p, float) for p in pts]
    m = len(pts)
    if m < 3:
        return [tuple(p) for p in pts]
    out = []
    for i in (range(m) if closed else range(m - 1)):
        p0 = pts[(i - 1) % m] if (closed or i > 0) else pts[0]
        p1, p2 = pts[i], pts[(i + 1) % m]
        p3 = pts[(i + 2) % m] if (closed or i + 2 < m) else pts[-1]
        for k in range(n):
            t = k / n
            out.append(tuple(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t
                                    + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3)))
    if not closed:
        out.append(tuple(pts[-1]))
    return out


def _quad(a, c, b, n=8):
    return [((1 - t) ** 2 * a[0] + 2 * (1 - t) * t * c[0] + t * t * b[0],
             (1 - t) ** 2 * a[1] + 2 * (1 - t) * t * c[1] + t * t * b[1]) for t in np.linspace(0, 1, n)]


def _capsule_poly(a, ra, b, rb, n=10):
    dx, dy = b[0] - a[0], b[1] - a[1]
    ang = math.atan2(dy, dx)
    pts = []
    for k in range(n + 1):
        t = ang + math.pi / 2 - math.pi * k / n
        pts.append((b[0] + rb * math.cos(t), b[1] + rb * math.sin(t)))
    for k in range(n + 1):
        t = ang - math.pi / 2 - math.pi * k / n
        pts.append((a[0] + ra * math.cos(t), a[1] + ra * math.sin(t)))
    return pts


def _path(ctx, pts, closed=True):
    ctx.move_to(*pts[0])
    for p in pts[1:]:
        ctx.line_to(*p)
    if closed:
        ctx.close_path()


def _group(ctx, shapes, fill, lw):
    """Stroke every shape, then fill every shape: one merged outlined silhouette."""
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    for s in shapes:
        _path(ctx, s)
    ctx.set_source_rgb(*LINE)
    ctx.set_line_width(2 * lw)
    ctx.stroke()
    ctx.set_source_rgb(*fill)
    for s in shapes:                    # one fill per shape: opposite windings must not cancel
        _path(ctx, s)
        ctx.fill()


def _line(ctx, pts, w, col=LINE, alpha=1.0, smooth=True):
    pts = _catmull(pts, 6) if smooth and len(pts) > 2 else pts
    _path(ctx, pts, closed=False)
    ctx.set_source_rgba(*col, alpha)
    ctx.set_line_width(w)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.stroke()


def _taper(ctx, pts, w0, w1, col, alpha=1.0):
    """A stroke that tapers from width w0 to w1 (lash lines, hair strands)."""
    pts = _catmull(pts, 8) if len(pts) > 2 else pts
    n = len(pts)
    left, right = [], []
    for i, p in enumerate(pts):
        q0, q1 = pts[max(0, i - 1)], pts[min(n - 1, i + 1)]
        dx, dy = q1[0] - q0[0], q1[1] - q0[1]
        d = math.hypot(dx, dy) + 1e-9
        w = (w0 + (w1 - w0) * i / max(1, n - 1)) / 2
        left.append((p[0] - dy / d * w, p[1] + dx / d * w))
        right.append((p[0] + dy / d * w, p[1] - dx / d * w))
    _path(ctx, left + right[::-1])
    ctx.set_source_rgba(*col, alpha)
    ctx.fill()


def _ellipse(ctx, cx, cy, rx, ry, ang=0.0):
    ctx.save()
    ctx.translate(cx, cy)
    ctx.rotate(ang)
    ctx.scale(max(rx, 1e-6), max(ry, 1e-6))
    ctx.arc(0, 0, 1, 0, 2 * math.pi)
    ctx.restore()


def _ellipse_pts(cx, cy, rx, ry, n=28, ang=0.0):
    ca, sa = math.cos(ang), math.sin(ang)
    return [(cx + rx * math.cos(t) * ca - ry * math.sin(t) * sa,
             cy + rx * math.cos(t) * sa + ry * math.sin(t) * ca)
            for t in np.linspace(0, 2 * math.pi, n, endpoint=False)]


# ------------------------------------------------------------------ poses

def pose_stand(head_turn=0, head_tilt=0, arms='down'):
    p = dict(head_turn=head_turn, head_tilt=head_tilt,
             arm_l=dict(abd=5, flex=0, bend=6), arm_r=dict(abd=5, flex=0, bend=6),
             leg_l=dict(spread=0.0), leg_r=dict(spread=0.0))
    if arms == 'hold_out':          # both arms reaching forward to hold something up
        p['arm_l'] = dict(abd=12, flex=70, bend=18)
        p['arm_r'] = dict(abd=12, flex=70, bend=18)
    return p


# ------------------------------------------------------------------ figure projection

class _Fig:
    def __init__(self, ox, oy, H, yaw):
        self.ox, self.oy, self.H = ox, oy, H
        self.yaw = math.radians(yaw)
        self.c, self.s = math.cos(self.yaw), math.sin(self.yaw)

    def P(self, p):
        x, y, z = p
        return (self.ox + (x * self.c + z * self.s) * self.H, self.oy - y * self.H)

    def depth(self, p):
        x, y, z = p
        return -x * self.s + z * self.c

    def section(self, y, w, d, c=0.0):
        half = math.sqrt((w * self.c) ** 2 + (d * self.s) ** 2)
        cx = c * self.s
        return (self.ox + (cx - half) * self.H, self.ox + (cx + half) * self.H, self.oy - y * self.H)

    def loft(self, sections, n=6):
        secs = [self.section(*s) for s in sections]
        left = [(l, y) for (l, r, y) in secs]
        right = [(r, y) for (l, r, y) in secs]
        return _catmull(left, n) + _catmull(right[::-1], n)


def _arm_points(side, a):
    """3D shoulder, elbow, wrist, fingertip. side -1 = her right (screen left from the front)."""
    S = np.array([0.086 * side, 0.716, 0.0])
    abd, flex, bend = (math.radians(a.get(k, 0)) for k in ('abd', 'flex', 'bend'))
    up = np.array([side * math.sin(abd) * math.cos(flex), -math.cos(abd) * math.cos(flex), math.sin(flex)])
    up /= np.linalg.norm(up)
    E = S + 0.132 * up
    fwd = np.array([0, 0, 1.0]) - up[2] * up
    if np.linalg.norm(fwd) < 1e-6:
        fwd = np.array([0, 1.0, 0])
    fwd /= np.linalg.norm(fwd)
    lo = math.cos(bend) * up + math.sin(bend) * fwd
    W = E + 0.118 * lo
    T = W + 0.052 * lo
    return S, E, W, T


def _leg_points(side, a):
    x0 = 0.037 * side
    sp = a.get('spread', 0.0)
    return [np.array(p) for p in [(x0, 0.49, 0), (x0 + sp * 0.3, 0.37, 0.002), (x0 + sp * 0.6, 0.283, 0.006),
                                  (x0 + 0.002 * side + sp * 0.8, 0.205, 0.0),
                                  (x0 + 0.004 * side + sp, 0.135, -0.004), (x0 + 0.005 * side + sp, 0.08, -0.004)]]


LEG_R = [0.036, 0.0305, 0.0215, 0.0245, 0.018, 0.0158]
ARM_R = [0.0185, 0.0155, 0.0122]


# ------------------------------------------------------------------ body parts

def _shoe(ctx, F, foot, lw):
    """Chunky white sneaker: a front-ish view or a profile depending on yaw."""
    x, z = foot
    H = F.H
    if abs(F.s) <= 0.6:
        cx, base = F.P((x, 0, z))
        w = 0.039 * H
        upper = _catmull([(-0.86, -0.016), (-0.95, -0.036), (-0.72, -0.06), (-0.36, -0.072), (0.0, -0.075),
                          (0.36, -0.072), (0.72, -0.06), (0.95, -0.036), (0.86, -0.016)], 6)
        upper = [(cx + u * w, base + v * H) for u, v in upper] + [(cx + 0.8 * w, base - 0.01 * H),
                                                                   (cx - 0.8 * w, base - 0.01 * H)]
        sole = [(cx - 1.02 * w, base - 0.002 * H), (cx - 1.05 * w, base - 0.019 * H), (cx + 1.05 * w, base - 0.019 * H),
                (cx + 1.02 * w, base - 0.002 * H), (cx + 0.9 * w, base + 0.002 * H), (cx - 0.9 * w, base + 0.002 * H)]
        _group(ctx, [upper], WHITE, lw)
        _group(ctx, [_catmull(sole, 3, closed=True)], WHITE, lw)
        _line(ctx, [(cx - 0.7 * w, base - 0.03 * H), (cx, base - 0.027 * H), (cx + 0.7 * w, base - 0.03 * H)],
              lw * 0.55, LINE, 0.55)
        tw = 0.3 * w
        for k in range(3):
            yy = base - (0.061 - 0.008 * k) * H
            _line(ctx, [(cx - tw, yy), (cx + tw, yy - 0.004 * H)], lw * 0.55, LINE, 0.85, False)
            _line(ctx, [(cx - tw, yy - 0.004 * H), (cx + tw, yy)], lw * 0.55, LINE, 0.85, False)
        return

    def Q(zz, yy):
        return (F.ox + (x * F.c + (z + zz) * F.s) * H, F.oy - yy * H)
    upper = _catmull([Q(-0.034, 0.016), Q(-0.039, 0.045), Q(-0.031, 0.073), Q(-0.012, 0.07), Q(0.008, 0.083),
                      Q(0.022, 0.07), Q(0.05, 0.05), Q(0.072, 0.034), Q(0.08, 0.018)], 6)
    upper += [Q(0.06, 0.012), Q(-0.03, 0.012)]
    sole = [Q(-0.04, 0.0), Q(-0.043, 0.02), Q(0.083, 0.02), Q(0.087, 0.008), Q(0.077, 0.0)]
    _group(ctx, [upper], WHITE, lw)
    _group(ctx, [sole], WHITE, lw)
    _line(ctx, [Q(0.045, 0.021), Q(0.05, 0.033), Q(0.078, 0.03)], lw * 0.55, LINE, 0.7)
    for k in range(3):
        _line(ctx, [Q(0.0 + 0.014 * k, 0.07 - 0.009 * k), Q(0.012 + 0.014 * k, 0.062 - 0.009 * k)],
              lw * 0.65, LINE, 0.9, False)
    _line(ctx, [Q(-0.02, 0.042), Q(0.0, 0.036), Q(0.012, 0.046)], lw * 0.55, LINE, 0.45)


def _hand(ctx, F, W, T, side, lw):
    a, b = F.P(W), F.P(T)
    H = F.H
    ang = math.atan2(b[1] - a[1], b[0] - a[0])
    L = math.hypot(b[0] - a[0], b[1] - a[1])
    k = max(0.5, min(1.0, L / (0.062 * H)))
    cx, cy = a[0] + (b[0] - a[0]) * 0.5, a[1] + (b[1] - a[1]) * 0.5
    ca, sa = math.cos(ang), math.sin(ang)
    # rounded palm + a thumb on the body-facing side, two finger lines
    cx, cy = a[0] + (b[0] - a[0]) * 0.55, a[1] + (b[1] - a[1]) * 0.55
    palm = _ellipse_pts(cx, cy, 0.025 * H * k, 0.012 * H, 26, ang)
    ts = -side if abs(F.s) < 0.6 else 1
    tc = (cx - ca * 0.006 * H + (-sa) * ts * 0.012 * H, cy - sa * 0.006 * H + ca * ts * 0.012 * H)
    thumb = _ellipse_pts(tc[0], tc[1], 0.0105 * H, 0.0052 * H, 16, ang - 0.45 * ts)
    _group(ctx, [palm, thumb], SKIN, lw)
    for f in (-0.35, 0.3):
        p0 = (cx + 0.004 * H * ca - f * 0.014 * H * sa, cy + 0.004 * H * sa + f * 0.014 * H * ca)
        p1 = (cx + 0.024 * H * ca - f * 0.014 * H * sa, cy + 0.024 * H * sa + f * 0.014 * H * ca)
        _line(ctx, [p0, p1], lw * 0.5, LINE, 0.6, False)


# ------------------------------------------------------------------ head

class _Head:
    """Head-local (u right, v down; 1 = face width; origin on the eye line) -> canvas."""

    def __init__(self, cx, cy, s, phi, roll):
        self.cx, self.cy, self.s = cx, cy, s
        self.phi = math.atan2(math.sin(phi), math.cos(phi))
        self.cr, self.sr, self.roll = math.cos(roll), math.sin(roll), roll

    def raw(self, u, v):
        return (self.cx + (u * self.cr - v * self.sr) * self.s, self.cy + (u * self.sr + v * self.cr) * self.s)

    def lp(self, u, v):
        """Silhouette parts: narrow a little and drift toward the face side as she turns."""
        sn = math.sin(self.phi)
        return self.raw(u * (1 - 0.12 * abs(sn)) + 0.05 * sn, v)

    def ang(self, u, r):
        a = math.asin(max(-1.0, min(1.0, u / r))) + self.phi
        return max(-math.pi / 2, min(math.pi / 2, a)) if abs(self.phi) <= math.pi / 2 else a

    def hp(self, u, v, r=0.52):
        return self.raw(r * math.sin(self.ang(u, r)), v)

    def vis(self, u, r=0.52):
        a = math.asin(max(-1.0, min(1.0, u / r)))
        return math.cos(a + self.phi)

    def kx(self, u, r=0.52):
        a = math.asin(max(-1.0, min(1.0, u / r)))
        return max(0.0, math.cos(a + self.phi)) / max(0.3, math.cos(a))

    def enter(self, ctx, u, v, min_vis=0.15, r=0.52):
        if self.vis(u, r) < min_vis:
            return False
        ctx.save()
        ctx.translate(*self.hp(u, v, r))
        ctx.rotate(self.roll)
        ctx.scale(self.s * self.kx(u, r), self.s)
        return True


# face region (skin), front view, from the forehead under the fringe round to the chin
FACE = [(0.0, -0.80), (0.40, -0.74), (0.50, -0.45), (0.51, -0.10), (0.505, 0.10), (0.47, 0.22),
        (0.37, 0.33), (0.19, 0.40), (0.0, CHIN_V), (-0.19, 0.40), (-0.37, 0.33), (-0.47, 0.22),
        (-0.505, 0.10), (-0.51, -0.10), (-0.50, -0.45), (-0.40, -0.74)]


# profile face (facing +u): forehead, small nose, lips, chin, jaw back to under the ear
PROFILE = [(0.28, -0.80), (0.45, -0.50), (0.50, -0.18), (0.50, 0.02), (0.56, 0.085), (0.505, 0.13),
           (0.50, 0.19), (0.515, 0.235), (0.49, 0.27), (0.47, 0.33), (0.39, 0.41), (0.22, 0.43),
           (0.02, 0.36), (-0.06, 0.24), (-0.02, 0.0), (0.12, -0.3), (0.25, -0.65)]


def _resample(pts, n):
    pts = np.array(pts + [pts[0]], float)
    seg = np.hypot(*np.diff(pts, axis=0).T)
    cum = np.concatenate([[0], np.cumsum(seg)])
    t = np.linspace(0, cum[-1], n, endpoint=False)
    return np.stack([np.interp(t, cum, pts[:, 0]), np.interp(t, cum, pts[:, 1])], 1)


def _face_pts(hd):
    sn = math.sin(hd.phi)
    front = _resample([hd.hp(u, v, 0.53) for u, v in FACE], 64)
    k = max(0.0, min(1.0, (abs(sn) - 0.62) / 0.3))
    if k <= 0 or math.cos(hd.phi) < 0:
        return _catmull([tuple(p) for p in front], 2, closed=True)
    d = math.copysign(1, sn)
    prof = [hd.raw(u * d, v) for u, v in PROFILE]
    if d < 0:
        prof = prof[::-1]
    prof = _resample(prof, 64)
    # align the starting points (top of the forehead) before blending
    i0 = int(np.argmin(front[:, 1]))
    j0 = int(np.argmin(prof[:, 1]))
    front = np.roll(front, -i0, axis=0)
    prof = np.roll(prof, -j0, axis=0)
    k = k * k * (3 - 2 * k)
    return _catmull([tuple(p) for p in front * (1 - k) + prof * k], 2, closed=True)


def _dome(hd):
    """The hair mass round the skull (stays put as she turns)."""
    pts = [(0.0, -1.03), (0.40, -0.98), (0.66, -0.72), (0.74, -0.35), (0.74, 0.05), (0.66, 0.2),
           (-0.66, 0.2), (-0.74, 0.05), (-0.74, -0.35), (-0.66, -0.72), (-0.40, -0.98)]
    sn = math.sin(hd.phi)

    def k(u):
        return (1 - 0.32 * abs(sn)) if u * sn > 0 else (1 + 0.08 * abs(sn))
    return _catmull([hd.raw(u * k(u), v) for u, v in pts], 5, closed=True)


def _hair_back(ctx, hd, lw, length=2.05):
    """The long straight curtain behind head and body."""
    w = 0.76 - 0.08 * abs(math.sin(hd.phi))
    pts = [hd.lp(-0.6, -0.8), hd.lp(0, -1.0), hd.lp(0.6, -0.8), hd.lp(w, -0.2), hd.raw(w + 0.06 + 0.05 * math.sin(hd.phi), 1.0)]
    tips = np.linspace(w + 0.08, -w - 0.08, 11)
    for k, u in enumerate(tips):
        pts.append(hd.raw(u + 0.05 * math.sin(hd.phi), length + (0.05 if k % 2 else -0.03)))
    pts += [hd.raw(-w - 0.06 + 0.05 * math.sin(hd.phi), 1.0), hd.lp(-w, -0.2)]
    _group(ctx, [_catmull(pts, 4, closed=True), _dome(hd)], HAIR, lw)
    for u in (-0.5, -0.2, 0.15, 0.45):
        _line(ctx, [hd.raw(u, 0.45), hd.raw(u * 1.04, length - 0.2)], lw * 0.65, HAIR_DK, 0.7, False)


def _side_locks(ctx, hd, lw, length=1.75):
    """Locks falling in front of the shoulders from behind the ears."""
    sn = math.sin(hd.phi)
    for side in (-1, 1):
        if side * sn > 0.55:                 # the far lock hides behind the head
            continue
        u0 = 0.58 * side
        pts = [hd.lp(u0 - 0.10 * side, -0.2), hd.lp(u0 + 0.12 * side, -0.25), hd.lp(u0 + 0.15 * side, 0.5),
               hd.lp(u0 + 0.15 * side, length - 0.3), hd.lp(u0 + 0.10 * side, length - 0.02),
               hd.lp(u0 + 0.05 * side, length - 0.15), hd.lp(u0 - 0.0 * side, length + 0.06),
               hd.lp(u0 - 0.06 * side, length - 0.35), hd.lp(u0 - 0.08 * side, 0.5)]
        _group(ctx, [_catmull(pts, 4, closed=True)], HAIR, lw)
        _line(ctx, [hd.lp(u0 + 0.05 * side, 0.3), hd.lp(u0 + 0.05 * side, length - 0.3)], lw * 0.6, HAIR_DK, 0.75)


def _ears(ctx, hd, lw):
    for side in (-1, 1):
        if hd.vis(0.5 * side, 0.53) < -0.15:
            continue
        c = hd.hp(0.505 * side, 0.08, 0.53)
        k = max(0.55, hd.kx(0.5 * side, 0.53) * 1.8) if hd.vis(0.5 * side) < 0.6 else 1.0
        ear = _ellipse_pts(c[0] + 0.045 * side * hd.s * math.cos(hd.phi), c[1], 0.082 * hd.s * min(1, k),
                           0.118 * hd.s, 24, hd.roll + 0.15 * side)
        _group(ctx, [ear], SKIN, lw)
        _line(ctx, [(c[0] + 0.02 * side * hd.s, c[1] - 0.05 * hd.s), (c[0] + 0.05 * side * hd.s, c[1]),
                    (c[0] + 0.025 * side * hd.s, c[1] + 0.05 * hd.s)], lw * 0.8, SKIN_SH, 1.0)


# fringe tips (u, v) left to right and the notches between them; one long strand between the eyes
FRINGE = [(-0.62, 0.26), (-0.52, -0.22), (-0.45, -0.03), (-0.36, -0.26), (-0.23, -0.10), (-0.13, -0.30),
          (0.02, 0.05), (0.09, -0.28), (0.23, -0.08), (0.32, -0.26), (0.44, -0.04), (0.51, -0.22),
          (0.62, 0.26)]


def _fringe(ctx, hd, lw):
    """Crown + side-swept fringe as one outlined mass (slides with the face), highlights on top."""
    r = 0.58
    top = [(-0.62, -0.25), (-0.56, -0.72), (-0.30, -0.95), (0.0, -1.0), (0.30, -0.95), (0.56, -0.72),
           (0.62, -0.25)]
    edge = []
    for i in range(len(FRINGE) - 1):
        a, b = FRINGE[i], FRINGE[i + 1]
        # strands sweep to screen-left: the control point leans toward the left of each span
        if b[1] > a[1]:                     # notch -> tip: a long concave sweep down-left
            c = (a[0] + (b[0] - a[0]) * 0.05, a[1] + (b[1] - a[1]) * 0.75)
        else:                               # tip -> next notch: short and straight-ish
            c = (a[0] + (b[0] - a[0]) * 0.55, a[1] + (b[1] - a[1]) * 0.35)
        edge += _quad(a, c, b, 8)[:-1]
    edge.append(FRINGE[-1])
    # crown arc right->left, then the fringe edge left->right
    pts = [hd.hp(u, v, r) for u, v in top[::-1]] + [hd.hp(u, v, r) for u, v in edge]
    edge_px = [hd.hp(u, v, r) for u, v in edge]
    ctx.save()
    _path(ctx, _dome(hd))
    _path(ctx, _face_pts(hd))
    ctx.clip()
    _path(ctx, pts)
    ctx.set_source_rgb(*HAIR)
    ctx.fill()
    _path(ctx, edge_px, closed=False)
    ctx.set_source_rgb(*LINE)
    ctx.set_line_width(2 * lw * 0.7)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.stroke()
    ctx.restore()
    # strand lines from the crown to the tips
    for i in range(0, len(FRINGE), 2):
        u, v = FRINGE[i]
        if hd.vis(u, r) < 0.2:
            continue
        _taper(ctx, [hd.hp(u * 0.6 + 0.04, -0.82, r), hd.hp(u * 0.85 + 0.02, -0.4, r), hd.hp(u, v - 0.06, r)],
               lw * 0.9, lw * 0.15, HAIR_DK, 0.8)
    # glossy band across the crown
    rnd = np.random.default_rng(5)
    for k, u in enumerate(np.linspace(-0.48, 0.48, 9)):
        if hd.vis(u, 0.62) < 0.2:
            continue
        v0 = -0.86 + 0.18 * u * u + rnd.uniform(-0.02, 0.02)
        L = rnd.uniform(0.06, 0.16)
        _taper(ctx, [hd.hp(u, v0, 0.62), hd.hp(u * 1.02, v0 + L * 0.5, 0.62), hd.hp(u * 1.04, v0 + L, 0.62)],
               hd.s * rnd.uniform(0.025, 0.04), hd.s * 0.004, HAIR_HI, 0.6)


def _eye(ctx, hd, side, f, lw):
    if not hd.enter(ctx, 0.255 * side, 0.0, 0.12):
        return
    out = side
    kind = f.get('eyes', 'open')
    lx, ly = f.get('look', (0, 0))
    if kind in ('open', 'half'):
        top = [(-0.13 * out, 0.02), (-0.09 * out, -0.075), (0.0, -0.118), (0.10 * out, -0.095), (0.155 * out, -0.045)]
        bot = [(0.155 * out, -0.045), (0.12 * out, 0.06), (0.03 * out, 0.115), (-0.08 * out, 0.09), (-0.13 * out, 0.02)]
        shape = _catmull(top + bot[1:], 6, closed=True)
        lid_y = -0.118 + f.get('lid', 0.0) * 0.233 if kind == 'half' else None
        ctx.save()
        _path(ctx, shape)
        ctx.clip()
        if lid_y is not None:
            ctx.rectangle(-1, lid_y, 2, 2)
            ctx.clip()
        ctx.set_source_rgb(*EYE_W)
        ctx.paint()
        r = f.get('iris', 0.098)
        ix, iy = lx * 0.045, 0.015 + ly * 0.03
        _ellipse(ctx, ix, iy, r * 0.88, r)
        ctx.set_source_rgb(*IRIS)
        ctx.fill()
        _ellipse(ctx, ix, iy + r * 0.48, r * 0.66, r * 0.42)
        ctx.set_source_rgb(*IRIS_LO)
        ctx.fill()
        if r > 0.05:
            _ellipse(ctx, ix + 0.035, iy - 0.045, 0.026, 0.026)
            ctx.set_source_rgb(1, 1, 1)
            ctx.fill()
            _ellipse(ctx, ix - 0.035, iy + 0.045, 0.01, 0.01)
            ctx.fill()
        ctx.restore()
        if lid_y is not None:
            _taper(ctx, [(-0.135 * out, lid_y + 0.035), (0.0, lid_y + 0.005), (0.16 * out, lid_y + 0.012)],
                   0.012, 0.03, LASH)
            _taper(ctx, [(0.14 * out, lid_y + 0.01), (0.19 * out, lid_y - 0.02)], 0.022, 0.004, LASH)
        else:
            _taper(ctx, top, 0.012, 0.034, LASH)
            _taper(ctx, [(0.13 * out, -0.07), (0.185 * out, -0.105), (0.205 * out, -0.105)], 0.022, 0.004, LASH)
            _taper(ctx, [(0.10 * out, -0.093), (0.15 * out, -0.13)], 0.014, 0.003, LASH)
            _line(ctx, [(-0.06 * out, -0.155), (0.04 * out, -0.17), (0.12 * out, -0.145)], 0.008, LINE, 0.4)
        _taper(ctx, [(0.0, 0.115), (0.09 * out, 0.085), (0.14 * out, 0.03)], 0.004, 0.012, LINE, 0.75)
        for k in range(2):                               # two little lower lashes
            x = (0.06 + 0.05 * k) * out
            _line(ctx, [(x, 0.105 - 0.025 * k), (x + 0.012 * out, 0.125 - 0.025 * k)], 0.006, LINE, 0.6, False)
        if f.get('bags'):
            _line(ctx, [(-0.08 * out, 0.15), (0.0, 0.17), (0.10 * out, 0.145)], 0.011, SKIN_SH, 1.0)
            _line(ctx, [(-0.05 * out, 0.195), (0.06 * out, 0.2)], 0.008, SKIN_SH, 0.9)
    elif kind == 'closed':
        _taper(ctx, [(-0.13 * out, 0.02), (0.0, 0.06), (0.15 * out, 0.015)], 0.01, 0.026, LASH)
        for k in range(3):
            x = (0.03 + 0.045 * k) * out
            _line(ctx, [(x, 0.05 - 0.01 * k), (x + 0.018 * out, 0.08 - 0.012 * k)], 0.009, LASH)
    elif kind == 'happy':
        _taper(ctx, [(-0.13 * out, 0.035), (0.0, -0.035), (0.14 * out, 0.03)], 0.01, 0.026, LASH)
        _taper(ctx, [(0.13 * out, 0.02), (0.18 * out, -0.01)], 0.016, 0.003, LASH)
    ctx.restore()


def _brows(ctx, hd, f):
    kind = f.get('brows', 'normal')
    for side in (-1, 1):
        if not hd.enter(ctx, 0.25 * side, -0.24, 0.15):
            continue
        out = side
        pts = {'angry': [(-0.12 * out, 0.06), (0.0, 0.015), (0.12 * out, -0.03)],
               'down': [(-0.12 * out, 0.03), (0.0, 0.0), (0.12 * out, 0.0)]}.get(
            kind, [(-0.12 * out, 0.01), (0.0, -0.03), (0.12 * out, -0.015)])
        _taper(ctx, pts, 0.018, 0.008, BROW)
        ctx.restore()


def _nose_mouth(ctx, hd, f):
    if hd.enter(ctx, 0.03, 0.10, 0.1):
        _line(ctx, [(0.0, -0.025), (0.016, 0.008), (-0.004, 0.018)], 0.011, rgb('#b47a65'), 1.0)
        ctx.restore()
    m = f.get('mouth', 'smile')
    if not hd.enter(ctx, 0.02, 0.24, 0.1):
        return
    if m == 'smile':
        _taper(ctx, [(-0.065, -0.012), (0.0, 0.016), (0.065, -0.014)], 0.006, 0.011, LINE)
    elif m == 'flat':
        _line(ctx, [(-0.032, 0.0), (0.032, -0.002)], 0.010, LINE, smooth=False)
    elif m == 'frown':
        _line(ctx, [(-0.045, 0.012), (0.0, -0.006), (0.045, 0.01)], 0.010, LINE)
    elif m == 'o':
        _ellipse(ctx, 0, 0.012, 0.026, 0.034)
        ctx.set_source_rgb(*MOUTH)
        ctx.fill_preserve()
        ctx.set_source_rgb(*LINE)
        ctx.set_line_width(0.009)
        ctx.stroke()
    elif m in ('laugh', 'shout'):
        pts = ([(-0.075, -0.02), (0.075, -0.02), (0.045, 0.055), (0.0, 0.072), (-0.045, 0.055)] if m == 'laugh'
               else [(-0.09, -0.035), (0.09, -0.045), (0.075, 0.06), (0.0, 0.10), (-0.07, 0.065)])
        shape = _catmull(pts, 5, closed=True)
        _path(ctx, shape)
        ctx.set_source_rgb(*MOUTH)
        ctx.fill_preserve()
        ctx.save()
        ctx.clip()
        _ellipse(ctx, 0.0, 0.08 if m == 'laugh' else 0.11, 0.055, 0.04)
        ctx.set_source_rgb(*TONGUE)
        ctx.fill()
        if m == 'shout':
            ctx.rectangle(-0.12, -0.06, 0.24, 0.04)
            ctx.set_source_rgb(1, 1, 1)
            ctx.fill()
        ctx.restore()
        _path(ctx, shape)
        ctx.set_source_rgb(*LINE)
        ctx.set_line_width(0.010)
        ctx.set_line_join(cairo.LINE_JOIN_ROUND)
        ctx.stroke()
    ctx.restore()


def _blush(ctx, hd):
    for side in (-1, 1):
        if hd.enter(ctx, 0.31 * side, 0.15, 0.2):
            _ellipse(ctx, 0, 0, 0.09, 0.045)
            ctx.set_source_rgba(*BLUSH, 0.42)
            ctx.fill()
            ctx.restore()


def _extras(ctx, hd, f):
    ex = f.get('extra')
    if ex == 'lines':
        for a, r0, r1 in [(-62, 1.05, 1.22), (-42, 1.08, 1.26), (-22, 1.1, 1.25)]:
            t = math.radians(a)
            _line(ctx, [hd.raw(math.cos(t) * r0 * 0.8, -0.35 + math.sin(t) * r0),
                        hd.raw(math.cos(t) * r1 * 0.8, -0.35 + math.sin(t) * r1)], 0.024 * hd.s, LINE, 1.0, False)
    if ex == 'vein' and hd.enter(ctx, -0.32, -0.55, 0.0):
        for k in range(4):
            ctx.save()
            ctx.rotate(k * math.pi / 2 + math.pi / 4)
            _line(ctx, [(0.02, -0.05), (0.012, -0.025), (0.05, -0.02)], 0.02, rgb('#d8342b'))
            ctx.restore()
        ctx.restore()


def draw_head(ctx, hd, f, lw, back_hair=True, locks=True, hair_len=2.05, lock_len=1.75):
    """Head + hair. back_hair/locks can be left to the caller (body depth order)."""
    if back_hair:
        _hair_back(ctx, hd, lw, hair_len)
    back_view = math.cos(hd.phi) < -0.15
    if back_view:
        for u in (-0.3, 0.0, 0.3):
            _line(ctx, [hd.lp(u * 0.6, -0.9), hd.lp(u, 0.1)], lw * 0.6, HAIR_DK, 0.7)
        return
    if locks:
        _side_locks(ctx, hd, lw, lock_len)
        ctx.save()
        top = hd.raw(0, 0.12)
        ang = hd.roll
        ctx.translate(*top)
        ctx.rotate(ang)
        ctx.rectangle(-5 * hd.s, -5 * hd.s, 10 * hd.s, 5 * hd.s)
        ctx.restore()
        ctx.save()
        ctx.clip()
        _path(ctx, _dome(hd))
        ctx.set_source_rgb(*HAIR)
        ctx.fill()
        ctx.restore()
    _ears(ctx, hd, lw)
    _group(ctx, [_face_pts(hd)], SKIN, lw)
    _blush(ctx, hd)
    _brows(ctx, hd, f)
    _eye(ctx, hd, -1, f, lw)
    _eye(ctx, hd, 1, f, lw)
    _nose_mouth(ctx, hd, f)
    _fringe(ctx, hd, lw)
    _extras(ctx, hd, f)


# ------------------------------------------------------------------ the whole figure

def draw_girl(ctx, ox, oy, H, pose=None, face='smile', yaw=0.0):
    """Standing figure, feet at (ox, oy), height H px, in ctx's current transform."""
    pose = pose or pose_stand()
    f = FACES[face] if isinstance(face, str) else face
    F = _Fig(ox, oy, H, yaw)
    lw = LW * H
    items = []                                       # (depth, fn)

    for side, key in ((-1, 'leg_l'), (1, 'leg_r')):
        pts = _leg_points(side, pose.get(key, {}))

        def leg(ctx, pts=pts):
            pp = [F.P(p) for p in pts]
            _group(ctx, [_capsule_poly(pp[i], LEG_R[i] * H, pp[i + 1], LEG_R[i + 1] * H)
                         for i in range(len(pp) - 1)], SKIN, lw)
            k = pp[2]
            _line(ctx, [(k[0] - 0.007 * H, k[1] + 0.003 * H), (k[0], k[1] + 0.007 * H),
                        (k[0] + 0.006 * H, k[1] + 0.003 * H)], lw * 0.6, SKIN_SH, 1.0)
            a, b = F.P(pts[4] + np.array([0, 0.008, 0])), F.P(pts[5] - np.array([0, 0.025, 0]))
            _group(ctx, [_capsule_poly(a, 0.0205 * H, b, 0.0185 * H)], WHITE, lw)
            for kk in range(2):
                yy = a[1] + 0.005 * H * (kk + 1)
                _line(ctx, [(a[0] - 0.016 * H, yy), (a[0] + 0.016 * H, yy)], lw * 0.45, WHITE_SH, 1.0, False)
            _shoe(ctx, F, (pts[5][0], 0.004), lw)
        items.append((-0.05 + 0.001 * F.depth(pts[2]), leg))

    def shorts(ctx):
        secs = [(0.558, 0.073, 0.054, -0.004), (0.53, 0.077, 0.058, -0.006), (0.485, 0.08, 0.06, -0.008)]
        shapes = [F.loft(secs)]
        for side in (-1, 1):
            x0 = 0.04 * side
            t0, t1 = F.section(0.49, 0.043, 0.05, 0.0), F.section(0.442, 0.046, 0.052, 0.0)
            dx = x0 * F.c * H
            shapes.append([(t0[0] + dx, t0[2]), (t0[1] + dx, t0[2]), (t1[1] + dx + 0.002 * H, t1[2]),
                           (t1[0] + dx - 0.002 * H, t1[2])])
        _group(ctx, shapes, SHORTS, lw)
        ctx.save()
        for s in shapes:
            _path(ctx, s)
        ctx.clip()
        l, r, y = F.section(0.5, 0.08, 0.06, -0.008)
        ctx.rectangle(l - H, F.oy - 0.47 * H, 3 * H, 0.03 * H)       # crotch shade
        ctx.set_source_rgba(*SHORTS_SH, 0.5)
        ctx.fill()
        ctx.restore()
        for side in (-1, 1):                          # rolled cuffs
            x0 = 0.04 * side
            t1 = F.section(0.442, 0.047, 0.053, 0.0)
            dx = x0 * F.c * H
            cuff = [(t1[0] + dx - 0.003 * H, t1[2] - 0.02 * H), (t1[1] + dx + 0.003 * H, t1[2] - 0.02 * H),
                    (t1[1] + dx + 0.004 * H, t1[2] + 0.001 * H), (t1[0] + dx - 0.004 * H, t1[2] + 0.001 * H)]
            _group(ctx, [cuff], SHORTS, lw * 0.85)
        if F.c > 0.5:                                  # fly + front pockets
            _line(ctx, [F.P((0.008, 0.548, 0.06)), F.P((0.01, 0.495, 0.06)), F.P((0.0, 0.48, 0.06))], lw * 0.6)
            for side in (-1, 1):
                _line(ctx, [F.P((0.045 * side, 0.55, 0.05)), F.P((0.058 * side, 0.522, 0.05)),
                            F.P((0.077 * side, 0.512, 0.04))], lw * 0.6)
        if F.c < -0.5:
            for side in (-1, 1):
                p0 = F.P((0.045 * side, 0.53, -0.06))
                _line(ctx, [(p0[0] - 0.02 * H, p0[1]), (p0[0] + 0.02 * H, p0[1])], lw * 0.6)
    items.append((0.0, shorts))

    arms = {}
    for side, key in ((-1, 'arm_l'), (1, 'arm_r')):
        arms[side] = _arm_points(side, pose.get(key, {}))

    def sleeve_shape(S, E):
        d = (E - S) / (np.linalg.norm(E - S) + 1e-9)
        a, b = F.P(S + d * 0.004 + np.array([0, 0.006, 0])), F.P(S + d * 0.066)
        ang = math.atan2(b[1] - a[1], b[0] - a[0]) + math.pi / 2
        wa, wb = 0.031 * H, 0.031 * H
        ca, sa = math.cos(ang), math.sin(ang)
        dx, dy = b[0] - a[0], b[1] - a[1]
        cap = [(a[0] + ca * wa * math.cos(t) - dx / 3.0 * math.sin(t), a[1] + sa * wa * math.cos(t) - dy / 3.0 * math.sin(t))
               for t in np.linspace(0, math.pi, 9)]
        return cap + [(b[0] - ca * wb, b[1] - sa * wb), (b[0] + ca * wb, b[1] + sa * wb)], (a, b, ang, wb)

    def arm_fn(side, with_sleeve):
        S, E, W, T = arms[side]

        def fn(ctx):
            pS, pE, pW = F.P(S), F.P(E), F.P(W)
            _group(ctx, [_capsule_poly(pS, ARM_R[0] * H, pE, ARM_R[1] * H),
                         _capsule_poly(pE, ARM_R[1] * H, pW, ARM_R[2] * H)], SKIN, lw)
            _hand(ctx, F, W, T, side, lw)
            if with_sleeve:
                sh, (a, b, ang, wb) = sleeve_shape(S, E)
                _group(ctx, [sh], SHIRT, lw)
                c = (a[0] + (b[0] - a[0]) * 0.82, a[1] + (b[1] - a[1]) * 0.82)
                _line(ctx, [(c[0] - math.cos(ang) * wb, c[1] - math.sin(ang) * wb),
                            (c[0] + math.cos(ang) * wb, c[1] + math.sin(ang) * wb)], lw * 0.7, LINE, 1.0, False)
        return fn

    side_view = abs(F.s) > 0.5
    for side in (-1, 1):
        S, E, W, T = arms[side]
        forward = E[2] > 0.05 or W[2] > 0.08
        if side_view:
            dep = F.depth(S) + (0.02 if forward else 0.0)
        else:
            dep = 0.02 if forward else -0.01
        items.append((dep, arm_fn(side, with_sleeve=forward or side_view)))

    def torso(ctx):
        nk = F.section(0.76, 0.0235, 0.026, 0.004)
        neck = [(nk[0], F.oy - 0.79 * H), (nk[1], F.oy - 0.79 * H), (nk[1], F.oy - 0.735 * H), (nk[0], F.oy - 0.735 * H)]
        _group(ctx, [neck], SKIN, lw)
        mx = (nk[0] + nk[1]) / 2
        _line(ctx, [(mx - 0.015 * H, F.oy - 0.772 * H), (mx, F.oy - 0.766 * H), (mx + 0.015 * H, F.oy - 0.772 * H)],
              0.01 * H, SKIN_SH, 0.6)
        secs = [(0.748, 0.036, 0.032, 0.0), (0.733, 0.066, 0.044, 0.0), (0.712, 0.076, 0.05, 0.002),
                (0.67, 0.073, 0.054, 0.006), (0.62, 0.072, 0.056, 0.01), (0.58, 0.073, 0.053, 0.006),
                (0.545, 0.076, 0.052, 0.0)]
        shapes = [F.loft(secs)]
        if not side_view:
            for side in (-1, 1):
                S, E, W, T = arms[side]
                if not (E[2] > 0.05 or W[2] > 0.08):
                    shapes.append(sleeve_shape(S, E)[0])
        _group(ctx, shapes, SHIRT, lw)
        if not side_view:
            for side in (-1, 1):
                S, E, W, T = arms[side]
                if not (E[2] > 0.05 or W[2] > 0.08):
                    sh, (a, b, ang, wb) = sleeve_shape(S, E)
                    c = (a[0] + (b[0] - a[0]) * 0.82, a[1] + (b[1] - a[1]) * 0.82)
                    _line(ctx, [(c[0] - math.cos(ang) * wb, c[1] - math.sin(ang) * wb),
                                (c[0] + math.cos(ang) * wb, c[1] + math.sin(ang) * wb)], lw * 0.7, LINE, 1.0, False)
                    _line(ctx, [F.P((0.07 * side, 0.672, 0.01)), F.P((0.068 * side, 0.66, 0.01))], lw * 0.6)
        ctx.save()                                       # side shade
        _path(ctx, F.loft(secs))
        ctx.clip()
        l, r, y = F.section(0.62, 0.072, 0.056, 0.01)
        ctx.rectangle(r - 0.026 * H, F.oy - 0.75 * H, 0.06 * H, 0.22 * H)
        ctx.set_source_rgba(*SHIRT_SH, 0.55)
        ctx.fill()
        ctx.restore()
        if F.c > -0.2:                                   # ribbed crew neck
            c = F.P((0, 0.744, 0.03 * F.c))
            w = 0.029 * H * max(0.45, abs(F.c))
            _ellipse(ctx, c[0], c[1], w, 0.010 * H)
            ctx.set_source_rgb(*SKIN)
            ctx.fill()
            for k, (ww, hh) in enumerate([(w, 0.010 * H), (w + 0.007 * H, 0.016 * H)]):
                ctx.save()
                ctx.translate(c[0], c[1])
                ctx.scale(ww, hh)
                ctx.arc(0, 0, 1, 0.0, math.pi)
                ctx.restore()
                ctx.set_source_rgb(*LINE)
                ctx.set_line_width(lw * (1.0 if k else 0.7))
                ctx.stroke()
    items.append((0.005, torso))

    hcx, hcy = F.P((0, EYE_Y, 0.006))
    phi = F.yaw + math.radians(pose.get('head_turn', 0))
    hd = _Head(hcx, hcy, FW * H, phi, math.radians(pose.get('head_tilt', 0)))
    back_view = math.cos(F.yaw) < -0.2
    items.append((-0.08 if not back_view else 0.09, lambda ctx: _hair_back(ctx, hd, lw)))
    items.append((0.03 if not back_view else 0.01, lambda ctx: draw_head(ctx, hd, f, lw, back_hair=False)))

    for dep, fn in sorted(items, key=lambda it: it[0]):
        fn(ctx)
    return hd
