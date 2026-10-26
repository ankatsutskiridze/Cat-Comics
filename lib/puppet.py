"""Puppet animation for cut-out character images (PIL).

The cat puppet = the big sitting body from the Gemini sheet with its head removed, plus the
sheet's expression heads swapped on top. The head can tilt, the body breathes and sways,
and blinking / meowing / moods are head swaps.
"""
import math
import os

import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CUT = os.path.join(ROOT, 'characters', 'cat', 'images', 'cut')

NECK_Y = 262          # sit_big: rows above this are the head (measured off its width profile)
TINT = (1.0, 1.0, 1.0)

_cache = {}


def _load(name):
    if name not in _cache:
        im = Image.open(os.path.join(CUT, name + '.png')).convert('RGBA')
        a = np.asarray(im).astype(float)
        # defringe: the grey JPEG halo on the edge ring -> outline colour
        al = a[..., 3]
        from PIL import ImageFilter
        inner = np.asarray(Image.fromarray(al.astype(np.uint8)).filter(ImageFilter.MinFilter(3))).astype(float)
        ring = (al > 0) & (inner < 250)
        a[ring, :3] = np.minimum(a[ring, :3], 50)
        a[..., 3] = np.minimum(al, inner * 0.6 + al * 0.4)
        a[..., :3] *= np.array(TINT)
        _cache[name] = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA')
    return _cache[name]


def widest_row(im):
    a = np.asarray(im)[..., 3] > 128
    best = (0, 0, 0, 0)
    for y in range(a.shape[0]):
        xs = np.where(a[y])[0]
        if len(xs) and xs.max() - xs.min() > best[0]:
            best = (xs.max() - xs.min(), y, (xs.max() + xs.min()) / 2, 0)
    w, y, cx, _ = best
    return cx, y, w


def body():
    if 'body' not in _cache:
        im = _load('s_sit_big').copy()
        a = np.asarray(im).copy()
        a[:NECK_Y, :, 3] = 0
        _cache['body'] = Image.fromarray(a, 'RGBA')
        hx, hy, hw = widest_row(Image.fromarray(np.asarray(_load('s_sit_big'))[:NECK_Y + 10].copy(), 'RGBA'))
        _cache['head_anchor'] = (hx, hy, hw)
    return _cache['body']


CHIN_Y = 284         # sit_big: where a swapped head's bottom edge lands (overlaps the neck)


def head(mood, blink=0.0):
    """An expression head; blink 0..1 closes its eyes with a black lid from the top."""
    h = _load('s_head_' + mood)
    if blink <= 0:
        return h
    key = ('blink', mood, round(blink, 2))
    if key not in _cache:
        from scipy import ndimage
        a = np.asarray(h).copy()
        r, g, b = (a[..., i].astype(int) for i in range(3))
        eye = (r > 170) & (g > 165) & (b > 90) & (r - g < 30) & (a[..., 3] > 200)
        eye_d = ndimage.binary_dilation(eye, iterations=2)
        lab, n = ndimage.label(eye_d)
        fur = np.median(a[(a[..., 3] > 250) & ~eye_d & (r < 80)][:, :3], axis=0)
        for i, sl in enumerate(ndimage.find_objects(lab)):
            y0, y1 = sl[0].start, sl[0].stop
            cut = int(y0 + (y1 - y0) * min(1.0, blink))
            m = (lab == i + 1)
            m[cut:] = False
            a[m, :3] = fur
            if blink > 0.85:                 # a closed-eye line along the lower lid
                rows = np.where((lab == i + 1).any(1))[0]
                yy = int(y0 + (y1 - y0) * 0.72)
                xs = np.where((lab == i + 1)[yy])[0]
                if len(xs) > 4:
                    a[yy - 1:yy + 2, xs.min() + 2:xs.max() - 1, :3] = (226, 216, 160)
        _cache[key] = Image.fromarray(a, 'RGBA')
    return _cache[key]


def cat_frame(mood='deadpan', tilt=0.0, breathe=0.0, lean=0.0, squash=1.0, blink=0.0):
    """The whole sitting cat as one RGBA image, in sit_big pixels (feet at the bottom centre).

    tilt: head roll in degrees; breathe: -1..1 chest swell; lean: body sway in degrees;
    squash: vertical squash (landing) 0.8..1.2.
    """
    b = body()
    ax, ay, aw = _cache['head_anchor']
    W, H = b.width + 160, b.height + 140
    canvas = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    ox, oy = 80, 140
    bb = b
    if breathe:
        k = 1 + 0.018 * breathe
        bb = b.resize((int(b.width * (1 + 0.01 * breathe)), int(b.height * k)), Image.BILINEAR)
        oy -= bb.height - b.height
        ox -= (bb.width - b.width) // 2
    canvas.alpha_composite(bb, (ox, oy))
    h = head(mood, blink)
    hx, hy, hw = widest_row(_load('s_head_' + mood))
    k = aw / max(1, hw) * 0.97
    hh = h.resize((max(1, int(h.width * k)), max(1, int(h.height * k))), Image.LANCZOS)
    # bottom-centre of the head on the neck; pivot at the chin, then roll
    al = np.asarray(hh)[..., 3] > 128
    rows = np.where(al.any(1))[0]
    bot = rows.max()
    xs = np.where(al[max(0, bot - int(hh.height * 0.15)):bot + 1].any(0))[0]
    bcx = (xs.min() + xs.max()) / 2
    hh2 = hh.rotate(tilt, resample=Image.BICUBIC, expand=False, center=(bcx, bot))
    dy = (b.height * (1 + 0.018 * breathe) - b.height) if breathe else 0
    canvas.alpha_composite(hh2, (int(80 + ax - bcx), int(140 + CHIN_Y - bot - dy)))
    if lean or squash != 1.0:
        if squash != 1.0:
            canvas = canvas.resize((int(W / squash ** 0.5), int(H * squash)), Image.BILINEAR)
            c2 = Image.new('RGBA', (W, H), (0, 0, 0, 0))
            c2.alpha_composite(canvas, ((W - canvas.width) // 2, H - canvas.height)) if canvas.height <= H else None
            canvas = c2 if canvas.height <= H else canvas
        if lean:
            canvas = canvas.rotate(lean, resample=Image.BICUBIC, center=(canvas.width / 2, canvas.height))
    return canvas


def pose(name):
    """Any other cut-out pose (jump, walk_side, lying ...)."""
    return _load('s_' + name)
