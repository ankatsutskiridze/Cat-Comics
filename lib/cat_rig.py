"""The cat, alive: the Gemini sheet's main sitting drawing on a mesh rig (lib/rig.py).

Texture = the sheet's sitting body with one of the sheet's expression heads on it
(puppet.cat_frame), so every mood is the artist's own face; the mesh then makes it breathe,
lean, crouch, tilt / nod / turn its head, flick its ears and squash into a meow.

    cat = CatSit(seed=1)
    cat.x.key(0, 300); cat.mood.set(2.0, 'surprised'); cat.meow(3.0)
    cat.draw(frame, t)            # frame: PIL RGBA, feet at (x, y), `height` px tall

Rig space = puppet.cat_frame canvas (489 x 809): feet at y 800, chin y 425, ear tips y 165.
"""
import math
import os
import random
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import puppet  # noqa: E402
from rig import Rig, Track, Steps, ease, ease_out  # noqa: E402

MOODS = ['deadpan', 'meow', 'surprised', 'sleepy', 'smug', 'angry', 'silly', 'confused']
FEET = (245.0, 800.0)
HEAD_C = (242.0, 335.0)
SRC_H = 640.0                 # ear tip to feet in rig px

BONES = {
    'root': (None, FEET),
    'body': ('root', (245.0, 800.0)),
    'chest': ('body', (245.0, 610.0)),
    'neck': ('chest', (242.0, 470.0)),
    'head': ('neck', (242.0, 428.0)),
    'earL': ('head', (196.0, 248.0)),
    'earR': ('head', (292.0, 248.0)),
}

_rig = None


def _band(h, w, y0, y1, soft=30.0):
    y = np.arange(h, dtype=np.float32)[:, None]
    m = np.clip((y - y0 + soft) / (2 * soft), 0, 1) * np.clip((y1 - y + soft) / (2 * soft), 0, 1)
    return np.repeat(m, w, 1)


def rig():
    global _rig
    if _rig is not None:
        return _rig
    base = np.asarray(puppet.cat_frame('deadpan'))
    h, w = base.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    head = (yy < 428).astype(np.float32)
    earL = ((yy < 250) & (xx < 225)).astype(np.float32)
    earR = ((yy < 250) & (xx > 262)).astype(np.float32)
    maps = {
        'root': (yy > 790).astype(np.float32),
        'body': _band(h, w, 640, 790),
        'chest': _band(h, w, 470, 640),
        'neck': _band(h, w, 428, 470, 12),
        'head': head * (1 - earL) * (1 - earR),
        'earL': earL,
        'earR': earR,
    }
    variants = {}
    for m in MOODS:
        for b in (0.0, 0.5, 1.0):
            if m == 'meow' and b:
                continue
            variants['%s%s' % (m, '' if not b else '_b%d' % int(b * 10))] = np.asarray(puppet.cat_frame(m, blink=b))
    r = Rig(base, BONES, maps, step=7, blur=7.0, extra_alpha=[v[..., 3] for v in variants.values()])
    for k, v in variants.items():
        r.add_texture(k, v)
    _rig = r
    return r


def _yaw_warp(yaw, nod):
    """Head turn / nod by parallax: the face moves more than the head's outline."""
    if not yaw and not nod:
        return ()
    cx, cy = HEAD_C

    def fn(V):
        dx, dy = V[:, 0] - cx, V[:, 1] - cy
        r = np.sqrt((dx / 120) ** 2 + (dy / 110) ** 2)
        g = np.clip(1 - r, 0, 1) ** 1.5
        inhead = (V[:, 1] < 430).astype(np.float64)
        out = np.zeros_like(V, dtype=np.float64)
        out[:, 0] = yaw * 22 * g * inhead
        out[:, 1] = nod * 14 * g * inhead
        return out
    return (fn,)


