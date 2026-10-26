"""The girl, v3: drawn in code (cairo vectors) after the master sheet's big standing figure
(characters/girl/girl_master_red.png -> characters/rig/girl_src.png), redrawn every frame.

The vector model (characters/girl/girl3_model.npz, measured by tools/trace_girl3.py) holds
every part as shapes: hair behind, far leg, arms, shirt, shorts, near leg, neck, face, the
hair in front (fringe + the lock over the chest); each with its base fill, shade / light
fills and interior ink lines, plus the face features (eyes: white, iris, pupil, highlights;
brow, nose, mouth). Drawing = filling and stroking those paths after moving their points
with the pose's bones, so the head turns and tilts, the hair swings, the legs step, and the
eyes blink / look / change expression, the mouth talks.

    draw_girl(ctx, x, y, scale, pose, expr, blink, look, talk)   # (x, y) = under her feet
"""
import math
import os

import cairo
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL = os.path.join(ROOT, 'characters', 'girl', 'girl3_model.npz')

INK = (38 / 255, 14 / 255, 10 / 255)
LASH = (26 / 255, 14 / 255, 12 / 255)
MOUTH_IN = (150 / 255, 58 / 255, 58 / 255)
TONGUE = (226 / 255, 120 / 255, 120 / 255)
TEETH = (252 / 255, 250 / 255, 248 / 255)
IRIS = (92 / 255, 88 / 255, 96 / 255)
OUTLINE_W = {'hair_back': 2.8, 'hair_front': 2.4, 'face': 2.6, 'neck': 2.2}
FEET = (165.0, 1180.0)

# bones: name -> (parent, pivot in src px)
BONES = {
    'root': (None, FEET),
    'hips': ('root', (165.0, 640.0)),
    'thigh_n': ('hips', (120.0, 660.0)), 'shin_n': ('thigh_n', (124.0, 840.0)), 'foot_n': ('shin_n', (128.0, 1040.0)),
    'thigh_f': ('hips', (205.0, 660.0)), 'shin_f': ('thigh_f', (193.3, 839.7)), 'foot_f': ('shin_f', (179.8, 1039.2)),
    'chest': ('hips', (172.0, 520.0)),
    'neck': ('chest', (180.0, 278.0)),
    'head': ('neck', (182.0, 250.0)),
    'lockL': ('chest', (60.0, 250.0)), 'lockR': ('chest', (278.0, 250.0)), 'lockF': ('chest', (135.0, 240.0)),
}
BONE_NAMES = list(BONES)


# ------------------------------------------------------------------ the model

_model = None


def model():
    global _model
    if _model is not None:
        return _model
    z = np.load(MODEL)
    parts = [str(p) for p in z['parts']]
    tags = [str(t) for t in z['fill_tags']]
    P = {p: dict(fills=[], lines=[]) for p in parts}
    fill_index = {}
    for k, (pi, fi, r, g, b, _) in enumerate(z['fill_meta']):
        f = dict(tag=tags[k], col=(r / 255, g / 255, b / 255), shapes={})
        P[parts[pi]]['fills'].append(f)
        fill_index[(int(pi), int(fi))] = f
    i = 0
    for L, (pi, fi, si) in zip(z['ring_len'], z['ring_meta']):
        fill_index[(int(pi), int(fi))]['shapes'].setdefault(int(si), []).append(z['ring_pts'][i:i + L].astype(np.float64))
        i += L
    i = 0
    for L, pi in zip(z['line_len'], z['line_meta']):
        P[parts[pi]]['lines'].append((z['line_pts'][i:i + L].astype(np.float64), z['line_w'][i:i + L]))
        i += L
    feats = {}
    i = 0
    for L, meta in zip(z['feat_len'], z['feat_meta']):
        f, kind, si = str(meta).split('|')
        feats.setdefault(f, {}).setdefault(kind, {}).setdefault(int(si), []).append(
            z['feat_pts'][i:i + L].astype(np.float64))
        i += L
    _model = dict(order=parts, parts=P, feats=feats, weights={})
    return _model


# ------------------------------------------------------------------ skinning

def _band(v, a, b):
    return np.clip((v - a) / max(1e-6, b - a), 0, 1)


def _bone_weights(part, pts):
    """Per-point weights over BONES for a part (smooth bands, by position)."""
    W = np.zeros((len(pts), len(BONE_NAMES)))
    ix = {n: i for i, n in enumerate(BONE_NAMES)}
    x, y = pts[:, 0], pts[:, 1]
    if part == 'feat':
        W[:, ix['head']] = 1
    elif part in ('face', 'hair_front', 'hair_back'):
        # the top of the head rides the head; long hair below hangs from the shoulders (its
        # own lock bones, children of the chest), blending smoothly in between
        hang = _band(y, 215, 330) if part != 'face' else np.zeros(len(y))
        lowL = hang * (x < 125)
        lowR = hang * (x > 240)
        lowF = hang * (x >= 125) * (x <= 240)
        W[:, ix['lockL']] = lowL
        W[:, ix['lockR']] = lowR
        W[:, ix['lockF']] = lowF
        W[:, ix['head']] = 1 - lowL - lowR - lowF
    elif part == 'hair_under':
        # the hair's silhouette riding head + chest only: fills any tear the hanging locks open
        k = _band(y, 230, 330)
        W[:, ix['head']] = 1 - k
        W[:, ix['chest']] = k
    elif part == 'neck':
        k = _band(y, 230, 270)
        W[:, ix['head']] = 1 - k
        W[:, ix['neck']] = k
    elif part in ('shirt', 'arms'):
        k = _band(y, 540, 600)
        W[:, ix['chest']] = 1 - k
        W[:, ix['hips']] = k
    elif part == 'shorts':
        legk = _band(y, 610, 700)
        near = (x < 165).astype(float)
        W[:, ix['hips']] = 1 - legk
        W[:, ix['thigh_n']] = legk * near
        W[:, ix['thigh_f']] = legk * (1 - near)
    elif part in ('leg_near', 'leg_far'):
        s = '_n' if part == 'leg_near' else '_f'
        top = 1 - _band(y, 640, 670)
        knee = _band(y, 810, 870)
        ankle = _band(y, 1020, 1060)
        W[:, ix['hips']] = top
        W[:, ix['thigh' + s]] = (1 - top) * (1 - knee)
        W[:, ix['shin' + s]] = (1 - top) * knee * (1 - ankle)
        W[:, ix['foot' + s]] = (1 - top) * knee * ankle
    else:
        W[:, ix['root']] = 1
    return W


