"""The girl standing, alive: the master sheet's big standing drawing (characters/rig/
girl_src.png, cut by tools/cut_rig_source.py from girl_master_red.png) on a mesh rig.

She breathes, shifts her weight, leans, tilts / nods / turns her head, blinks (the lids are
painted in her own skin and lash colours), talks (an open mouth replaces the smile) and her
long hair swings with lag on three locks driven by spring physics.

    g = GirlStand(x=300, y=1800, height=1300)
    g.tilt.key(1.0, 6); g.talk.append((2.0, 3.2)); g.draw(frame, t)
Moving her (x track) makes the hair trail. flip=True mirrors her (she faces left).
"""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rig import Rig, Track, Steps, Pendulum  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'characters', 'rig', 'girl_src.png')
FEET = (165.0, 1180.0)
SRC_H = 1180.0

SKIN = (248, 208, 182, 255)
LASH = (52, 30, 28, 255)
EYE_L = [(121, 178), (130, 170), (150, 160), (170, 156), (185, 157), (188, 170), (183, 185), (170, 192),
         (150, 193), (137, 189)]
EYE_R = [(213, 156), (225, 142), (245, 132), (261, 130), (266, 145), (263, 160), (253, 171), (235, 172),
         (221, 167)]
MOUTH = (208, 202)

BONES = {
    'root': (None, FEET),
    'hips': ('root', (165.0, 640.0)),
    'thighL': ('root', (120.0, 660.0)),
    'shinL': ('thighL', (122.0, 830.0)),
    'thighR': ('root', (205.0, 660.0)),
    'shinR': ('thighR', (182.0, 830.0)),
    'spine': ('hips', (168.0, 560.0)),
    'chest': ('spine', (180.0, 420.0)),
    'neck': ('chest', (195.0, 275.0)),
    'head': ('neck', (196.0, 250.0)),
    'hairL1': ('head', (78.0, 200.0)),
    'hairL2': ('hairL1', (55.0, 345.0)),
    'hairR1': ('head', (268.0, 200.0)),
    'hairR2': ('hairR1', (278.0, 335.0)),
    'hairF1': ('head', (150.0, 245.0)),
    'hairF2': ('hairF1', (157.0, 345.0)),
}
_rig = None


def _hair_mask(a):
    r, g, b = (a[..., i].astype(int) for i in range(3))
    hair = (r > g * 1.6) & (r > b * 1.6) & (r > 70) & (a[..., 3] > 40)
    lab, n = ndimage.label(hair)
    sizes = ndimage.sum(hair, lab, range(1, n + 1))
    hair = np.isin(lab, [i + 1 for i, s in enumerate(sizes) if s > 300])
    dark = (a[..., :3].max(-1) < 90) & (a[..., 3] > 40)
    hair |= dark & ndimage.binary_dilation(hair, iterations=3)
    return ndimage.binary_closing(hair, iterations=2)


