"""The cat: a black graffiti cat drawn from a 3D stick skeleton.

Design source: characters/cat/reference_sheet_anka.jpeg (Anka, 2026-10-25), at normal
cat proportions (the sheet's "In action" figures), not the sheet's stretched hero, and
with thick fur and NO coloured drawings on the face or the tail (Anka, 2026-10-25).

How it works
- A pose is plain data: 3D joints in HEAD-WIDTH units (ground y=0, +z = the way the
  cat faces, +x = the cat's left = screen right in a front view) with a radius each.
- `draw_cat` projects the pose orthographically at any yaw (0 front, 90 facing right,
  180 back), so one pose renders from every side.
- Everything black (body, legs, tail, head, ears) is drawn into ONE mask, so overlaps
  merge into a single silhouette; its edge is roughened with a noise field (brush look).
- On top, in ink: thin fur flicks off every body edge, long hair spikes on the cheeks,
  pencil overshoot strokes at the ear tips, paint drips under the chin and tail tip.
  Inside: long violet / pink sketch lines and toe lines on the paws.
- Face on top of that. Facial features slide on a sphere with the head's yaw; the head's
  silhouette (cheek hair) stays put, as in a cartoon.
"""
import math

import cairo
import numpy as np
from scipy import ndimage


def rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


INK = rgb('#0b0a0d')
EYE = rgb('#f6efc6')
PUPIL = rgb('#1d1a0b')
GOLD = rgb('#d9b21e')
NOSE = rgb('#ee8d96')
ORANGE = rgb('#f2541b')
GREEN = rgb('#58b33b')
YELLOW = rgb('#f5d327')
PINK = rgb('#f0479a')
BLUE = rgb('#2f86e0')
VIOLET = rgb('#8a5bd6')
MOUTH = rgb('#4a0b16')
TONGUE = rgb('#f07a8c')
RED = rgb('#e0302a')
PALETTE = [INK, EYE, ORANGE, GREEN, PINK, BLUE]

HEAD_R = 0.5          # sphere radius the facial features slide on

FACES = {
    'smug':      dict(eyes='slit', open=0.67, slant=0.53, mouth='smile'),
    'deadpan':   dict(eyes='slit', open=0.45, slant=0.06, mouth='flat'),
    'surprised': dict(eyes='round', mouth='o', extra='shock'),
    'sleepy':    dict(eyes='closed', mouth='flat'),
    'angry':     dict(eyes='slit', open=0.62, slant=0.80, mouth='frown', extra='anger'),
    'silly':     dict(eyes='happy', mouth='tongue'),
    'confused':  dict(eyes='round', mouth='flat', extra='question', look=(-0.5, -0.3)),
    'love':      dict(eyes='heart', mouth='smile', extra='hearts'),
    'scream':    dict(eyes='round', mouth='scream', extra='shock'),
}


# ---------------------------------------------------------------- poses

def _leg_ik(root, foot, l1, l2, bend):
    """2-bone IK in 3D: returns the middle joint."""
    a, f, b = np.array(root, float), np.array(foot, float), np.array(bend, float)
    d = f - a
    dist = float(np.linalg.norm(d))
    dist = max(1e-6, min(dist, l1 + l2 - 1e-4))
    u = d / (np.linalg.norm(d) + 1e-9)
    along = (l1 * l1 - l2 * l2 + dist * dist) / (2 * dist)
    h = math.sqrt(max(l1 * l1 - along * along, 0.0))
    perp = b - np.dot(b, u) * u
    perp /= (np.linalg.norm(perp) + 1e-9)
    return tuple(a + u * along + perp * h)


def _front_leg(sx, shoulder, foot):
    s = (sx,) + tuple(shoulder)
    f = (sx,) + tuple(foot)
    wrist = (f[0], f[1] + 0.07, f[2] - 0.02)
    elbow = _leg_ik(s, wrist, 0.47, 0.45, (0, 0, -1))
    return [(s, 0.085), (elbow, 0.062), (wrist, 0.052)], (f[0], f[1], f[2])


def _back_leg(sx, hip, foot, thigh_r=0.14):
    h = (sx,) + tuple(hip)
    f = (sx,) + tuple(foot)
    hock = (f[0], f[1] + 0.26, f[2] - 0.10)
    ankle = (f[0], f[1] + 0.06, f[2] - 0.02)
    knee = _leg_ik(h, hock, 0.44, 0.38, (0, 0, 1))
    return [(h, thigh_r), (knee, 0.085), (hock, 0.055), (ankle, 0.05)], (f[0], f[1], f[2] + 0.03)


