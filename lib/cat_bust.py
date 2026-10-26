"""The cat's close-up, alive: the Gemini deadpan face drawing (characters/cat/poses/
face_deadpan.png) on a mesh rig: it breathes, tilts its head, flicks an ear, and blinks a
slow deadpan blink (black lids come down over the cream eyes, as in lib/puppet.py).
"""
import math
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rig import Rig, Track  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'characters', 'cat', 'poses', 'face_deadpan.png')
BONES = {
    'root': (None, (220.0, 542.0)),
    'chest': ('root', (220.0, 542.0)),
    'head': ('chest', (218.0, 388.0)),
    'earL': ('head', (115.0, 120.0)),
    'earR': ('head', (322.0, 120.0)),
}
_rig = None


def lids(a, amount):
    """Close the cream eyes from the top by `amount` 0..1 with the fur colour."""
    a = a.copy()
    r, g, b = (a[..., i].astype(int) for i in range(3))
    eye = (r > 170) & (g > 160) & (b > 90) & (r - g < 40) & (a[..., 3] > 200)
    eye = ndimage.binary_opening(eye, iterations=1)
    eye_d = ndimage.binary_dilation(eye, iterations=3)
    lab, n = ndimage.label(eye_d)
    sizes = ndimage.sum(eye_d, lab, range(1, n + 1))
    fur = np.median(a[(a[..., 3] > 250) & ~eye_d & (r < 80)][:, :3], axis=0)
    ink = (28, 20, 20)
    from PIL import ImageDraw
    for i, sl in enumerate(ndimage.find_objects(lab)):
        if sizes[i] < 400:
            continue
        y0, y1 = sl[0].start, sl[0].stop
        x0, x1 = sl[1].start, sl[1].stop
        m = ndimage.binary_dilation(lab == i + 1, iterations=6)     # the eye with its outline
        if amount >= 1.0:
            a[m, :3] = fur
            # closed: a thin cream crescent, like the sheet's sleepy face
            im = Image.fromarray(a, 'RGBA')
            d = ImageDraw.Draw(im)
            yc = y0 + (y1 - y0) * 0.62
            d.arc((x0 + 6, yc - (y1 - y0) * 0.35, x1 - 6, yc + (y1 - y0) * 0.25), 20, 160,
                  fill=(226, 214, 160, 255), width=5)
            a = np.asarray(im).copy()
            continue
        cut = int(y0 + (y1 - y0) * amount)
        mm = m.copy()
        mm[cut:] = False
        a[mm, :3] = fur
        xs = np.where(m[min(cut, y1 - 3)])[0]
        if len(xs) > 4:                              # the lid's dark edge
            a[max(0, cut - 2):cut + 2, xs.min():xs.max() + 1, :3] = ink
    return a


def open_mouth(a, k=1.0):
    """Paint the frown out and an open mouth in (for speaking a word), size k 0..1."""
    from PIL import ImageDraw
    a = a.copy()
    r, g, b = (a[..., i].astype(int) for i in range(3))
    reg = np.zeros(r.shape, bool)
    reg[318:356, 190:252] = True
    fur = np.median(a[310:360, 160:180][..., :3].reshape(-1, 3), axis=0)
    pink = reg & (r > 90) & (r - b > 15)
    a[ndimage.binary_dilation(pink, iterations=2) & reg, :3] = fur
    im = Image.fromarray(a, 'RGBA')
    d = ImageDraw.Draw(im)
    cx, cy, rx, ry = 221, 338, 13 + 4 * k, 6 + 10 * k
    d.ellipse((cx - rx, cy - ry * 0.4, cx + rx, cy + ry * 1.6), fill=(96, 34, 44, 255), outline=(25, 16, 18, 255), width=3)
    d.ellipse((cx - rx * 0.6, cy + ry * 0.7, cx + rx * 0.6, cy + ry * 1.5), fill=(226, 120, 130, 255))
    return np.asarray(im).copy()


def rig():
    global _rig
    if _rig is not None:
        return _rig
    im = np.asarray(Image.open(SRC).convert('RGBA'))
    h, w = im.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    head = np.clip((395 - yy) / 20, 0, 1)
    earL = ((yy < 150) & (xx < 190)).astype(np.float32)
    earR = ((yy < 150) & (xx > 245)).astype(np.float32)
    maps = {'root': np.zeros((h, w), np.float32), 'chest': 1 - head,
            'head': head * (1 - earL) * (1 - earR), 'earL': earL, 'earR': earR}
    r = Rig(im, BONES, maps, step=8, blur=8.0)
    for k in (0.35, 0.7, 1.0):
        r.add_texture('lid%d' % int(k * 100), lids(im, k))
    r.add_texture('talk1', open_mouth(im, 0.45))
    r.add_texture('talk2', open_mouth(im, 1.0))
    _rig = r
    return r


class CatBust:
    def __init__(self):
        self.tilt = Track()
        self.blinks = []           # (t, duration): slow deadpan blinks
        self.flicks = []
        self.words = []            # (t0, t1, syllables): the mouth opens and closes

    def state(self, t):
        b = math.sin(t * 2 * math.pi / 2.8)
        tex = 'base'
        for t0, d in self.blinks:
            u = (t - t0) / d
            if 0 <= u < 1:
                k = math.sin(u * math.pi)              # down, hold-ish, up
                k = min(1.0, k * 1.25)
                tex = 'base' if k < 0.2 else 'lid35' if k < 0.5 else 'lid70' if k < 0.85 else 'lid100'
        for t0, t1, n in self.words:
            if t0 <= t < t1:
                ph = (t - t0) / (t1 - t0) * n
                o = math.sin((ph % 1) * math.pi)
                tex = 'talk2' if o > 0.6 else 'talk1' if o > 0.2 else 'base'
        er = 0.0
        for tf in self.flicks:
            dt = t - tf
            if 0 <= dt < 0.4:
                er = 16 * math.sin(dt / 0.4 * 2 * math.pi) * (1 - dt / 0.4)
        pose = {'chest': dict(sy=1 + 0.012 * b, sx=1 + 0.006 * b),
                'head': dict(rot=self.tilt(t) + 0.8 * math.sin(t * 0.8), dy=-1.5 * b),
                'earR': dict(rot=er), 'earL': dict(rot=-0.3 * er)}
        return pose, tex

    def render(self, t, scale, at):
        """at = screen point of the bottom-centre of the drawing."""
        pose, tex = self.state(t)
        return rig().render(pose, scale, at, (220.0, 542.0), tex)
