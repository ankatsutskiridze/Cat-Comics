"""The cat walking, alive: the Gemini side-view walking drawing (characters/cat/poses/
walk_side.png, facing left) on a mesh rig: four two-segment legs stepping in a walk gait
(swing legs lift, stance legs stay planted), body bob, head nod, a tail that sways.

    w = CatWalk(x0=900, x1=-200, y=1800, height=360, t0=12.6, t1=15.2)
    w.draw(frame, t)

Moving right? pass x1 > x0: the drawing is mirrored.
"""
import math
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rig import Rig, Track, Pendulum, ease  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'characters', 'cat', 'poses', 'walk_side.png')
FEET_Y = 466.0
FEET = (220.0, FEET_Y)
SRC_H = 466.0 - 118.0          # ear tip to paws

# legs: name -> (hip/shoulder, knee/elbow, paw, gait phase); phases = lateral-sequence walk
LEGS = {
    'ff': ((118, 335), (80, 405), (42, 460), 0.25),     # front, far side (reaching forward)
    'fn': ((172, 350), (186, 412), (182, 460), 0.75),   # front, near side
    'hn': ((288, 355), (306, 415), (272, 456), 0.50),   # hind, near side
    'hf': ((364, 335), (392, 402), (405, 460), 0.00),   # hind, far side (pushing back)
}
TAIL = [(352, 252), (374, 150), (390, 62)]

BONES = {'root': (None, FEET), 'body': ('root', (235.0, 330.0)), 'head': ('body', (128.0, 292.0))}
for n, (hip, knee, paw, ph) in LEGS.items():
    BONES[n + '_u'] = ('body', hip)
    BONES[n + '_l'] = (n + '_u', knee)
BONES['tail1'] = ('body', TAIL[0])
BONES['tail2'] = ('tail1', TAIL[1])
BONES['tail3'] = ('tail2', TAIL[2])

_rig = None


def _seg_dist(px, py, a, b):
    ax, ay = a
    bx, by = b
    vx, vy = bx - ax, by - ay
    t = np.clip(((px - ax) * vx + (py - ay) * vy) / (vx * vx + vy * vy), 0, 1)
    return np.hypot(px - ax - t * vx, py - ay - t * vy)


def rig():
    global _rig
    if _rig is not None:
        return _rig
    im = np.asarray(Image.open(SRC).convert('RGBA'))
    h, w = im.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    leg_zone = np.clip((yy - 352) / 22, 0, 1)          # legs hang below the belly
    segs = {}
    for n, (hip, knee, paw, _) in LEGS.items():
        segs[n + '_u'] = _seg_dist(xx, yy, hip, knee)
        segs[n + '_l'] = _seg_dist(xx, yy, knee, paw)
    D = np.stack(list(segs.values()))
    near = np.argmin(D, 0)
    maps = {}
    for i, n in enumerate(segs):
        maps[n] = (near == i) * leg_zone
    tail = ((xx > 335) & (yy < 268)).astype(np.float32)
    maps['tail1'] = tail * (yy >= 175)
    maps['tail2'] = tail * (yy < 175) * (yy >= 95)
    maps['tail3'] = tail * (yy < 95)
    head = ((xx < 132) & (yy < 330)).astype(np.float32) * (1 - leg_zone)
    maps['head'] = head
    maps['body'] = (1 - leg_zone) * (1 - tail) * (1 - head)
    maps['root'] = np.zeros((h, w), np.float32)
    # z-order: far legs, then the body (head, tail), then near legs; leg layers reach a
    # little up into the body so a swinging leg never opens a gap at the hip
    names = list(segs)
    reach = np.clip((yy - 330) / 6, 0, 1)
    body_m = 1 - np.clip((yy - 352) / 4, 0, 1)

    def leg_mask(*legs):
        idx = [i for i, n in enumerate(names) if n[:2] in legs]
        return np.isin(near, idx) * reach
    layers = [('far', leg_mask('ff', 'hf')), ('body', body_m), ('near', leg_mask('fn', 'hn'))]
    _rig = Rig(im, BONES, maps, step=6, blur=4.0, layers=layers)
    return _rig


class CatWalk:
    """Walks from x0 to x1 between t0 and t1 (screen px), feet on y; `cadence` steps/s."""

    def __init__(self, x0, x1, y, height, t0, t1, cadence=None, amp=15.0):
        self.x0, self.x1, self.y, self.height, self.t0, self.t1 = x0, x1, y, height, t0, t1
        self.amp = amp
        if cadence is None:               # planted feet: one stride per cycle at this speed
            stride = 2 * math.radians(amp) * 125 * height / SRC_H
            cadence = abs(x1 - x0) / max(1e-6, t1 - t0) / stride
        self.cadence = cadence
        self.tail = [Pendulum(90, 40, 5, 0.6) for _ in range(3)]
        self._tail_t = None
        self._tail_cache = {}

    def x(self, t):
        u = (t - self.t0) / (self.t1 - self.t0)
        return self.x0 + (self.x1 - self.x0) * min(1, max(0, u))

    def pose(self, t):
        ph = (t - self.t0) * self.cadence
        moving = self.t0 <= t <= self.t1
        p = {}
        A = self.amp
        for n, (hip, knee, paw, off) in LEGS.items():
            s = 2 * math.pi * (ph + off)
            if not moving:
                s = 2 * math.pi * off
            swing = math.sin(s)                          # +1 = forward (left)
            fwd = math.cos(s) > 0                        # moving forward = lifted
            lift = max(0.0, math.cos(s)) if moving else 0.0
            bias = {'ff': -8, 'fn': 0, 'hn': 0, 'hf': 8}[n]
            p[n + '_u'] = dict(rot=A * swing + bias - (A * math.sin(2 * math.pi * off)))
            bend = (-1 if n[0] == 'f' else 1) * 28 * lift   # elbows fold back, hocks fold forward
            p[n + '_l'] = dict(rot=bend)
        bob = abs(math.sin(2 * math.pi * ph)) if moving else 0.0
        p['body'] = dict(dy=-4 * bob, rot=1.2 * math.sin(2 * math.pi * ph) if moving else 0)
        p['head'] = dict(rot=2.5 * math.sin(2 * math.pi * ph + 0.8) if moving else 0)
        sway = 7 * math.sin(2 * math.pi * ph * 0.5)
        p['tail1'] = dict(rot=sway * 0.5)
        p['tail2'] = dict(rot=sway * 0.8)
        p['tail3'] = dict(rot=sway * 1.2)
        return p

    def draw(self, frame, t, tint=None):
        r = rig()
        scale = self.height / SRC_H
        flip = self.x1 > self.x0
        img, (x0, y0) = r.render(self.pose(t), scale, (self.x(t), self.y), FEET, flip=flip)
        if tint is not None:
            a = np.asarray(img).astype(np.float32)
            a[..., :3] *= np.array(tint, np.float32)
            img = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA')
        return img, (x0, y0)