def pose_stand(head_turn=0, head_roll=0, step=0.0):
    """Standing on four legs. `step` -1..1 swings the legs (a walk frame)."""
    s = step
    chest, hip = (1.02, 0.42), (1.04, -0.42)
    fl, fl_paw = _front_leg(-0.15, chest, (0.05 + 0.07 * max(0, s), 0.46 + 0.22 * s))
    fr, fr_paw = _front_leg(0.15, chest, (0.05 + 0.07 * max(0, -s), 0.46 - 0.22 * s))
    bl, bl_paw = _back_leg(-0.16, hip, (0.05 + 0.07 * max(0, -s), -0.48 - 0.20 * s))
    br, br_paw = _back_leg(0.16, hip, (0.05 + 0.07 * max(0, s), -0.48 + 0.20 * s))
    return dict(
        torso=[((0, 1.03, 0.42), 0.19), ((0, 0.99, 0.0), 0.165), ((0, 1.04, -0.42), 0.185)],
        neck=[((0, 1.08, 0.45), 0.13), ((0, 1.40, 0.62), 0.12)],
        legs=[fl, fr, bl, br], paws=[fl_paw, fr_paw, bl_paw, br_paw],
        tail=[(0, 1.02, -0.48), (0.03, 1.28, -0.74), (0.07, 1.58, -0.86), (0.10, 1.86, -0.84), (0.12, 2.02, -0.70)],
        head=(0, 1.64, 0.72), head_turn=head_turn, head_roll=head_roll)


def pose_sit(head_turn=0, head_roll=0, tail='up', tail_side=1):
    """Sitting upright, front paws together. tail='up' rises beside the body,
    tail='ground' curls along the floor with its tip turned up; tail_side=-1 mirrors it."""
    k = tail_side
    fl, fl_paw = _front_leg(-0.11, (0.93, 0.12), (0.05, 0.30))
    fr, fr_paw = _front_leg(0.11, (0.93, 0.12), (0.05, 0.30))
    return dict(
        torso=[((0, 0.30, -0.14), 0.25), ((0, 0.62, -0.02), 0.20), ((0, 0.95, 0.08), 0.175)],
        blobs=[((-0.17, 0.23, -0.04), 0.17), ((0.17, 0.23, -0.04), 0.17)],
        neck=[((0, 0.98, 0.10), 0.13), ((0, 1.28, 0.18), 0.12)],
        legs=[fl, fr], paws=[fl_paw, fr_paw, (-0.30, 0.05, 0.08), (0.30, 0.05, 0.08)],
        tail=[(0.05 * k, 0.24, -0.34), (0.32 * k, 0.26, -0.40), (0.50 * k, 0.54, -0.32),
              (0.55 * k, 0.92, -0.24), (0.50 * k, 1.22, -0.18)] if tail == 'up' else
             [(0.05 * k, 0.20, -0.34), (0.34 * k, 0.07, -0.42), (0.62 * k, 0.06, -0.30),
              (0.82 * k, 0.07, -0.06), (0.90 * k, 0.16, 0.06)],
        head=(0, 1.52, 0.22), head_turn=head_turn, head_roll=head_roll)


def pose_loaf(head_turn=0, head_roll=0):
    """Lying down, paws tucked, tail wrapped along the ground."""
    return dict(
        torso=[((0, 0.27, 0.30), 0.25), ((0, 0.30, -0.06), 0.29), ((0, 0.28, -0.44), 0.27)],
        neck=[((0, 0.38, 0.36), 0.15), ((0, 0.55, 0.48), 0.13)],
        legs=[], paws=[(-0.13, 0.05, 0.58), (0.13, 0.05, 0.58)],
        tail=[(0, 0.14, -0.68), (0.24, 0.07, -0.76), (0.46, 0.07, -0.50), (0.50, 0.07, -0.14),
              (0.40, 0.08, 0.10)],
        head=(0, 0.78, 0.58), head_turn=head_turn, head_roll=head_roll)


def pose_bow(head_turn=0, head_roll=-8):
    """Play bow / stretch: chest down, front legs flat forward, rear up."""
    fl = [((-0.11, 0.40, 0.42), 0.085), ((-0.11, 0.11, 0.80), 0.062), ((-0.11, 0.08, 1.06), 0.052)]
    fr = [((0.11, 0.40, 0.42), 0.085), ((0.11, 0.11, 0.78), 0.062), ((0.11, 0.08, 1.03), 0.052)]
    bl, bl_paw = _back_leg(-0.12, (1.06, -0.40), (0.05, -0.48))
    br, br_paw = _back_leg(0.12, (1.06, -0.40), (0.05, -0.44))
    return dict(
        torso=[((0, 0.42, 0.40), 0.18), ((0, 0.74, 0.0), 0.16), ((0, 1.06, -0.40), 0.185)],
        neck=[((0, 0.46, 0.46), 0.13), ((0, 0.58, 0.68), 0.12)],
        legs=[fl, fr, bl, br], paws=[(-0.11, 0.05, 1.10), (0.11, 0.05, 1.07), bl_paw, br_paw],
        tail=[(0, 1.08, -0.50), (0, 1.40, -0.72), (0, 1.78, -0.78), (0, 2.08, -0.68), (0, 2.30, -0.56)],
        head=(0, 0.80, 0.86), head_turn=head_turn, head_roll=head_roll)


