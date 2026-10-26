"""Green-screen cut-out: key out the green background, despill the edges, split into figures.

Usage: python tools/chroma_cut.py <image> <out_dir> <prefix> [min_area]
Writes <prefix>_<k>.png (RGBA, trimmed) per figure, left-to-right in rows; prints the boxes.
"""
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage


def key(im):
    r, g, b = im[..., 0], im[..., 1], im[..., 2]
    greenness = g - np.maximum(r, b)              # big on the screen, ~0 or negative on figures
    a = np.clip(1.0 - (greenness - 30) / 60.0, 0, 1)
    # despill: pull green down to the max of red/blue where it dominates
    out = im.copy()
    out[..., 1] = np.minimum(g, np.maximum(r, b) + 8)
    return out, a


def cut(path, out_dir, prefix, min_area=3000):
    im = np.asarray(Image.open(path).convert('RGB')).astype(float)
    rgb, a = key(im)
    fg = a > 0.5
    fg = ndimage.binary_opening(fg, iterations=1)
    figs, n = ndimage.label(fg)
    objs = ndimage.find_objects(figs)
    items = []
    for i, sl in enumerate(objs):
        area = int((figs[sl] == i + 1).sum())
        if area >= min_area:
            items.append((sl, i + 1, area))
    items.sort(key=lambda it: (round(it[0][0].start / 250), it[0][1].start))
    os.makedirs(out_dir, exist_ok=True)
    for k, (sl, idx, area) in enumerate(items):
        y0, y1 = max(0, sl[0].start - 3), min(im.shape[0], sl[0].stop + 3)
        x0, x1 = max(0, sl[1].start - 3), min(im.shape[1], sl[1].stop + 3)
        own = ndimage.binary_dilation(figs[y0:y1, x0:x1] == idx, iterations=2)
        al = a[y0:y1, x0:x1] * own
        rgba = np.dstack([rgb[y0:y1, x0:x1], al * 255]).clip(0, 255).astype(np.uint8)
        name = os.path.join(out_dir, '%s_%d.png' % (prefix, k))
        Image.fromarray(rgba, 'RGBA').save(name)
        print(k, (x0, y0, x1, y1), area, name)


if __name__ == '__main__':
    a = sys.argv
    cut(a[1], a[2], a[3], int(a[4]) if len(a) > 4 else 3000)