def _mat(rot=0.0, sx=1.0, sy=1.0, dx=0.0, dy=0.0, px=0.0, py=0.0):
    c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    a = np.array([[c * sx, -s * sy], [s * sx, c * sy]])
    p = np.array([px, py])
    t = p + a @ (np.array([dx, dy]) - p)
    m = np.eye(3)
    m[:2, :2] = a
    m[:2, 2] = t
    return m


def transforms(pose):
    G = {}
    for n, (parent, piv) in BONES.items():
        p = pose.get(n, {})
        m = _mat(p.get('rot', 0.0), p.get('sx', 1.0), p.get('sy', 1.0), p.get('dx', 0.0), p.get('dy', 0.0), *piv)
        if 'ox' in p or 'oy' in p:
            t = np.eye(3)
            t[:2, 2] = (p.get('ox', 0.0), p.get('oy', 0.0))
            m = t @ m
        G[n] = (G[parent] @ m) if parent else m
    return G


def _with_gravity(pose):
    """Long hair hangs down: the lock bones undo most of the root / hips / chest tilt."""
    g = float(pose.get('gravity', 1.0))
    if not g:
        return pose
    tilt = g * sum(pose.get(b, {}).get('rot', 0.0) for b in ('root', 'hips', 'chest'))
    if not tilt:
        return pose
    pose = dict(pose)
    for b, k in (('lockL', 0.5), ('lockR', 0.5), ('lockF', 0.45)):
        q = dict(pose.get(b, {}))
        q['rot'] = q.get('rot', 0.0) - k * tilt
        pose[b] = q
    return pose


class _Skin:
    def __init__(self, pose):
        G = transforms(_with_gravity(pose))
        self.stack = np.stack([G[n] for n in BONE_NAMES])
        self.cache = model()['weights']
        self.turn = pose.get('turn', 0.0)
        self.nod = pose.get('nod', 0.0)

    def __call__(self, part, pts, key):
        if key is None:
            W = _bone_weights(part, pts)
        else:
            k = (part, key)
            if k not in self.cache:
                self.cache[k] = _bone_weights(part, pts)
            W = self.cache[k]
        P = pts
        if (self.turn or self.nod) and part in ('face', 'hair_front', 'feat'):
            # a head turn / nod by parallax: the face moves more than the head's outline
            if part == 'feat':
                g = np.ones(len(pts))
            else:
                g = np.clip(1 - np.hypot((pts[:, 0] - 195) / 95, (pts[:, 1] - 165) / 85), 0, 1) ** 1.3
                g = g * (pts[:, 1] < 240)
            P = pts + np.c_[self.turn * 10 * g, self.nod * 8 * g]
        V = np.c_[P, np.ones(len(P))]
        return np.einsum('nb,bij,nj->ni', W, self.stack, V)[:, :2]


# ------------------------------------------------------------------ drawing helpers

def _rings_path(ctx, rings):
    for r in rings:
        ctx.move_to(*r[0])
        for p in r[1:]:
            ctx.line_to(*p)
        ctx.close_path()


def _stroke_var(ctx, pts, wid, col=INK):
    """A polyline whose width changes along it (a filled ribbon, tapered at the ends)."""
    n = len(pts)
    if n < 2:
        return
    d = np.gradient(pts, axis=0)
    nrm = np.c_[-d[:, 1], d[:, 0]]
    nrm /= np.maximum(1e-6, np.hypot(nrm[:, 0], nrm[:, 1]))[:, None]
    t = np.linspace(0, 1, n)
    taper = np.clip(np.minimum(t, 1 - t) * n / 1.5, 0.35, 1.0)
    hw = (np.asarray(wid) * taper / 2)[:, None]
    L, R = pts + nrm * hw, pts - nrm * hw
    ctx.move_to(*L[0])
    for p in L[1:]:
        ctx.line_to(*p)
    for p in R[::-1]:
        ctx.line_to(*p)
    ctx.close_path()
    ctx.set_source_rgb(*col)
    ctx.fill()


# ------------------------------------------------------------------ the face

EXPR = {
    'smile':     dict(open=1.0, mouth='smile'),
    'neutral':   dict(open=1.0, mouth='flat'),
    'happy':     dict(closed='happy', mouth='open'),
    'bored':     dict(open=0.78, mouth='flat'),
    'annoyed':   dict(open=0.68, mouth='flat', brow=-1),
    'angry':     dict(open=0.75, mouth='shout', brow=-2),
    'surprised': dict(open=1.12, mouth='o', brow=1.5),
    'sleep':     dict(closed='sleep', mouth='flat'),
}
EYE_LOW = {'eye_n': 192.0, 'eye_f': 170.0}       # lower lid line (src px)
# the far eye is drawn much smaller on the sheet (3/4 view); it is enlarged to match the near
# eye's height so the two read as the same eyes (Anka, 2026-10-26)
EYE_GROW = {'eye_n': (1.0, 1.0), 'eye_f': (1.22, 1.24)}


def _eye(ctx, skin, name, F, e, blink, look):
    op = e.get('open', 1.0) * (1 - blink)
    low = EYE_LOW[name]
    allw = [r for shp in F['white'].values() for r in shp]
    if not allw:
        return
    P = np.concatenate(allw)
    gx, gy = EYE_GROW[name]
    cx0, cy0 = P[:, 0].mean(), low

    def grow(r):
        return np.c_[cx0 + (r[:, 0] - cx0) * gx, cy0 + (r[:, 1] - cy0) * gy]
    xs = grow(P)[:, 0]
    x0, x1 = xs.min(), xs.max()
    if e.get('closed') or op < 0.15:
        c = (x0 + x1) / 2
        mid = low - 14
        if e.get('closed') == 'happy':               # ^ ^
            pts = np.array([(x0 + 4, mid + 6), (c, mid - 10), (x1 - 4, mid + 6)])
        else:                                        # calm closed lids: a soft, almost flat arc
            pts = np.array([(x0 + 4, mid), (c, mid + 7), (x1 - 4, mid)])
        t = np.linspace(0, 1, 16)[:, None]
        q = (1 - t) ** 2 * pts[0] + 2 * (1 - t) * t * pts[1] + t ** 2 * pts[2]
        _stroke_var(ctx, skin('feat', q, None), np.full(len(q), 4.5), LASH)
        return
    k = min(1.15, op)
    lx, ly = look

    def ring_set(kind, shift=False):
        out = []
        for shp in F.get(kind, {}).values():
            for r in shp:
                rr = grow(r)
                rr[:, 1] = low + (rr[:, 1] - low) * k       # the lid squashes toward the lower lid
                if shift:
                    rr = rr + [lx * 5, ly * 3]
                out.append(skin('feat', rr, None))
        return out
    white = ring_set('white')
    ctx.save()
    _rings_path(ctx, white)
    ctx.set_source_rgb(0.98, 0.97, 0.96)
    ctx.fill_preserve()
    ctx.clip()
    _rings_path(ctx, ring_set('iris', True))
    ctx.set_source_rgb(*IRIS)
    ctx.fill()
    ctx.restore()
    _rings_path(ctx, ring_set('ink'))
    ctx.set_source_rgb(*LASH)
    ctx.fill()
    ctx.save()
    _rings_path(ctx, white)
    ctx.clip()
    _rings_path(ctx, ring_set('hi', True))
    ctx.set_source_rgb(1, 1, 1)
    ctx.fill()
    ctx.restore()