def pose_leap(head_turn=0, head_roll=6):
    """Mid-air leap: stretched out, front legs reaching, back legs pushing off."""
    y = 1.25
    fl = [((-0.10, y, 0.44), 0.085), ((-0.10, y + 0.02, 0.84), 0.062), ((-0.10, y - 0.04, 1.18), 0.052)]
    fr = [((0.10, y, 0.44), 0.085), ((0.10, y - 0.10, 0.80), 0.062), ((0.10, y - 0.20, 1.10), 0.052)]
    bl = [((-0.12, y, -0.46), 0.14), ((-0.12, y - 0.24, -0.76), 0.085), ((-0.12, y - 0.36, -1.12), 0.055)]
    br = [((0.12, y, -0.46), 0.14), ((0.12, y - 0.16, -0.80), 0.085), ((0.12, y - 0.22, -1.18), 0.055)]
    return dict(
        torso=[((0, y + 0.02, 0.44), 0.185), ((0, y + 0.06, 0.0), 0.165), ((0, y, -0.46), 0.18)],
        neck=[((0, y + 0.06, 0.48), 0.13), ((0, y + 0.22, 0.80), 0.12)],
        legs=[fl, fr, bl, br],
        paws=[(-0.10, y - 0.05, 1.25), (0.10, y - 0.22, 1.17), (-0.12, y - 0.38, -1.20), (0.12, y - 0.24, -1.26)],
        tail=[(0, y + 0.04, -0.62), (0, y + 0.18, -0.94), (0, y + 0.32, -1.26), (0, y + 0.50, -1.50)],
        head=(0, y + 0.42, 1.00), head_turn=head_turn, head_roll=head_roll, airborne=True)


def pose_bust(head_turn=0, head_roll=0):
    """Head and shoulders for close-ups."""
    return dict(
        torso=[((0, 0.10, 0.0), 0.38), ((0, 0.70, 0.05), 0.26)],
        neck=[((0, 0.80, 0.08), 0.17), ((0, 1.10, 0.12), 0.15)],
        legs=[], paws=[], tail=[],
        head=(0, 1.40, 0.18), head_turn=head_turn, head_roll=head_roll)


# ---------------------------------------------------------------- geometry helpers

def _catmull(pts, n_per=10, closed=False):
    pts = [np.array(p, float) for p in pts]
    if len(pts) < 2:
        return pts
    out = []
    m = len(pts)
    rng = range(m) if closed else range(m - 1)
    for i in rng:
        p0 = pts[(i - 1) % m] if (closed or i > 0) else pts[0]
        p1, p2 = pts[i], pts[(i + 1) % m]
        p3 = pts[(i + 2) % m] if (closed or i + 2 < m) else pts[-1]
        for k in range(n_per):
            t = k / n_per
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    if not closed:
        out.append(pts[-1])
    return out


class _Mask:
    """Collects black shapes in canvas px; renders them to one antialiased mask."""

    def __init__(self):
        self.ops, self.xs, self.ys = [], [], []

    def _ext(self, x, y, r=0):
        self.xs += [x - r, x + r]
        self.ys += [y - r, y + r]

    def circle(self, c, r):
        self.ops.append(('c', c, r))
        self._ext(c[0], c[1], r)

    def capsule(self, a, ra, b, rb):
        self.circle(a, ra)
        self.circle(b, rb)
        dx, dy = b[0] - a[0], b[1] - a[1]
        d = math.hypot(dx, dy)
        if d <= abs(ra - rb) + 1e-6:
            return
        ang = math.atan2(dy, dx)
        beta = math.acos(max(-1, min(1, (ra - rb) / d)))
        p = [(a[0] + ra * math.cos(ang + beta), a[1] + ra * math.sin(ang + beta)),
             (b[0] + rb * math.cos(ang + beta), b[1] + rb * math.sin(ang + beta)),
             (b[0] + rb * math.cos(ang - beta), b[1] + rb * math.sin(ang - beta)),
             (a[0] + ra * math.cos(ang - beta), a[1] + ra * math.sin(ang - beta))]
        self.poly(p)

    def ellipse(self, c, rx, ry, ang=0.0):
        self.ops.append(('e', c, rx, ry, ang))
        self._ext(c[0], c[1], max(rx, ry))

    def poly(self, pts):
        self.ops.append(('p', [tuple(p) for p in pts]))
        for p in pts:
            self._ext(p[0], p[1])

    def render(self, x0, y0, w, h, ss):
        surf = cairo.ImageSurface(cairo.FORMAT_A8, w * ss, h * ss)
        ctx = cairo.Context(surf)
        ctx.scale(ss, ss)
        ctx.translate(-x0, -y0)
        ctx.set_source_rgba(0, 0, 0, 1)
        for op in self.ops:
            _op_path(ctx, op)
            ctx.fill()
        surf.flush()
        stride = surf.get_stride()
        a = np.frombuffer(surf.get_data(), np.uint8).reshape(h * ss, stride)[:, :w * ss]
        return a.copy()


def _op_path(ctx, op):
    ctx.new_path()
    if op[0] == 'c':
        ctx.arc(op[1][0], op[1][1], op[2], 0, 2 * math.pi)
    elif op[0] == 'e':
        ctx.save()
        ctx.translate(*op[1])
        ctx.rotate(op[4])
        ctx.scale(op[2], op[3])
        ctx.arc(0, 0, 1, 0, 2 * math.pi)
        ctx.restore()
    else:
        ctx.move_to(*op[1][0])
        for q in op[1][1:]:
            ctx.line_to(*q)
        ctx.close_path()


def _covered(ops, pt):
    """Is canvas point pt inside any of these mask shapes?"""
    surf = cairo.ImageSurface(cairo.FORMAT_A8, 1, 1)
    ctx = cairo.Context(surf)
    for op in ops:
        _op_path(ctx, op)
        if ctx.in_fill(pt[0], pt[1]):
            return True
    return False