def _face_textures(a):
    """blink (closed), half (lids half down), talk (open mouth)."""
    out = {}

    def lid_line(d, pts, w=4):
        d.line(pts, fill=LASH, width=w, joint='curve')

    for name, cut in (('half', 0.5), ('blink', 1.0)):
        im = Image.fromarray(a.copy(), 'RGBA')
        m = Image.new('L', im.size, 0)
        dm = ImageDraw.Draw(m)
        for poly in (EYE_L, EYE_R):
            ys = [p[1] for p in poly]
            y_cut = min(ys) + (max(ys) - min(ys)) * cut
            dm.polygon(poly, fill=255)
            if cut < 1:
                dm.rectangle((0, y_cut, im.width, im.height), fill=0)
                dm.polygon(poly, fill=0) if False else None
        mm = np.asarray(m) > 0
        if cut < 1:                                    # keep the lower half of each eye
            mm2 = np.zeros_like(mm)
            for poly in (EYE_L, EYE_R):
                pm = Image.new('L', im.size, 0)
                ImageDraw.Draw(pm).polygon(poly, fill=255)
                pm = np.asarray(pm) > 0
                ys = np.where(pm.any(1))[0]
                yc = int(ys.min() + (ys.max() - ys.min()) * cut)
                pm[yc:] = False
                mm2 |= pm
            mm = mm2
        arr = np.asarray(im).copy()
        arr[ndimage.binary_dilation(mm, iterations=1)] = SKIN
        im = Image.fromarray(arr, 'RGBA')
        d = ImageDraw.Draw(im)
        if cut >= 1:                                   # closed: a lash curve along the lower lid
            lid_line(d, [(121, 179), (134, 186), (152, 190), (170, 188), (186, 180)], 5)
            lid_line(d, [(121, 179), (113, 174)], 3)
            lid_line(d, [(214, 160), (226, 166), (242, 166), (256, 158), (264, 150)], 4)
            lid_line(d, [(264, 150), (270, 144)], 3)
        else:                                          # the upper lash line at the lid
            lid_line(d, [(122, 179), (140, 175), (160, 174), (178, 175), (188, 177)], 5)
            lid_line(d, [(214, 157), (232, 153), (250, 150), (265, 149)], 4)
        out[name] = np.asarray(im).copy()
    im = Image.fromarray(a.copy(), 'RGBA')
    d = ImageDraw.Draw(im)
    mx, my = MOUTH
    d.ellipse((mx - 16, my - 9, mx + 16, my + 7), fill=SKIN)         # smile out
    d.chord((mx - 10, my - 7, mx + 9, my + 9), 0, 180, fill=(140, 52, 56, 255), outline=(80, 34, 34, 255), width=2)
    d.line([(mx - 10, my + 1), (mx + 9, my + 1)], fill=(80, 34, 34, 255), width=2)
    d.ellipse((mx - 5, my + 4, mx + 5, my + 8), fill=(226, 120, 120, 255))
    out['talk'] = np.asarray(im).copy()
    return out


def rig():
    global _rig
    if _rig is not None:
        return _rig
    a = np.asarray(Image.open(SRC).convert('RGBA'))
    h, w = a.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    hair = _hair_mask(a).astype(np.float32)
    body = 1 - hair
    sm = lambda v0, v1, v: np.clip((v - v0) / max(1e-6, v1 - v0), 0, 1)  # noqa: E731
    # hair: scalp + fringe ride the head; lower locks hang on spring chains
    low = sm(195, 240, yy)
    left = (xx < 118).astype(np.float32)
    right = (xx > 248).astype(np.float32)
    front = ((xx >= 118) & (xx <= 182) & (yy > 236)).astype(np.float32)
    mid = np.clip(1 - left - right - front, 0, 1)
    seg2L, seg2R, seg2F = sm(310, 370, yy), sm(305, 360, yy), sm(320, 370, yy)
    maps = {
        'hairL1': hair * low * left * (1 - seg2L), 'hairL2': hair * low * left * seg2L,
        'hairR1': hair * low * right * (1 - seg2R), 'hairR2': hair * low * right * seg2R,
        'hairF1': hair * low * front * (1 - seg2F), 'hairF2': hair * low * front * seg2F,
    }
    # the middle hair behind the neck / shoulders follows the chest below the head
    maps['head'] = hair * (1 - low) + hair * low * mid * (1 - sm(250, 300, yy)) + body * (1 - sm(238, 262, yy))
    maps['neck'] = body * sm(238, 262, yy) * (1 - sm(278, 300, yy))
    maps['chest'] = body * sm(278, 300, yy) * (1 - sm(450, 500, yy)) + hair * low * mid * sm(250, 300, yy)
    maps['spine'] = body * sm(450, 500, yy) * (1 - sm(560, 600, yy))
    leg = sm(640, 680, yy)
    split = 168 + (yy - 660) * 0.02
    isL = (xx < split).astype(np.float32)
    knee = sm(800, 860, yy)
    maps['hips'] = body * sm(560, 600, yy) * (1 - leg)
    maps['thighL'] = body * leg * isL * (1 - knee)
    maps['shinL'] = body * leg * isL * knee
    maps['thighR'] = body * leg * (1 - isL) * (1 - knee)
    maps['shinR'] = body * leg * (1 - isL) * knee
    maps['root'] = np.zeros((h, w), np.float32)
    # z-order: the hair locks hang over her shirt and arms; give them their own layer
    hair_lock = ((hair > 0.5) & (low > 0.5) & (mid < 0.5)).astype(np.float32)
    hair_lock = ndimage.gaussian_filter(hair_lock, 0.7) * (hair > 0.5)
    # legs below the shorts get their own layers (far leg, near leg) behind the body, so a
    # stepping leg slides under the shorts' cuff instead of tearing the drawing
    r_, g_, b_ = (a[..., i].astype(int) for i in range(3))
    shorts = (r_ > 150) & (g_ < 165) & (np.abs(g_ - b_) < 16) & (r_ - g_ > 40)
    shorts = ndimage.binary_closing(shorts, iterations=3) & (yy > 520) & (yy < 720)
    shorts = ndimage.binary_dilation(shorts, iterations=3)
    legzone = ((yy > 630) & ~shorts & (a[..., 3] > 0)).astype(np.float32)
    up = ndimage.binary_dilation(legzone > 0, iterations=18) & (yy > 600) & (a[..., 3] > 0)
    leg_any = np.maximum(legzone, up.astype(np.float32))
    farleg, nearleg = leg_any * (1 - isL), leg_any * isL
    upper = [b for b in BONES if not b.startswith(('thigh', 'shin'))]
    hipband = 1 - sm(610, 650, yy)

    def leg_w(th, sh):
        return {'hips': hipband, th: (1 - hipband) * (1 - knee), sh: (1 - hipband) * knee}
    layers = [('far', farleg, leg_w('thighR', 'shinR')),
              ('near', nearleg, leg_w('thighL', 'shinL')),
              ('body', 1 - legzone, upper), ('hair', hair_lock, upper)]
    r = Rig(a, BONES, maps, step=7, blur=3.0, layers=layers)
    # the body layer must not show a hole where a lock swings away: under the locks it
    # continues what is around them (shirt, arm), and is empty outside her silhouette
    holes = ndimage.binary_erosion(hair_lock > 0.5, iterations=2)   # its rim stays drawn underneath
    inside = ndimage.binary_fill_holes(ndimage.binary_closing((body * (a[..., 3] > 128)) > 0, iterations=12))
    idx = ndimage.distance_transform_edt(holes | ~((body > 0) & (a[..., 3] > 128)), return_distances=False,
                                         return_indices=True)

    def under(arr):
        out = arr.copy()
        fill = holes & inside
        out[fill] = arr[idx[0][fill], idx[1][fill]]
        out[holes & ~inside, 3] = 0
        return out
    r.add_texture('base@body', under(a))
    for k, v in _face_textures(a).items():
        r.add_texture(k, v)
        r.add_texture(k + '@body', under(v))
    _rig = r
    return r