class CatSit:
    """A sitting cat with tracks: x, y (screen feet), height (screen px), lean, tilt, nod,
    yaw (-1..1), crouch (0..1), earL / earR (deg), alpha; mood (Steps); meows; blinks."""

    def __init__(self, seed=0, x=540, y=1500, height=420, mood='deadpan', blink_every=(2.2, 4.5)):
        self.x, self.y, self.height = Track(x), Track(y), Track(height)
        self.lean, self.tilt, self.nod, self.yaw = Track(), Track(), Track(), Track()
        self.crouch, self.earL, self.earR = Track(), Track(), Track()
        self.rot = Track()            # whole-body rotation about the feet (jumps)
        self.mood = Steps(mood)
        self.flip = Steps(False)
        self.meows = []
        self.flicks = []
        rnd = random.Random(seed)
        self.blinks, t = [], rnd.uniform(0.6, 1.6)
        while t < 120:
            self.blinks.append(t)
            t += rnd.uniform(*blink_every)
        self.phase = rnd.uniform(0, 6.28)
        self.rnd = rnd

    def meow(self, t, dur=0.55):
        self.meows.append((t, dur))
        return self

    def flick(self, t, ear='R'):
        self.flicks.append((t, ear))
        return self

    def blink_at(self, t):
        self.blinks.append(t)
        self.blinks.sort()
        return self

    # ------------------------------------------------------------- state

    def _meow_amt(self, t):
        for t0, d in self.meows:
            if t0 - 0.12 <= t <= t0 + d + 0.12:
                u = (t - t0) / d
                return t0, d, u
        return None

    def _blink(self, t):
        for b in self.blinks:
            dt = t - b
            if 0 <= dt < 0.16:
                return 1.0 if 0.04 <= dt < 0.11 else 0.5
        return 0.0

    def state(self, t):
        mood = self.mood(t)
        tex = mood
        breathe = math.sin(t * 2 * math.pi / 2.6 + self.phase)
        crouch = self.crouch(t)
        head_rot = self.tilt(t) + 1.2 * math.sin(t * 0.9 + self.phase)
        nod = self.nod(t)
        sy_head = 1.0
        m = self._meow_amt(t)
        if m:
            t0, d, u = m
            if -0.12 / d <= u < 0:                     # anticipation: dip the head
                k = ease((u * d + 0.12) / 0.12)
                nod += 0.5 * k
                sy_head = 1 - 0.05 * k
            elif u <= 1:
                tex = 'meow'
                k = math.sin(min(1, u) * math.pi)
                nod -= 0.9 * k
                head_rot += 3 * math.sin(u * math.pi * 2)
                sy_head = 1 + 0.07 * k
                crouch -= 0.15 * k
            else:
                k = ease((u * d - d) / 0.12)
                sy_head = 1 - 0.03 * (1 - k)
        b = self._blink(t) if tex != 'meow' else 0.0
        if b:
            tex = '%s_b%d' % (tex, int(b * 10))
        ear_l, ear_r = self.earL(t), self.earR(t)
        for tf, ear in self.flicks:
            dt = t - tf
            if 0 <= dt < 0.35:
                a = -14 * math.sin(dt / 0.35 * math.pi * 2) * (1 - dt / 0.35)
                if ear == 'L':
                    ear_l -= a
                else:
                    ear_r += a
        pose = {
            'root': dict(rot=self.rot(t)),
            'body': dict(sy=(1 + 0.012 * breathe) * (1 - 0.18 * crouch), sx=1 + 0.006 * breathe + 0.08 * crouch),
            'chest': dict(rot=self.lean(t)),
            'neck': dict(dy=-1.5 * breathe),
            'head': dict(rot=head_rot, sy=sy_head, sx=2 - sy_head if sy_head != 1 else 1),
            'earL': dict(rot=ear_l),
            'earR': dict(rot=ear_r),
        }
        return pose, tex, self.yaw(t), nod

    def draw(self, frame, t, tint=None):
        r = rig()
        pose, tex, yaw, nod = self.state(t)
        scale = self.height(t) / SRC_H
        img, (x0, y0) = r.render(pose, scale, (self.x(t), self.y(t)), FEET, tex,
                                 warps=_yaw_warp(yaw, nod), flip=self.flip(t))
        if tint is not None:
            a = np.asarray(img).astype(np.float32)
            a[..., :3] *= np.array(tint, np.float32)
            from PIL import Image
            img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA')
        frame.alpha_composite(img, (x0, y0)) if x0 >= 0 and y0 >= 0 else _paste(frame, img, x0, y0)
        return r.point(pose, (242, 300), 'head')


def _paste(frame, img, x0, y0):
    """alpha_composite with negative offsets."""
    cx0, cy0 = max(0, -x0), max(0, -y0)
    if cx0 >= img.width or cy0 >= img.height:
        return
    frame.alpha_composite(img.crop((cx0, cy0, img.width, img.height)), (x0 + cx0, y0 + cy0))