def _rough_alpha(mask, H, ss, seed):
    """Binary mask -> alpha with a brush-like irregular edge (supersampled)."""
    m = mask >= 128
    sdf = ndimage.distance_transform_edt(m) - ndimage.distance_transform_edt(~m)
    rng = np.random.default_rng(seed)
    n1 = ndimage.gaussian_filter(rng.standard_normal(m.shape), sigma=max(1.0, 0.03 * H * ss))
    n1 /= n1.std() + 1e-9
    n2 = ndimage.gaussian_filter(rng.standard_normal(m.shape), sigma=max(0.7, 0.006 * H * ss))
    n2 /= n2.std() + 1e-9
    a = np.clip(sdf + (n1 * 0.006 + n2 * 0.0025) * H * ss + 0.5, 0, 1)
    if ss > 1:
        hh, ww = a.shape[0] // ss, a.shape[1] // ss
        a = a[:hh * ss, :ww * ss].reshape(hh, ss, ww, ss).mean(axis=(1, 3))
    return a


def _np_view(surface):
    surface.flush()
    w, h, stride = surface.get_width(), surface.get_height(), surface.get_stride()
    return np.ndarray((h, w, 4), np.uint8, surface.get_data(), strides=(stride, 4, 1))


# ---------------------------------------------------------------- ink strokes

def _hair(ctx, root, ang, length, width, bend=0.0):
    """One tapered brush flick: root width -> sharp tip, slightly curved."""
    ca, sa = math.cos(ang), math.sin(ang)
    nx, ny = -sa, ca
    tip = (root[0] + ca * length + nx * bend * length, root[1] + sa * length + ny * bend * length)
    mid = (root[0] + ca * length * 0.5 + nx * bend * length * 0.35,
           root[1] + sa * length * 0.5 + ny * bend * length * 0.35)
    w = width / 2
    ctx.move_to(root[0] + nx * w, root[1] + ny * w)
    ctx.curve_to(mid[0] + nx * w * 0.5, mid[1] + ny * w * 0.5, tip[0], tip[1], tip[0], tip[1])
    ctx.curve_to(tip[0], tip[1], mid[0] - nx * w * 0.5, mid[1] - ny * w * 0.5,
                 root[0] - nx * w, root[1] - ny * w)
    ctx.close_path()


def _drip(ctx, x, y, length, width):
    ctx.rectangle(x - width / 2, y - width, width, length + width)
    ctx.arc(x, y + length, width * 0.75, 0, 2 * math.pi)


def _heart_path(ctx, cx, cy, size, ang=0.0):
    pts = []
    for i in range(48):
        t = 2 * math.pi * i / 48
        x = 16 * math.sin(t) ** 3
        y = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
        x, y = x / 32 * size, y / 32 * size
        ca, sa = math.cos(ang), math.sin(ang)
        pts.append((cx + x * ca - y * sa, cy + x * sa + y * ca))
    ctx.move_to(*pts[0])
    for p in pts[1:]:
        ctx.line_to(*p)
    ctx.close_path()


# ---------------------------------------------------------------- head

class _Head:
    """Head-local coords (u right, v down; cheek-to-cheek width = 1) -> canvas px."""

    def __init__(self, cx, cy, s, phi, roll):
        # a cartoon head never goes to a flat profile: cheat to 3/4 (62 deg off front/back)
        c, sn = math.cos(phi), math.sin(phi)
        a = math.atan2(sn, c)
        lim = math.radians(62)
        if abs(a) <= math.pi / 2:
            a = max(-lim, min(lim, a))
        else:
            a = math.copysign(max(math.pi - lim, abs(a)), a)
        phi = a
        self.cx, self.cy, self.s, self.phi = cx, cy, s, phi
        self.cr, self.sr = math.cos(roll), math.sin(roll)
        self.roll = roll

    def lp_raw(self, u, v):
        return (self.cx + (u * self.cr - v * self.sr) * self.s,
                self.cy + (u * self.sr + v * self.cr) * self.s)

    def lp(self, u, v):
        """Silhouette placement (does not slide with yaw)."""
        return self.lp_raw(u * (1 - 0.16 * abs(math.sin(self.phi))) + 0.05 * math.sin(self.phi), v)

    def _alpha(self, u):
        return math.asin(max(-1.0, min(1.0, u / HEAD_R)))

    @property
    def fphi(self):
        return self.phi

    def hp(self, u, v):
        """Sphere placement (facial features)."""
        return self.lp_raw(HEAD_R * math.sin(self._alpha(u) + self.fphi), v)

    def vis(self, u):
        return math.cos(self._alpha(u) + self.fphi)

    def kx(self, u):
        a = self._alpha(u)
        return max(0.0, math.cos(a + self.fphi)) / max(0.35, math.cos(a))

    def ang(self, a):
        """Head-local direction angle -> canvas angle."""
        return a + self.roll


# Measured off the sheet's head close-up (width 1 between the cheeks at eye level).
FACE_OUTLINE = [(0, -0.50), (0.22, -0.50), (0.45, -0.42), (0.50, -0.18), (0.51, 0.03), (0.50, 0.15),
                (0.45, 0.25), (0.27, 0.32), (0, 0.34), (-0.27, 0.32), (-0.45, 0.25), (-0.50, 0.15),
                (-0.51, 0.03), (-0.50, -0.18), (-0.45, -0.42), (-0.22, -0.50)]