class GirlStand:
    """Tracks: x, y (feet, screen), height, lean (deg, whole body), tilt / nod (head, deg),
    turn (-1..1 head parallax), weight (-1..1 shift onto a leg), talk [(t0, t1)], face
    (Steps: 'base' | 'half' for sleepy), blinks auto. flip mirrors her."""

    def __init__(self, x=540, y=1800, height=1300, seed=0, flip=False):
        self.x, self.y, self.height = Track(x), Track(y), Track(height)
        self.lean, self.tilt, self.nod, self.turn, self.weight = Track(), Track(), Track(), Track(), Track()
        self.face = Steps('base')
        self.flip = flip
        self.talk = []
        self.walk = Track(0.0)          # 0 = standing, 1 = walking (blend)
        self.cadence = 1.2              # walk cycles per second
        rnd = np.random.default_rng(seed)
        self.blinks = list(0.8 + np.cumsum(rnd.uniform(2.0, 4.0, 60)))
        self.phase = float(rnd.uniform(0, 6.28))
        self._baked = None

    def _bake(self, fps=60, dur=60.0):
        """Hair physics, stepped once in time order (deterministic, so every render worker
        gets the same hair)."""
        locks = {k: Pendulum(140 if k[-1] == '1' else 110, stiffness=38, damping=5.5, gain=0.7)
                 for k in ('hairL1', 'hairL2', 'hairR1', 'hairR2', 'hairF1', 'hairF2')}
        n = int(dur * fps)
        out = np.zeros((n, 6), np.float32)
        prev_x, prev_v, prev_h = self.x(0), 0.0, 0.0
        s = self.height(0) / SRC_H
        for i in range(n):
            t = i / fps
            x = self.x(t) / max(1e-6, s)
            v = (x - prev_x) * fps if i else 0.0
            acc = (v - prev_v) * fps if i else 0.0
            hr = self.tilt(t) + self.lean(t)
            hv = (hr - prev_h) * fps if i else 0.0
            prev_x, prev_v, prev_h = x, v, hr
            ax = acc * (-1 if self.flip else 1)
            for j, (k, p) in enumerate(locks.items()):
                # gravity keeps a lock hanging: counter the head's roll, lag behind motion
                tgt = -hr * (0.55 if k[-1] == '1' else 0.35)
                ang = p.step(1 / fps, tgt - 0.02 * hv, ax * (1.0 if k[-1] == '1' else 1.4))
                out[i, j] = ang
        self._baked = (fps, out)

    def hair(self, t):
        if self._baked is None:
            self._bake()
        fps, arr = self._baked
        i = min(len(arr) - 1, max(0, int(round(t * fps))))
        return arr[i]

    def state(self, t):
        b = math.sin(t * 2 * math.pi / 3.2 + self.phase)
        tex = self.face(t)
        for a0, a1 in self.talk:
            if a0 <= t < a1 and math.sin((t - a0) * math.pi * 4.4) > -0.2:
                tex = 'talk'
        for bt in self.blinks:
            if 0 <= t - bt < 0.14:
                tex = 'blink' if 0.03 <= t - bt < 0.10 else 'half'
        wgt = self.weight(t) + 0.15 * math.sin(t * 0.7 + self.phase)
        hl = self.hair(t)
        wk = self.walk(t)
        ph = 2 * math.pi * self.walk_phase(t)
        swing = 15.0 * wk
        lift_l = max(0.0, math.cos(ph)) * wk          # a leg bends its knee while it swings
        lift_r = max(0.0, -math.cos(ph)) * wk
        bob = abs(math.sin(ph)) * wk
        pose = {
            'root': dict(rot=self.lean(t) + 2.0 * wk, dy=-14 * bob + 6 * wk),
            'hips': dict(rot=1.2 * wgt, dx=3 * wgt),
            'thighL': dict(rot=-0.8 * wgt - swing * math.sin(ph)),
            'shinL': dict(rot=26 * lift_l),
            'thighR': dict(rot=-0.8 * wgt + swing * math.sin(ph)),
            'shinR': dict(rot=26 * lift_r),
            'spine': dict(rot=-1.0 * wgt + 1.5 * wk * math.sin(ph)),
            'chest': dict(sy=1 + 0.008 * b, sx=1 + 0.004 * b),
            'neck': dict(dy=-1.0 * b),
            'head': dict(rot=self.tilt(t) + 0.6 * math.sin(t * 0.83 + self.phase), dy=self.nod(t) * 0.0),
            'hairL1': dict(rot=float(hl[0])), 'hairL2': dict(rot=float(hl[1])),
            'hairR1': dict(rot=float(hl[2])), 'hairR2': dict(rot=float(hl[3])),
            'hairF1': dict(rot=float(hl[4])), 'hairF2': dict(rot=float(hl[5])),
        }
        return pose, tex

    def walk_phase(self, t):
        """Cycles walked so far (integrated, so changing the blend never jumps the legs)."""
        if getattr(self, '_wp', None) is None:
            fps, n = 120, 120 * 60
            acc, out = 0.0, np.zeros(n, np.float64)
            for i in range(n):
                out[i] = acc
                acc += self.cadence * min(1.0, self.walk(i / fps) * 1.0) / fps
            self._wp = (fps, out)
        fps, arr = self._wp
        return float(arr[min(len(arr) - 1, max(0, int(t * fps)))])

    def _warps(self, t):
        turn, nod = self.turn(t), self.nod(t)
        if not turn and not nod:
            return ()
        cx, cy = 200.0, 170.0

        def fn(V):
            dx, dy = V[:, 0] - cx, V[:, 1] - cy
            g = np.clip(1 - np.sqrt((dx / 95) ** 2 + (dy / 95) ** 2), 0, 1) ** 1.4
            g *= (V[:, 1] < 240)
            o = np.zeros_like(V, dtype=np.float64)
            o[:, 0] = turn * 12 * g
            o[:, 1] = nod * 9 * g
            return o
        return (fn,)

    def render(self, t):
        pose, tex = self.state(t)
        return rig().render(pose, self.height(t) / SRC_H, (self.x(t), self.y(t)), FEET, tex,
                            warps=self._warps(t), flip=self.flip)

    def draw(self, frame, t):
        img, (x0, y0) = self.render(t)
        cx0, cy0 = max(0, -x0), max(0, -y0)
        if cx0 < img.width and cy0 < img.height:
            frame.alpha_composite(img.crop((cx0, cy0, img.width, img.height)), (x0 + cx0, y0 + cy0))