def _mouth(ctx, skin, F, e, talk):
    shape = e.get('mouth', 'smile')
    if talk > 0.05 and shape in ('smile', 'flat'):
        shape = 'talk'
    if shape == 'smile':
        _rings_path(ctx, [skin('feat', r, None) for shp in F['mouth']['ink'].values() for r in shp])
        ctx.set_source_rgb(*INK)
        ctx.fill()
        return
    cx, cy = 207.0, 203.0
    if shape in ('flat', 'frown'):
        d = 3 if shape == 'frown' else 0
        q = np.array([(cx - 9, cy + 2 + d), (cx, cy + 1 - d), (cx + 10, cy + d)])
        _stroke_var(ctx, skin('feat', q, None), np.full(3, 2.2))
        return
    k = {'talk': 0.45 + 0.55 * talk, 'o': 0.8, 'open': 0.9, 'shout': 1.25}[shape]
    w = {'talk': 10, 'o': 6, 'open': 12, 'shout': 14}[shape]
    hgt = 4 + 10 * k
    t = np.linspace(0, 2 * math.pi, 28)
    if shape == 'o':
        q = np.c_[cx + w * np.cos(t), cy + 5 + hgt * 0.55 * np.sin(t)]
    else:
        q = np.c_[cx + w * np.cos(t), cy + hgt * 0.15 + np.where(np.sin(t) > 0, hgt * 0.85, hgt * 0.2) * np.sin(t)]
    q = skin('feat', q, None)
    ctx.save()
    _rings_path(ctx, [q])
    ctx.set_source_rgb(*MOUTH_IN)
    ctx.fill_preserve()
    ctx.clip()
    _rings_path(ctx, [skin('feat', np.c_[cx + w * 0.7 * np.cos(t), cy + hgt + hgt * 0.35 * np.sin(t)], None)])
    ctx.set_source_rgb(*TONGUE)
    ctx.fill()
    if shape == 'shout':
        _rings_path(ctx, [skin('feat', np.array([(cx - w, cy - 4), (cx + w, cy - 4), (cx + w, cy + hgt * 0.25),
                                                 (cx - w, cy + hgt * 0.25)]), None)])
        ctx.set_source_rgb(*TEETH)
        ctx.fill()
    ctx.restore()
    _rings_path(ctx, [q])
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(1.8)
    ctx.stroke()


def _brows(ctx, skin, F, e):
    lift = e.get('brow', 0)
    rings = []
    for shp in F['brow_f']['ink'].values():
        for r in shp:
            r = r.copy()
            if lift < 0:
                r[:, 1] += np.clip((240 - r[:, 0]) / 25, 0, 1) * abs(lift) * 4
            else:
                r[:, 1] -= lift * 4
            rings.append(skin('feat', r, None))
    _rings_path(ctx, rings)
    ctx.set_source_rgb(0.40, 0.20, 0.16)
    ctx.fill()


# ------------------------------------------------------------------ the far foot

# the far foot is hidden behind the near one on the sheet: it is drawn as a copy of the near
# foot (sock + sneaker), set back and a little smaller, moving with the far leg's bones
FAR_FOOT_SHIFT = (46.0, -16.0)
FAR_FOOT_SCALE = 0.95
ANKLE_CUT = 1004.0


FAR_TURN = 5.0                 # the far leg's rest stance: the near leg turned this much


def _far_leg(ctx, M, pose):
    """The far leg is mostly hidden on the sheet, so it is drawn as the near leg's drawing
    moved to the far hip (turned FAR_TURN deg, its rest stance), driven by the far bones."""
    mirror = dict(pose)
    hx = BONES['thigh_f'][1][0] - BONES['thigh_n'][1][0]
    for a, b in (('thigh_n', 'thigh_f'), ('shin_n', 'shin_f'), ('foot_n', 'foot_f')):
        mirror[a] = dict(pose.get(b, {}))
    mirror['thigh_n']['rot'] = mirror['thigh_n'].get('rot', 0.0) + FAR_TURN
    mirror['thigh_n']['ox'] = hx
    skin = _Skin(mirror)
    part = M['parts']['leg_near']
    ctx.save()
    base = []
    for fi, f in enumerate(part['fills']):
        for si, rings in f['shapes'].items():
            rr = [skin('leg_near', r, (fi, si, j)) for j, r in enumerate(rings)]
            if f['tag'] == 'base':
                _rings_path(ctx, rr)
                ctx.set_source_rgb(*INK)                   # its own outline all round
                ctx.set_line_width(5.0)
                ctx.stroke_preserve()
                ctx.set_source_rgb(*f['col'])
                ctx.fill()
                base += rr
            elif f['tag'] == 'ink':
                _rings_path(ctx, rr)
                ctx.set_source_rgb(*INK)
                ctx.set_line_width(0.6)
                ctx.fill_preserve()
                ctx.stroke()
            else:
                ctx.save()
                _rings_path(ctx, base)
                ctx.clip()
                _rings_path(ctx, rr)
                ctx.set_source_rgb(*f['col'])
                ctx.fill()
                ctx.restore()
    # a far leg sits a touch deeper: tint it slightly
    _rings_path(ctx, base)
    ctx.set_source_rgba(0.55, 0.30, 0.25, 0.10)
    ctx.fill()
    ctx.restore()