# right ear (mirrored for the left): flat dip between the ears at v=-0.49, tall sharp tip
EAR_R = [(0.08, -0.40), (0.10, -0.49), (0.37, -0.87), (0.44, -0.66), (0.48, -0.42), (0.50, -0.12),
         (0.25, -0.15)]
EAR_CU = 0.30           # ear centre's lateral offset in a front view
# cheek hair, viewer's right side: (v at the edge, angle deg below horizontal, length, root width)
CHEEK_HAIR = [(-0.20, -12, 0.08, 0.020), (-0.08, -4, 0.13, 0.024), (0.01, 4, 0.18, 0.026),
              (0.07, 11, 0.20, 0.026), (0.12, 19, 0.17, 0.026), (0.17, 28, 0.19, 0.024),
              (0.21, 40, 0.13, 0.022), (0.25, 55, 0.10, 0.020)]
CHIN_DRIPS = [(-0.40, 0.08, 0.016), (-0.31, 0.13, 0.014), (-0.18, 0.05, 0.012), (0.20, 0.06, 0.012),
              (0.34, 0.12, 0.016), (0.42, 0.07, 0.013)]


def _head_silhouette(m, hd):
    pts = [hd.lp(u, v) for u, v in FACE_OUTLINE]
    m.poly(_catmull(pts, 5, closed=True))
    c, sn = math.cos(hd.phi), math.sin(hd.phi)
    ears = []
    for side in (-1, 1):
        ear = [(u * side, v) for u, v in EAR_R]             # side=-1: viewer's-left ear
        cu = EAR_CU * side
        # turned heads keep both ears (as on the sheet): they drift toward the face side,
        # the ear on the face side narrows
        x = EAR_CU * side * (1 - 0.25 * abs(sn)) + 0.10 * sn
        w = max(0.55, abs(c)) if side * sn > 0 else 1.0
        poly = [hd.lp_raw(x + (u - cu) * w, v) for u, v in ear]
        m.poly(poly)
        ears.append(poly)
    # a few thick tufts at the lower cheeks so the silhouette itself is jagged
    for side in (-1, 1):
        for v, a, L, w in [(0.10, 15, 0.07, 0.05), (0.20, 35, 0.07, 0.05), (0.27, 60, 0.05, 0.045)]:
            b = hd.lp(0.48 * side, v)
            ang = hd.ang(math.radians(a) if side > 0 else math.pi - math.radians(a))
            dx, dy = math.cos(ang), math.sin(ang)
            L, w = L * hd.s, w * hd.s
            m.poly([(b[0] - dy * w / 2, b[1] + dx * w / 2), (b[0] + dx * L, b[1] + dy * L),
                    (b[0] + dy * w / 2, b[1] - dx * w / 2)])
    if abs(sn) > 0.25:                       # muzzle bump in profile
        m.circle(hd.lp(0.46 * sn, 0.20), 0.10 * abs(sn) * hd.s)
    return ears


def _head_ink(ctx, hd, ears):
    """Cheek hair, top hairs, ear-tip overshoot strokes, chin drips."""
    s = hd.s
    for side in (-1, 1):
        for v, a, L, w in CHEEK_HAIR:
            root = hd.lp(0.47 * side, v)
            ang = hd.ang(math.radians(a) if side > 0 else math.pi - math.radians(a))
            _hair(ctx, root, ang, (L + 0.04) * s, w * s, bend=0.05 * side)
    for (u, a, L) in [(-0.04, -100, 0.07), (0.05, -78, 0.06), (0.0, -90, 0.05)]:
        _hair(ctx, hd.lp(u, -0.47), hd.ang(math.radians(a)), L * s, 0.016 * s)
    for poly in ears:
        tip, outer = poly[2], poly[3]
        for k, (f, over) in enumerate([(0.0, 0.10), (0.25, 0.07)]):
            r = (outer[0] + (tip[0] - outer[0]) * f, outer[1] + (tip[1] - outer[1]) * f)
            ang = math.atan2(tip[1] - outer[1], tip[0] - outer[0]) + (0.06 if k else -0.04)
            L = math.hypot(tip[0] - r[0], tip[1] - r[1]) + over * s
            _hair(ctx, r, ang, L, 0.012 * s)
        inner = poly[1]
        ang = math.atan2(tip[1] - inner[1], tip[0] - inner[0]) + 0.05
        _hair(ctx, (inner[0] + (tip[0] - inner[0]) * 0.4, inner[1] + (tip[1] - inner[1]) * 0.4),
              ang, math.hypot(tip[0] - inner[0], tip[1] - inner[1]) * 0.6 + 0.06 * s, 0.010 * s)
        # two little hairs on the ear's outer edge
        for f, L in [(0.45, 0.06), (0.75, 0.05)]:
            p0, p1 = poly[4], poly[5]
            r = (p0[0] + (p1[0] - p0[0]) * f, p0[1] + (p1[1] - p0[1]) * f)
            out = math.atan2(p1[1] - p0[1], p1[0] - p0[0]) + (math.pi / 2 if r[0] > hd.cx else -math.pi / 2)
            _hair(ctx, r, out - 0.5 * (1 if r[0] > hd.cx else -1), L * s, 0.014 * s)
    for u, L, w in CHIN_DRIPS:
        x, y = hd.lp(u, 0.30 - 0.06 * (abs(u) > 0.3))
        _drip(ctx, x, y, L * s, w * s)
    ctx.set_source_rgb(*INK)
    ctx.fill()


