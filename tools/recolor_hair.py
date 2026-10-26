"""Shift the girl's hair in a generated image to a clear red.

Hair = reddish-brown pixels (hue near 0-14 deg, saturated) inside a box around her; the
wooden furniture (hue ~15-30 deg) and her skin (low saturation) stay out of the mask.

Usage: python tools/recolor_hair.py <in> <out> x0 y0 x1 y1 [preview.png]
"""
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

TARGET_HUE = 2.0 / 360        # clear red
SAT_GAIN = 1.45
VAL_GAIN = 1.12
VMAX = 0.78                   # pinker, lighter things (shorts, blush) stay out


def rgb_to_hsv(a):
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mx, mn = a.max(-1), a.min(-1)
    d = mx - mn + 1e-9
    h = np.where(mx == r, ((g - b) / d) % 6, np.where(mx == g, (b - r) / d + 2, (r - g) / d + 4)) / 6
    s = np.where(mx > 0, (mx - mn) / (mx + 1e-9), 0)
    return h, s, mx


def hsv_to_rgb(h, s, v):
    i = np.floor(h * 6).astype(int) % 6
    f = h * 6 - np.floor(h * 6)
    p, q, t = v * (1 - s), v * (1 - f * s), v * (1 - (1 - f) * s)
    out = np.zeros(h.shape + (3,))
    for k, (r, g, b) in enumerate([(v, t, p), (q, v, p), (p, v, t), (p, q, v), (t, p, v), (v, p, q)]):
        m = i == k
        out[m] = np.stack([r[m], g[m], b[m]], -1)
    return out


def main(src, dst, x0, y0, x1, y1, preview=None):
    im = np.asarray(Image.open(src).convert('RGB')).astype(float) / 255
    h, s, v = rgb_to_hsv(im)
    hue = h * 360
    m = (((hue < 14) | (hue > 345)) & (s > 0.28) & (v > 0.12) & (v < VMAX)).astype(float)
    box = np.zeros_like(m)
    box[y0:y1, x0:x1] = 1
    m *= box
    m = ndimage.binary_opening(m > 0.5, iterations=1)
    lab, n = ndimage.label(m)                     # drop stray specks (wood grain etc.)
    sizes = ndimage.sum(m, lab, range(1, n + 1))
    m = np.isin(lab, [i + 1 for i, sz in enumerate(sizes) if sz > 300]).astype(float)
    m = ndimage.gaussian_filter(m, 1.2)
    nh = np.full_like(h, TARGET_HUE)
    ns = np.clip(s * SAT_GAIN, 0, 1)
    nv = np.clip(v * VAL_GAIN, 0, 1)
    red = hsv_to_rgb(nh, ns, nv)
    out = im * (1 - m[..., None]) + red * m[..., None]
    Image.fromarray((np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)).save(dst, quality=95)
    if preview:
        Image.fromarray((m * 255).astype(np.uint8)).save(preview)


if __name__ == '__main__':
    a = sys.argv
    main(a[1], a[2], *map(int, a[3:7]), *(a[7:8] or [None]))