def _far_foot(ctx, M, pose):
    mirror = dict(pose)
    for a, b in (('thigh_n', 'thigh_f'), ('shin_n', 'shin_f'), ('foot_n', 'foot_f')):
        mirror[a] = pose.get(b, {})
    skin = _Skin(mirror)
    dx, dy = FAR_FOOT_SHIFT
    k = FAR_FOOT_SCALE
    ax, ay = 124.0, ANKLE_CUT

    def place(r):
        q = r.copy()
        q[:, 0] = ax + (q[:, 0] - ax) * k + dx
        q[:, 1] = ay + (q[:, 1] - ay) * k + dy
        return q
    part = M['parts']['leg_near']
    ctx.save()
    # only below the ankle (in the near leg's own space), carried by its bones
    clip = np.array([(40.0, ANKLE_CUT), (300.0, ANKLE_CUT), (300.0, 1260.0), (40.0, 1260.0)])
    _rings_path(ctx, [place(skin('leg_near', clip, None))])
    ctx.clip()
    base = []
    for fi, f in enumerate(part['fills']):
        for si, rings in f['shapes'].items():
            rr = [place(skin('leg_near', r, (fi, si, j))) for j, r in enumerate(rings)]
            if f['tag'] == 'base':
                _rings_path(ctx, rr)
                ctx.set_source_rgb(*f['col'])
                ctx.fill()
                base += rr
            elif f['tag'] == 'ink':
                _rings_path(ctx, rr)
                ctx.set_source_rgb(*INK)
                ctx.set_line_width(0.6)
                ctx.fill_preserve()
                ctx.stroke()
            else:
                ctx.save()
                _rings_path(ctx, base)
                ctx.clip()
                _rings_path(ctx, rr)
                ctx.set_source_rgb(*f['col'])
                ctx.fill()
                ctx.restore()
    ctx.restore()


# ------------------------------------------------------------------ arms and hands

# The arms are Anka's parts sheet's upper arm and forearm + hand (traced to vectors by
# tools/trace_girl3_arms.py -> characters/girl/girl3_arms.npz). The tee's sleeves are cut out
# of the master figure's shirt and ride their upper arm, so a sleeve goes where the arm goes.
# Angles: degrees from straight down, + toward +x (the way she faces).
ARMS_NPZ = os.path.join(ROOT, 'characters', 'girl', 'girl3_arms.npz')
SHOULDER = {'n': (108.0, 335.0), 'f': (258.0, 335.0)}       # shoulder joints (src px)
REST_SH = {'n': -2.0, 'f': 0.0}                              # the sleeves' angle as drawn
ARM_SCALE = {'n': 1.08, 'f': 1.0}                            # the far arm is a touch smaller
SLEEVE_CUT = {'n': 74.0, 'f': 80.0}     # the sleeve hem's nearest point along the arm: above it the arm is IN the sleeve
ARM_W = {'n': 0.8, 'f': 0.68}            # upper arm width (fits inside its sleeve)
SHIRT = (187 / 255, 186 / 255, 137 / 255)
SKIN_ARM = (247 / 255, 206 / 255, 179 / 255)
HAIR_DK = (125 / 255, 5 / 255, 2 / 255)
# the torso's sides under the sleeves (shown when an arm lifts its sleeve away)
UNDER_N = [(126, 282), (104, 286), (90, 304), (92, 334), (112, 350), (124, 380), (128, 454), (150, 454), (150, 282)]
UNDER_F = [(232, 290), (248, 292), (250, 464), (234, 464)]
_arms = None


def arms_model():
    global _arms
    if _arms is not None:
        return _arms
    z = np.load(ARMS_NPZ)
    names = [str(n) for n in z['names']]
    P = {n: [] for n in names}
    idx = {}
    for (pi, fi), col, tag in zip(z['fill_meta'], z['fill_col'], z['fill_tag']):
        f = dict(tag=str(tag), col=tuple(float(c) for c in col), shapes={})
        P[names[int(pi)]].append(f)
        idx[(int(pi), int(fi))] = f
    i = 0
    for L, (pi, fi, si) in zip(z['ring_len'], z['ring_meta']):
        idx[(int(pi), int(fi))]['shapes'].setdefault(int(si), []).append(z['ring_pts'][i:i + L].astype(np.float64))
        i += L
    j = z['joints']
    _arms = dict(pieces=P, upper=((j[0][0], j[0][1]), (j[0][2], j[0][3])),
                 fore=((j[1][0], j[1][1]), (j[1][2], j[1][3])),
                 sleeve_n=z['sleeve_n'].astype(float), sleeve_f=z['sleeve_f'].astype(float))
    return _arms


def _len(j):
    return math.hypot(j[1][0] - j[0][0], j[1][1] - j[0][1])


def arm_lengths(side='n'):
    A = arms_model()
    k = ARM_SCALE[side]
    return _len(A['upper']) * k, _len(A['fore']) * k


def _dir(a):
    r = math.radians(a)
    return math.sin(r), math.cos(r)


def arm_joints(side, arm, shoulder):
    """(elbow, wrist, hand angle) for an arm dict(sh, el, wr) from `shoulder`."""
    sh, el, wr = arm.get('sh', 0.0), arm.get('el', 0.0), arm.get('wr', 0.0)
    L1, L2 = arm_lengths(side)
    dx, dy = _dir(sh)
    E = (shoulder[0] + dx * L1, shoulder[1] + dy * L1)
    dx2, dy2 = _dir(sh + el)
    Wr = (E[0] + dx2 * L2, E[1] + dy2 * L2)
    return E, Wr, sh + el + wr


def arm_ik(side, target, bend=1.0, shoulder=None):
    """sh / el that put the wrist on `target` (src px); bend -1 = the elbow bends back."""
    S = shoulder or SHOULDER[side]
    L1, L2 = arm_lengths(side)
    tx, ty = target[0] - S[0], target[1] - S[1]
    d = min(math.hypot(tx, ty), L1 + L2 - 1e-3)
    th = math.degrees(math.atan2(tx, ty))
    al = math.degrees(math.acos(max(-1.0, min(1.0, (L1 * L1 + d * d - L2 * L2) / (2 * L1 * d)))))
    sh = th - al * bend
    E = (S[0] + _dir(sh)[0] * L1, S[1] + _dir(sh)[1] * L1)
    fa = math.degrees(math.atan2(target[0] - E[0], target[1] - E[1]))
    return dict(sh=sh, el=fa - sh)


def _place(rings, j0, j1, at, ang, k, hand=None, wk=1.0):
    """Piece rings (piece px) -> src px: joint j0 onto `at`, axis j0->j1 pointing at `ang`."""
    a0 = math.degrees(math.atan2(j1[0] - j0[0], j1[1] - j0[1]))
    r = math.radians(-(ang - a0))
    c, s_ = math.cos(r), math.sin(r)
    out = []
    for ring in rings:
        q = ring - np.array(j0)
        if wk != 1.0:                                        # slimmer piece (across its axis)
            q = np.c_[q[:, 0] * wk, q[:, 1]]
        if hand is not None:
            # the hand (beyond the wrist): curl the fingers (grip) and bend it at the wrist
            wy, curl, wr = hand
            t = np.clip((q[:, 1] - wy) / 12.0, 0, 1)
            hk = 0.86 * (1 - 0.32 * curl)                      # the hand a touch smaller than the sheet's
            yy = np.where(q[:, 1] > wy, wy + (q[:, 1] - wy) * hk, q[:, 1])
            xx = np.where(q[:, 1] > wy, q[:, 0] * (0.6 + 0.4 * hk / 0.86) * 0.92 + q[:, 0] * 0.0, q[:, 0])
            q = np.c_[xx, yy]
            if wr:
                rr = np.radians(-wr) * t
                wx = 0.0
                dx, dy = q[:, 0] - wx, q[:, 1] - wy
                q = np.c_[wx + dx * np.cos(rr) - dy * np.sin(rr), wy + dx * np.sin(rr) + dy * np.cos(rr)]
        q = q * k
        out.append(np.c_[at[0] + q[:, 0] * c - q[:, 1] * s_, at[1] + q[:, 0] * s_ + q[:, 1] * c])
    return out