def _feature(ctx, hd, u, v, min_vis=0.12):
    """Enter a feature's local frame (head units). Returns False if it faces away."""
    if hd.vis(u) < min_vis:
        return False
    p = hd.hp(u, v)
    ctx.save()
    ctx.translate(*p)
    ctx.rotate(hd.roll)
    ctx.scale(hd.s * hd.kx(u), hd.s)
    return True


def _ellipse(ctx, cx, cy, rx, ry):
    ctx.save()
    ctx.translate(cx, cy)
    ctx.scale(rx, ry)
    ctx.arc(0, 0, 1, 0, 2 * math.pi)
    ctx.restore()


def _eye(ctx, hd, side, f):
    u, v = 0.23 * side, 0.06
    if not _feature(ctx, hd, u, v, 0.08):
        return
    inner = -side                        # inner corner is toward the nose
    kind = f.get('eyes', 'slit')
    lx, ly = f.get('look', (0, 0))
    if kind == 'slit':
        rx, ry = 0.148, 0.15
        op, sl = f.get('open', 0.67), f.get('slant', 0.53)
        y0 = -ry + (1 - op) * 2 * ry

        def lid(x):
            return y0 + sl * x * inner
        ctx.move_to(-1, lid(-1))
        ctx.line_to(1, lid(1))
        ctx.line_to(1, 1)
        ctx.line_to(-1, 1)
        ctx.close_path()
        ctx.clip()
        _ellipse(ctx, 0, 0, rx, ry)
        ctx.clip_preserve()
        ctx.set_source_rgb(*EYE)
        ctx.fill()
        # slit pupil hanging from the lid, a gold sliver beside it
        px = lx * 0.06 + 0.012 * inner
        top = lid(px) - 0.02
        bot = min(0.11, top + 0.20) + ly * 0.03
        for dx, col, w in [(0.013, GOLD, 0.008), (0.0, PUPIL, 0.013)]:
            ctx.move_to(px + dx - w, top)
            ctx.line_to(px + dx + w, top)
            ctx.curve_to(px + dx + w, (top + bot) / 2, px + dx + w * 0.3, bot, px + dx, bot)
            ctx.curve_to(px + dx - w * 0.3, bot, px + dx - w, (top + bot) / 2, px + dx - w, top)
            ctx.close_path()
            ctx.set_source_rgb(*col)
            ctx.fill()
    elif kind == 'round':
        _ellipse(ctx, 0, -0.04, 0.155, 0.21)
        ctx.set_source_rgb(*EYE)
        ctx.fill()
        px, py = lx * 0.06, -0.04 + ly * 0.06
        _ellipse(ctx, px + 0.012, py, 0.016, 0.13)
        ctx.set_source_rgb(*GOLD)
        ctx.fill()
        _ellipse(ctx, px, py, 0.013, 0.13)
        ctx.set_source_rgb(*PUPIL)
        ctx.fill()
    elif kind in ('closed', 'happy'):
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        if kind == 'closed':
            # the sheet's sleepy eye: a long thin line, rising toward the outer corner
            ctx.set_line_width(0.016)
            ctx.move_to(0.13 * inner, 0.09)
            ctx.curve_to(0.04 * inner, 0.11, -0.08 * inner, 0.09, -0.15 * inner, 0.03)
        else:
            # the sheet's 'silly' eye: a wide thin arch
            ctx.set_line_width(0.018)
            ctx.move_to(-0.14, 0.08)
            ctx.curve_to(-0.08, -0.03, 0.08, -0.03, 0.14, 0.08)
        ctx.set_source_rgb(*rgb('#efe3a0'))
        ctx.stroke()
    elif kind == 'heart':
        _heart_path(ctx, 0, 0.03, 0.34)
        ctx.set_source_rgb(*rgb('#f26b7a'))
        ctx.fill()
    ctx.restore()


def _tongue(ctx, hd):
    """The sheet's 'silly' tongue: big, pink, hanging past the chin, tipped to one side."""
    if not _feature(ctx, hd, 0.03, 0.262):
        return
    ctx.rotate(-0.18)
    ctx.move_to(-0.055, 0.0)
    ctx.line_to(0.055, 0.0)
    ctx.curve_to(0.065, 0.12, 0.06, 0.20, 0.0, 0.20)
    ctx.curve_to(-0.06, 0.20, -0.065, 0.12, -0.055, 0.0)
    ctx.close_path()
    ctx.set_source_rgb(*TONGUE)
    ctx.fill_preserve()
    ctx.set_source_rgb(*rgb('#c9566a'))
    ctx.set_line_width(0.009)
    ctx.stroke()
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.move_to(0.0, 0.03)
    ctx.line_to(0.0, 0.11)
    ctx.stroke()
    ctx.restore()


def _nose_mouth(ctx, hd, f):
    if _feature(ctx, hd, 0, 0.225):
        ctx.move_to(-0.026, -0.012)
        ctx.curve_to(-0.01, -0.018, 0.01, -0.018, 0.026, -0.012)
        ctx.line_to(0.0, 0.016)
        ctx.close_path()
        ctx.set_source_rgb(*NOSE)
        ctx.fill()
        ctx.restore()
    mouth = f.get('mouth', 'smile')
    if not _feature(ctx, hd, 0, 0.262):
        return
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.set_line_width(0.012)
    ctx.set_source_rgb(*NOSE)
    if mouth in ('smile', 'tongue'):
        ctx.move_to(-0.085, -0.014)
        ctx.curve_to(-0.06, 0.016, -0.015, 0.018, 0.0, -0.004)
        ctx.curve_to(0.015, 0.018, 0.06, 0.016, 0.085, -0.014)
        ctx.stroke()
    elif mouth == 'flat':
        ctx.move_to(-0.04, 0.004)
        ctx.line_to(0.04, 0.0)
        ctx.stroke()
    elif mouth == 'frown':
        ctx.move_to(-0.05, 0.012)
        ctx.curve_to(-0.02, -0.01, 0.02, -0.01, 0.05, 0.012)
        ctx.stroke()
    elif mouth in ('o', 'scream'):
        rx, ry = (0.03, 0.035) if mouth == 'o' else (0.10, 0.09)
        cy = 0.02 if mouth == 'o' else 0.04
        _ellipse(ctx, 0, cy, rx, ry)
        ctx.set_source_rgb(*MOUTH)
        ctx.fill_preserve()
        ctx.save()
        ctx.clip()
        _ellipse(ctx, 0, cy + ry * 0.85, rx * 0.75, ry * 0.5)
        ctx.set_source_rgb(*TONGUE)
        ctx.fill()
        ctx.restore()
        _ellipse(ctx, 0, cy, rx, ry)
        ctx.set_source_rgb(*NOSE)
        ctx.set_line_width(0.01)
        ctx.stroke()
    ctx.restore()