def _draw_fills(ctx, fills, xf):
    base = []
    for f in fills:
        for si, rings in f['shapes'].items():
            rr = xf(rings)
            if f['tag'] == 'base':
                _rings_path(ctx, rr)
                ctx.set_source_rgb(*f['col'])
                ctx.fill()
                base += rr
            elif f['tag'] == 'ink':
                _rings_path(ctx, rr)
                ctx.set_source_rgb(*INK)
                ctx.set_line_width(0.6)
                ctx.fill_preserve()
                ctx.stroke()
            else:
                ctx.save()
                _rings_path(ctx, base)
                ctx.clip()
                _rings_path(ctx, rr)
                ctx.set_source_rgb(*f['col'])
                ctx.fill()
                ctx.restore()


def draw_arm(ctx, side, arm, skin):
    """One arm (+ its sleeve) in src space; `skin` places the shoulder with the body."""
    A = arms_model()
    k = ARM_SCALE[side]
    S = tuple(skin('shirt', np.array([SHOULDER[side]]), None)[0])
    E, Wr, ha = arm_joints(side, arm, S)
    sh, el = arm.get('sh', 0.0), arm.get('el', 0.0)
    prop = arm.get('prop')
    if prop and arm.get('prop_behind'):
        prop(ctx, Wr, ha)
    ctx.save()
    ctx.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
    (u0, u1), (f0, f1) = A['upper'], A['fore']
    curl = 1.0 if arm.get('hand') == 'grip' else 0.0
    xf_f = lambda rr: _place(rr, f0, f1, E, sh + el, k, hand=(f1[1] - f0[1], curl, arm.get('wr', 0.0)))  # noqa
    xf_u = lambda rr: _place(rr, u0, u1, S, sh, k, wk=ARM_W[side])  # noqa: E731
    # the arm is inside its sleeve: nothing of it is drawn above the hem (in the arm's frame)
    dx_, dy_ = _dir(sh)
    nx_, ny_ = -dy_, dx_
    cut = SLEEVE_CUT[side]

    def at(a_, c_):
        return (S[0] + dx_ * a_ + nx_ * c_, S[1] + dy_ * a_ + ny_ * c_)
    tube = [at(-80, -70), at(cut, -70), at(cut, 70), at(-80, 70)]
    ctx.save()
    ctx.rectangle(-3000, -3000, 6000, 6000)
    ctx.move_to(*tube[0])
    for p_ in tube[1:]:
        ctx.line_to(*p_)
    ctx.close_path()
    ctx.clip()
    # ONE arm: the outline goes round both pieces together (strokes first, then the fills),
    # so there is no seam at the elbow; then shade and the lines inside the hand
    bases = []
    for piece, xf in (('fore', xf_f), ('upper', xf_u)):
        for f in A['pieces'][piece]:
            if f['tag'] == 'base':
                for rings in f['shapes'].values():
                    bases.append((xf(rings), f['col']))
    for rr, _ in bases:
        _rings_path(ctx, rr)
        ctx.set_source_rgb(*INK)
        ctx.set_line_width(5.0)
        ctx.stroke()
    for rr, col in bases:
        _rings_path(ctx, rr)
        ctx.set_source_rgb(*col)
        ctx.fill()
    ctx.save()
    ctx.set_fill_rule(cairo.FILL_RULE_WINDING)
    for rr, _ in bases:
        _rings_path(ctx, rr)
    ctx.clip()
    ctx.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
    for piece, xf in (('fore', xf_f), ('upper', xf_u)):
        for f in A['pieces'][piece]:
            if f['tag'] == 'base':
                continue
            for rings in f['shapes'].values():
                _rings_path(ctx, xf(rings))
                ctx.set_source_rgb(*(INK if f['tag'] == 'ink' else f['col']))
                ctx.fill()
    ctx.restore()
    ctx.restore()                                            # end of the in-the-sleeve clip
    # the sleeve: a short flared tube round the upper arm, in the arm's own frame, so it is
    # always ON the arm (the arm comes out of its hem) whatever the arm does
    _sleeve(ctx, side, S, sh)
    ctx.restore()
    if prop and not arm.get('prop_behind'):
        prop(ctx, Wr, ha)
    return Wr, ha


SLEEVE = {'n': dict(top=27.0, hem=37.0, length=80.0), 'f': dict(top=22.0, hem=28.0, length=86.0)}
SHIRT_SH = (160 / 255, 158 / 255, 116 / 255)
SHIRT_FOLD = (138 / 255, 136 / 255, 98 / 255)


def _sleeve(ctx, side, S, sh):
    g = SLEEVE[side]
    dx, dy = _dir(sh)
    nx, ny = -dy, dx

    def at(a, c):
        return (S[0] + dx * a + nx * c, S[1] + dy * a + ny * c)
    wt, wh, L = g['top'], g['hem'], g['length']
    # outline: one side down, the hem (a slight curve), the other side up, the round top
    side_a = [at(-8 + (L + 8) * u, -(wt + (wh - wt) * u ** 1.4)) for u in np.linspace(0, 1, 8)]
    hem = [at(L + 5 * math.sin(math.pi * u), -wh + 2 * wh * u) for u in np.linspace(0, 1, 9)]
    side_b = [at(-8 + (L + 8) * u, (wt + (wh - wt) * u ** 1.4)) for u in np.linspace(1, 0, 8)]
    top = [at(-8 - wt * math.sin(math.pi * u), wt * math.cos(math.pi * u)) for u in np.linspace(0, 1, 11)]
    outline = side_a + hem + side_b + top
    ctx.save()
    ctx.set_fill_rule(cairo.FILL_RULE_WINDING)
    ctx.move_to(*outline[0])
    for p_ in outline[1:]:
        ctx.line_to(*p_)
    ctx.close_path()
    ctx.set_source_rgb(*SHIRT)
    ctx.fill_preserve()
    ctx.clip()
    # shade along the back of the sleeve, a fold or two near the hem
    shade = [at(-8 + (L + 12) * u, (wt + (wh - wt) * u ** 1.4) * 0.62) for u in np.linspace(0, 1, 8)]
    shade += [at(-8 + (L + 12) * u, wh + 10) for u in np.linspace(1, 0, 8)]
    ctx.move_to(*shade[0])
    for p_ in shade[1:]:
        ctx.line_to(*p_)
    ctx.close_path()
    ctx.set_source_rgb(*SHIRT_SH)
    ctx.fill()
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_source_rgb(*SHIRT_FOLD)
    for c0, a0, a1 in ((0.2, 0.6, 0.9),):
        ctx.move_to(*at(L * a0, wh * c0))
        ctx.line_to(*at(L * a1, wh * c0 * 1.1))
        ctx.set_line_width(2.4)
        ctx.stroke()
    ctx.restore()
    # ink: the two sides and the hem (no line over the shoulder: it is the same cloth)
    ctx.save()
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.set_line_cap(cairo.LINE_CAP_ROUND)
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(2.8)
    seg = side_a[2:] + hem + side_b[:-2]
    ctx.move_to(*seg[0])
    for p_ in seg[1:]:
        ctx.line_to(*p_)
    ctx.stroke()
    ctx.restore()