def _extras(ctx, hd, f):
    ex = f.get('extra')
    s = hd.s
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    if ex == 'anger' and _feature(ctx, hd, 0.26, -0.30, 0.0):
        ctx.set_line_width(0.02)
        for k in range(4):
            ctx.save()
            ctx.rotate(k * math.pi / 2 + math.pi / 4)
            ctx.move_to(0.022, -0.055)
            ctx.curve_to(0.012, -0.028, 0.028, -0.018, 0.055, -0.022)
            ctx.restore()
        ctx.set_source_rgb(*RED)
        ctx.stroke()
        ctx.restore()
        cx, cy = hd.lp(0, 0)
        ctx.set_line_width(0.02 * s)
        for (a, r0, r1) in [(-30, 0.78, 0.95), (-15, 0.80, 0.98)]:
            ang = math.radians(a)
            ctx.move_to(cx + math.cos(ang) * r0 * s, cy + math.sin(ang) * r0 * s)
            ctx.line_to(cx + math.cos(ang) * r1 * s, cy + math.sin(ang) * r1 * s)
        ctx.set_source_rgb(*INK)
        ctx.stroke()
    elif ex in ('question', 'hearts', 'shock'):
        cx, cy = hd.lp(0, 0)
        if ex == 'question':
            ctx.select_font_face('Segoe Print', cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
            for (dx, dy, sz) in [(0.62, -0.42, 0.30), (0.80, -0.20, 0.22)]:
                ctx.set_font_size(sz * s)
                ctx.move_to(cx + dx * s, cy + dy * s)
                ctx.set_source_rgb(*INK)
                ctx.show_text('?')
        elif ex == 'hearts':
            for (dx, dy, sz) in [(0.68, -0.42, 0.16), (0.80, -0.66, 0.11)]:
                _heart_path(ctx, cx + dx * s, cy + dy * s, sz * s, 0.25)
                ctx.set_source_rgb(*INK)
                ctx.fill()
        else:
            ctx.set_line_width(0.022 * s)
            for (a, r0, r1) in [(-122, 0.98, 1.14), (-95, 1.0, 1.18), (-58, 0.98, 1.14)]:
                ang = math.radians(a)
                ctx.move_to(cx + math.cos(ang) * r0 * s * 0.7, cy + math.sin(ang) * r0 * s)
                ctx.line_to(cx + math.cos(ang) * r1 * s * 0.7, cy + math.sin(ang) * r1 * s)
            ctx.set_source_rgb(*INK)
            ctx.stroke()


# ---------------------------------------------------------------- main entry

def _tail_radius(t):
    """As on the sheet: wide where it grows out of the rump, a slim middle, then a long
    oval paddle at the tip."""
    if t < 0.3:
        k = t / 0.3
        return 0.16 - 0.075 * (k * k * (3 - 2 * k))
    if t < 0.6:
        return 0.085
    k = min(1.0, (t - 0.6) / 0.3)
    return 0.085 + 0.06 * math.sin(math.pi / 2 * k)


FUR = 1.45            # thick fur: every body radius is scaled by this


def draw_cat(surface, pose, ox, oy, H, yaw=0.0, face='smug', seed=7, shadow=True, ss=2, fur=FUR):
    """Draw the cat onto a cairo ARGB32 surface.

    ox, oy: canvas px of the ground point under the cat's centre. H: head width in px.
    yaw: degrees (0 = facing the camera, 90 = facing right, 180 = back).
    face: a FACES key or a dict.
    """
    f = FACES[face] if isinstance(face, str) else face
    yw = math.radians(yaw)
    cy_, sy_ = math.cos(yw), math.sin(yw)

    def P(p):
        x, y, z = p
        return (ox + (x * cy_ + z * sy_) * H, oy - y * H)

    m = _Mask()
    segs, leg_segs = [], []
    chains = [pose.get('torso', []), pose.get('neck', [])] + list(pose.get('legs', []))
    for ci, chain in enumerate(chains):
        for (pa, ra), (pb, rb) in zip(chain, chain[1:]):
            a, b = P(pa), P(pb)
            m.capsule(a, ra * fur * H, b, rb * fur * H)
            segs.append((a, ra * fur * H, b, rb * fur * H))
            if ci >= 2:
                leg_segs.append(segs[-1])
        if len(chain) == 1:
            m.circle(P(chain[0][0]), chain[0][1] * fur * H)
    for (p, r) in pose.get('blobs', []):
        m.circle(P(p), r * fur * H)
    paw_rx, paw_ry = (0.12 + 0.03 * abs(sy_)) * H, 0.08 * H
    paws_px = [P(p) for p in pose.get('paws', [])]
    for c in paws_px:
        m.ellipse((c[0], c[1] - 0.01 * H), paw_rx, paw_ry)
    # tail
    tail_pts, tail_r = [], []
    tail_ops = (len(m.ops), len(m.ops))
    if pose.get('tail'):
        sm = _catmull([P(p) for p in pose['tail']], 12)
        n = len(sm)
        tail_r = [_tail_radius(i / (n - 1)) * H for i in range(n)]
        for i in range(n - 1):
            m.capsule(tuple(sm[i]), tail_r[i], tuple(sm[i + 1]), tail_r[i + 1])
        tail_pts = sm
        tail_ops = (tail_ops[0], len(m.ops))
    # head
    hp3 = pose['head']
    hc = P(hp3)
    phi = yw + math.radians(pose.get('head_turn', 0))
    hd = _Head(hc[0], hc[1], H * pose.get('head_scale', 1.0), phi, math.radians(pose.get('head_roll', 0)))
    ears = _head_silhouette(m, hd)

    # ---- render the silhouette
    pad = int(0.25 * H) + 4
    x0 = int(math.floor(min(m.xs))) - pad
    y0 = int(math.floor(min(m.ys))) - pad
    x1 = int(math.ceil(max(m.xs))) + pad
    y1 = int(math.ceil(max(m.ys))) + pad
    W, Hh = surface.get_width(), surface.get_height()
    cx0, cy0, cx1, cy1 = max(0, x0), max(0, y0), min(W, x1), min(Hh, y1)
    if cx1 <= cx0 or cy1 <= cy0:
        return

    ctx = cairo.Context(surface)
    if shadow:
        if pose.get('airborne'):
            sx0, sx1, al = ox - 0.8 * H, ox + 0.8 * H, 0.07
        else:
            xs = [p[0] for p in paws_px] or [ox]
            sx0, sx1, al = min(xs) - 0.22 * H, max(xs) + 0.22 * H, 0.10
        _ellipse(ctx, (sx0 + sx1) / 2, oy + 0.01 * H, (sx1 - sx0) / 2, 0.06 * H)
        ctx.set_source_rgba(0, 0, 0, al)
        ctx.fill()

    mask = m.render(x0, y0, x1 - x0, y1 - y0, ss)
    alpha = _rough_alpha(mask, H, ss, seed)

    # plain black: no coloured lines anywhere on the body (Anka, 2026-10-25)
    dst = _np_view(surface)
    sl = (slice(cy0, cy1), slice(cx0, cx1))
    ls = (slice(cy0 - y0, cy1 - y0), slice(cx0 - x0, cx1 - x0))
    a = alpha[ls][..., None]
    D = dst[sl].astype(np.float32) / 255.0
    ink = np.array([INK[2], INK[1], INK[0], 1.0], np.float32)
    D = ink * a + D * (1 - a)
    dst[sl] = np.clip(D * 255 + 0.5, 0, 255).astype(np.uint8)
    surface.mark_dirty()

    ctx = cairo.Context(surface)
    _head_ink(ctx, hd, ears)
    if len(tail_pts) > 4:                    # drip off the paddle tip
        p = tail_pts[-1]
        if p[1] >= tail_pts[-4][1]:
            _drip(ctx, p[0] + 0.02 * H, p[1] + tail_r[-1] * 0.7, 0.06 * H, 0.012 * H)
            ctx.set_source_rgb(*INK)
            ctx.fill()

    if math.cos(hd.phi) > -0.35:
        ctx.save()
        face_pts = _catmull([hd.lp(u, v) for u, v in FACE_OUTLINE], 5, closed=True)
        ctx.move_to(*face_pts[0])
        for q in face_pts[1:]:
            ctx.line_to(*q)
        ctx.close_path()
        ctx.clip()
        _eye(ctx, hd, -1, f)
        _eye(ctx, hd, 1, f)
        _nose_mouth(ctx, hd, f)
        ctx.restore()
        if f.get('mouth') == 'tongue':           # hangs past the chin, so drawn unclipped
            _tongue(ctx, hd)
    _extras(ctx, hd, f)