def _under(ctx, skin, poly, edge, ink=1.0):
    """The torso's side under a sleeve: shirt colour, its outer edge inked (`ink` 0..1: the
    edge only shows once the sleeve has moved off it, so at rest there is no seam)."""
    q = skin('shirt', np.array(poly, float), None)
    _rings_path(ctx, [q])
    ctx.set_source_rgb(*SHIRT)
    ctx.fill()
    e = q[edge]
    ctx.move_to(*e[0])
    for p_ in e[1:]:
        ctx.line_to(*p_)
    ctx.set_source_rgba(*INK, ink)
    ctx.set_line_width(2.6)
    ctx.stroke()


def _sleeve_moved(side, arm):
    return min(1.0, abs(arm.get('sh', 0.0) - REST_SH[side]) / 25.0)


ARMS_DOWN = {'n': dict(sh=-2.0, el=5.0), 'f': dict(sh=1.0, el=4.0)}


# ------------------------------------------------------------------ the girl

def _draw_part(ctx, skin, name, part):
    base = []
    for fi, f in enumerate(part['fills']):
        for si, rings in f['shapes'].items():
            rr = [skin(name, r, (fi, si, j)) for j, r in enumerate(rings)]
            if f['tag'] == 'base':
                _rings_path(ctx, rr)
                if name == 'leg_far':               # its hidden edge shows when the legs part
                    ctx.set_source_rgb(*INK)
                    ctx.set_line_width(2.6)
                    ctx.stroke_preserve()
                ctx.set_source_rgb(*f['col'])
                ctx.fill()
                base += rr
            elif f['tag'] == 'ink':
                _rings_path(ctx, rr)
                ctx.set_source_rgb(*INK)
                ctx.set_line_width(0.6)
                ctx.fill_preserve()
                ctx.stroke()
            else:
                ctx.save()
                if base:
                    _rings_path(ctx, base)
                    ctx.clip()
                _rings_path(ctx, rr)
                ctx.set_source_rgb(*f['col'])
                ctx.fill()
                ctx.restore()
    for li, (pts, wid) in enumerate(part['lines']):
        col = (0.38, 0.03, 0.01) if name.startswith('hair') else INK
        _stroke_var(ctx, skin(name, pts, ('L', li)), wid * 0.9, col)


def draw_girl(ctx, x, y, scale, pose=None, expr='smile', blink=0.0, look=(0.0, 0.0), talk=0.0, flip=False,
              arms=None):
    """arms: {'n': arm, 'f': arm}, arm = dict(sh, el, wr, hand='relaxed'|'open'|'grip',
    prop=fn(ctx, wrist, hand angle), prop_behind=bool); a side not given hangs down."""
    pose = pose or {}
    M = model()
    A = arms_model()
    skin = _Skin(pose)
    e = EXPR.get(expr, EXPR['smile'])
    arms = dict(arms or {})
    for side in ('n', 'f'):
        if side not in arms:
            arms[side] = dict(ARMS_DOWN[side])
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(-scale if flip else scale, scale)
    ctx.translate(-FEET[0], -FEET[1])
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
    far_front = False
    for name in M['order']:
        if name == 'hair_back':
            for f in M['parts'][name]['fills']:
                if f['tag'] == 'base':
                    for si, rings in f['shapes'].items():
                        _rings_path(ctx, [skin('hair_under', r, ('U', si, j)) for j, r in enumerate(rings)])
                        ctx.set_source_rgb(*HAIR_DK)
                        ctx.fill()
        if name == 'leg_far':
            _far_leg(ctx, M, pose)
            continue
        part = M['parts'][name]
        if name == 'arms':
            # the sheet's arms (hands behind her back) are not drawn; the hair they covered is
            ctx.save()
            ctx.rectangle(-500, -500, 1500, 500 + 522)
            ctx.clip()
            for f in part['fills']:
                if f['tag'] == 'base':
                    for si, rings in f['shapes'].items():
                        _rings_path(ctx, [skin('arms', r, (0, si, j)) for j, r in enumerate(rings)])
                        ctx.set_source_rgb(*HAIR_DK)
                        ctx.fill()
            ctx.restore()
            # behind the sleeves is her long hair: shows when a sleeve swings away
            _rings_path(ctx, [skin('shirt', A['sleeve_n'], None), skin('shirt', A['sleeve_f'], None)])
            ctx.set_source_rgb(*HAIR_DK)
            ctx.fill()
            far_front = arms['f'].get('sh', 0.0) > REST_SH['f'] + 12   # reaching forward: in front
            if not far_front:
                draw_arm(ctx, 'f', arms['f'], skin)         # the far arm: behind her body
            continue
        if name == 'shirt':
            _under(ctx, skin, UNDER_N, slice(0, 7), _sleeve_moved('n', arms['n']))
            _under(ctx, skin, UNDER_F, slice(1, 3), _sleeve_moved('f', arms['f']))
            ctx.save()                                       # the tee without its sleeves
            ctx.rectangle(-2000, -2000, 5000, 5000)
            _rings_path(ctx, [skin('shirt', A['sleeve_n'], None), skin('shirt', A['sleeve_f'], None)])
            ctx.clip()
            _draw_part(ctx, skin, name, part)
            ctx.restore()
            if far_front:
                draw_arm(ctx, 'f', arms['f'], skin)
            draw_arm(ctx, 'n', arms['n'], skin)             # the near arm: in front
            continue
        _draw_part(ctx, skin, name, part)
        if name == 'face':
            F = M['feats']
            _brows(ctx, skin, F, e)
            _eye(ctx, skin, 'eye_n', F['eye_n'], e, blink, look)
            _eye(ctx, skin, 'eye_f', F['eye_f'], e, blink, look)
            _rings_path(ctx, [skin('feat', r, None) for shp in F['nose']['ink'].values() for r in shp])
            ctx.set_source_rgb(*INK)
            ctx.fill()
            _mouth(ctx, skin, F, e, talk)
    ctx.restore()


# ------------------------------------------------------------------ walking

LEG_N = ((120.0, 660.0), (124.0, 840.0), (128.0, 1040.0))     # hip, knee, ankle (rest, src px)
LEG_F = ((205.0, 660.0), (193.3, 839.7), (179.8, 1039.2))   # = the near leg, shifted + turned 5 deg
STANCE = 0.6                                                    # share of a cycle a foot is planted


def _ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def walk_pose(phase, stride, lift=34.0):
    """Leg pose for a walk cycle (she walks toward +x, the way she faces).

    phase = cycles walked so far; stride = how far a foot travels relative to the body per
    step (src px; 0 = standing). A planted foot moves back at exactly the body's speed, so it
    stays put on the floor when the body moves at speed(stride, period) = stride / (STANCE *
    period). Returns pose entries for the legs + the root's dip (straight leg = lowest hip)."""
    targets = {}
    for leg, (H, K, A), off in (('n', LEG_N, 0.0), ('f', LEG_F, 0.5)):
        u = (phase + off) % 1.0
        if u < STANCE:
            s = u / STANCE
            fx, fy = stride / 2 - s * stride, 0.0
            pitch = -10 * max(0.0, (s - 0.75) / 0.25) * min(1.0, stride / 60)     # heel lifts at push-off
        else:
            s = (u - STANCE) / (1 - STANCE)
            fx = -stride / 2 + _ease(s) * stride
            fy = -lift * math.sin(math.pi * s) * min(1.0, stride / 60)
            pitch = 6 * math.sin(math.pi * s) * min(1.0, stride / 60)
        targets[leg] = (H, K, A, fx, fy, pitch)
    return legs_pose(targets)


def legs_pose(targets, hip=None):
    """targets: leg ('n' | 'f') -> (H, K, A, fx, fy, pitch): the ankle's offset from rest.
    Two-bone IK per leg. hip=None: the hip dips just enough for the straighter leg to reach
    (walking); hip=(dx, dy): the hips are put there (sitting, crouching) and the legs fold."""
    if hip is not None:
        return _legs_at(targets, hip[0], hip[1])
    drop = 0.0
    for H, K, A, fx, fy, _ in targets.values():
        l1 = math.hypot(K[0] - H[0], K[1] - H[1])
        l2 = math.hypot(A[0] - K[0], A[1] - K[1])
        vx, vy = A[0] + fx - H[0], A[1] + fy - H[1]
        L = (l1 + l2) * 0.997
        if abs(vx) < L:
            drop = max(drop, vy - math.sqrt(L * L - vx * vx))
    return _legs_at(targets, 0.0, drop)


def _legs_at(targets, hdx, drop):
    pose = {'root': dict(dx=hdx, dy=drop)}
    for leg, (H, K, A, fx, fy, pitch) in targets.items():
        l1 = math.hypot(K[0] - H[0], K[1] - H[1])
        l2 = math.hypot(A[0] - K[0], A[1] - K[1])
        hx, hy = H[0] + hdx, H[1] + drop
        tx, ty = A[0] + fx, A[1] + fy
        d = min(math.hypot(tx - hx, ty - hy), l1 + l2 - 1e-3)
        th = math.atan2(tx - hx, ty - hy)                     # from straight down, toward +x
        al = math.acos(max(-1.0, min(1.0, (l1 * l1 + d * d - l2 * l2) / (2 * l1 * d))))
        ph_t = th + al                                        # the knee bends forward (+x)
        kx, ky = hx + l1 * math.sin(ph_t), hy + l1 * math.cos(ph_t)
        ph_s = math.atan2(tx - kx, ty - ky)
        rest_t = math.atan2(K[0] - H[0], K[1] - H[1])
        rest_s = math.atan2(A[0] - K[0], A[1] - K[1])
        rt = -math.degrees(ph_t - rest_t)
        rs = -math.degrees(ph_s - rest_s) - rt
        pose['thigh_' + leg] = dict(rot=rt)
        pose['shin_' + leg] = dict(rot=rs)
        pose['foot_' + leg] = dict(rot=-rt - rs + pitch)
    return pose


def foot_pose(near=(0.0, 0.0, 0.0), far=(0.0, 0.0, 0.0)):
    """Place the feet directly: (fx, fy, pitch) offsets of each ankle (taps, kicks, shifts)."""
    return legs_pose({'n': LEG_N + tuple(near), 'f': LEG_F + tuple(far)})


class Walker:
    """Integrates a walk: x(t) and the leg pose. `plan` = [(t, target_x)] stops; she walks
    toward each target at `speed` (src px/s) with steps of `stride`, easing in and out."""

    def __init__(self, x0, plan, speed=260.0, stride=150.0, fps=120):
        self.fps = fps
        n = int((plan[-1][0] + 10) * fps)
        xs, ph, st = np.zeros(n), np.zeros(n), np.zeros(n)
        x, phase, cur = x0, 0.0, 0.0
        legs = sorted(plan)
        for i in range(n):
            t = i / fps
            target = x0
            for (ts, tx) in legs:
                if t >= ts:
                    target = tx
            dist = target - x
            want = 1.0 if abs(dist) > 2 else 0.0
            # ramp the stride: start / stop within ~0.35 s, and slow down close to the target
            want = min(want, abs(dist) / (stride * 0.9)) if want else 0.0
            cur += (want - cur) * min(1.0, 7.0 / fps)
            s = stride * cur
            v = speed * cur * (1 if dist >= 0 else -1)
            period = s / (STANCE * abs(speed)) if cur > 1e-3 else 1.0
            if cur > 1e-3:
                phase += (1.0 / fps) / max(0.25, stride / (STANCE * speed))
            else:
                # settle the feet together: finish at a phase where both are near the body
                phase += 0.0
            x += v / fps
            xs[i], ph[i], st[i] = x, phase, s
        self.xs, self.ph, self.st = xs, ph, st

    def _i(self, t):
        return min(len(self.xs) - 1, max(0, int(round(t * self.fps))))

    def x(self, t):
        return float(self.xs[self._i(t)])

    def pose(self, t):
        i = self._i(t)
        return walk_pose(float(self.ph[i]), float(self.st[i]))

    def moving(self, t):
        return float(self.st[self._i(t)]) / 150.0

    def facing(self, t):
        i = self._i(t)
        j = max(0, i - 6)
        return 1 if self.xs[i] >= self.xs[j] - 1e-6 else -1


# ------------------------------------------------------------------ whole-body poses

# A body state is plain numbers, so any two states blend smoothly (feet stay put because the
# blend runs on the IK inputs, not on joint angles):
#   hip: (dx, dy) of the hips from standing (src px; None = let the legs decide, as walking)
#   n, f: (fx, fy, pitch) ankle offsets from standing; lean: chest tilt (+ = forward, toward +x)
#   hips: hips tilt; root: whole-body tilt about the feet; head, nod, turn: the head
#   arm_n, arm_f: None (behind her back, as on the sheet) or dict(sh, el, wr, hand)
STATES = {
    'stand':      dict(),
    'crouch':     dict(hip=(-30, 210), n=(40, 0, 0), f=(40, 0, 0), lean=20, head=-10, nod=0.5),
    'squat_pet':  dict(hip=(-30, 230), n=(45, 0, 0), f=(45, 0, 0), lean=26, head=-6, nod=0.8,
                       arm_n=dict(sh=60, el=25, hand='open'), arm_f=dict(sh=20, el=30)),
    'sit_chair':  dict(hip=(0, 185), n=(190, 0, 0), f=(190, 0, 0), lean=6,
                       arm_n=dict(sh=18, el=42), arm_f=dict(sh=8, el=34)),
    'sit_floor':  dict(hip=(0, 375), n=(330, 172, 0), f=(330, 172, 0), lean=-6,
                       arm_n=dict(sh=-12, el=10, hand='open'), arm_f=dict(sh=-22, el=0, hand='open')),
    'lie_back':   dict(hip=(0, 455), n=(330, 150, 0), f=(330, 150, 0), hips=-84, head=-4, gravity=0.0,
                       arm_n=dict(sh=96, el=0, hand='relaxed'), arm_f=dict(sh=92, el=0)),
    'bend':       dict(hip=(-40, 25), lean=55, head=-15, nod=0.4,
                       arm_n=dict(sh=68, el=0, hand='open'), arm_f=dict(sh=58, el=10, hand='open')),
    'wave':       dict(arm_f=dict(sh=150, el=30, hand='open')),
    'arms_down':  dict(),
    'hands_hips': dict(arm_n=dict(sh=-35, el=80, wr=40), arm_f=dict(sh=30, el=-80, wr=-40)),
    'shrug':      dict(arm_n=dict(sh=-20, el=95, hand='open'), arm_f=dict(sh=25, el=-95, hand='open'),
                       head=4),
    'stretch':    dict(arm_n=dict(sh=172, el=-8, hand='open'), arm_f=dict(sh=-172, el=8, hand='open'),
                       lean=-4, head=-4, nod=-0.6),
    'point':      dict(arm_f=dict(sh=95, el=-5)),
}
STATES['hands_hips'] = dict(arm_n=dict(arm_ik('n', (110, 585), bend=1), hand='grip', wr=-60),
                           arm_f=dict(arm_ik('f', (252, 585), bend=-1), hand='grip', wr=60))
STATES['shrug'] = dict(arm_n=dict(sh=-25, el=70, hand='open', wr=-30), arm_f=dict(sh=20, el=-70, hand='open', wr=30),
                       head=4)
REST_ARM = ARMS_DOWN                                  # arms hanging at her sides


def _arm_of(state, side):
    a = state.get('arm_' + side)
    return a


def blend(a, b, k):
    """Blend two body states (k 0..1). Arms behind the back blend from REST_ARM."""
    k = max(0.0, min(1.0, k))
    out = {}
    for key in ('lean', 'hips', 'root', 'head', 'nod', 'turn'):
        out[key] = a.get(key, 0.0) + (b.get(key, 0.0) - a.get(key, 0.0)) * k
    out['gravity'] = a.get('gravity', 1.0) + (b.get('gravity', 1.0) - a.get('gravity', 1.0)) * k
    ha, hb = a.get('hip'), b.get('hip')
    if ha is not None or hb is not None:
        ha, hb = ha or (0.0, 0.0), hb or (0.0, 0.0)
        out['hip'] = (ha[0] + (hb[0] - ha[0]) * k, ha[1] + (hb[1] - ha[1]) * k)
    for leg in ('n', 'f'):
        fa, fb = a.get(leg, (0, 0, 0)), b.get(leg, (0, 0, 0))
        out[leg] = tuple(fa[i] + (fb[i] - fa[i]) * k for i in range(3))
    for side in ('n', 'f'):
        xa, xb = _arm_of(a, side), _arm_of(b, side)
        if xa is None and xb is None:
            continue
        xa = xa or REST_ARM[side]
        xb = xb or REST_ARM[side]
        arm = {}
        for q in ('sh', 'el', 'wr'):
            arm[q] = xa.get(q, 0.0) + (xb.get(q, 0.0) - xa.get(q, 0.0)) * k
        arm['hand'] = xb.get('hand', 'relaxed') if k > 0.5 else xa.get('hand', 'relaxed')
        out['arm_' + side] = arm
    return out


def body(state, walk=None):
    """Body state -> (pose, arms) for draw_girl. walk=(phase, stride) overrides the legs."""
    st = state
    if walk is not None:
        pose = walk_pose(*walk)
    else:
        hd = st.get('hip', (0.0, 0.0))
        th = math.radians(st.get('hips', 0.0))
        tg = {}
        for leg, L in (('n', LEG_N), ('f', LEG_F)):
            fx, fy, pitch = st.get(leg, (0, 0, 0))
            # the ankle target in the tilted hips' frame (legs keep their place on the floor)
            rx, ry = L[2][0] + fx - hd[0] - 165.0, L[2][1] + fy - hd[1] - 640.0
            c, s_ = math.cos(-th), math.sin(-th)
            lx, ly = 165.0 + rx * c - ry * s_, 640.0 + rx * s_ + ry * c
            tg[leg] = L + (lx - L[2][0] + hd[0], ly - L[2][1] + hd[1], pitch - st.get('hips', 0.0))
        pose = legs_pose(tg, hd)
    pose = dict(pose)
    if st.get('root'):
        r = dict(pose.get('root', {}))
        r['rot'] = st['root']
        pose['root'] = r
    if st.get('hips'):
        pose['hips'] = dict(rot=st['hips'])
    pose['chest'] = dict(rot=st.get('lean', 0.0))
    pose['head'] = dict(rot=st.get('head', 0.0))
    pose['nod'] = st.get('nod', 0.0)
    pose['turn'] = st.get('turn', 0.0)
    pose['gravity'] = st.get('gravity', 1.0)
    arms = {}
    for side in ('n', 'f'):
        a = st.get('arm_' + side)
        if a is not None:
            arms[side] = dict(a)
    return pose, (arms or None)
