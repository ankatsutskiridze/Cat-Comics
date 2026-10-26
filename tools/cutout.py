"""Cut figures out of a generated image with a flat light background.

Background = pixels close to the corner colour that are connected to the image border, so
light parts INSIDE a figure (eyes, teeth) stay. Each remaining blob above a size threshold
becomes its own RGBA PNG, trimmed to its bounding box.

Usage: python tools/cutout.py <image> <out_dir> <prefix> [min_area]
Prints one line per figure: index, bbox, area (sorted left-to-right, top-to-bottom rows).
"""
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

TOL = 26          # max colour distance from the background colour


def cut(path, out_dir, prefix, min_area=4000):
    im = np.asarray(Image.open(path).convert('RGB')).astype(float)
    bg = np.median(np.concatenate([im[:8, :8].reshape(-1, 3), im[:8, -8:].reshape(-1, 3),
                                   im[-8:, :8].reshape(-1, 3), im[-8:, -8:].reshape(-1, 3)]), axis=0)
    near = np.linalg.norm(im - bg, axis=-1) < TOL
    lab, _ = ndimage.label(near)
    border = np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
    bgmask = np.isin(lab, border[border > 0])
    # big enclosed background-coloured holes (gaps between legs) are background too;
    # small light bits inside a figure (eyes, teeth, highlights) are not
    holes, nh = ndimage.label(near & ~bgmask)
    if nh:
        sizes = ndimage.sum(np.ones_like(holes), holes, range(1, nh + 1))
        bgmask |= np.isin(holes, [i + 1 for i, sz in enumerate(sizes) if sz > 250])
    fg = ~bgmask
    fg = ndimage.binary_opening(fg, iterations=1)
    figs, n = ndimage.label(fg)
    objs = ndimage.find_objects(figs)
    # soft alpha: distance-based feather of 1 px on the edge
    dist_out = ndimage.distance_transform_edt(~fg)
    alpha_full = np.clip(1.0 - dist_out, 0, 1)
    alpha_full[fg] = 1.0
    items = []
    for i, sl in enumerate(objs):
        area = int((figs[sl] == i + 1).sum())
        if area < min_area:
            continue
        items.append((sl, i + 1, area))
    items.sort(key=lambda it: (round(it[0][0].start / 300), it[0][1].start))
    os.makedirs(out_dir, exist_ok=True)
    for k, (sl, idx, area) in enumerate(items):
        y0, y1 = max(0, sl[0].start - 3), min(im.shape[0], sl[0].stop + 3)
        x0, x1 = max(0, sl[1].start - 3), min(im.shape[1], sl[1].stop + 3)
        own = ndimage.binary_dilation(figs[y0:y1, x0:x1] == idx, iterations=2)
        a = alpha_full[y0:y1, x0:x1] * own
        rgba = np.dstack([im[y0:y1, x0:x1], a * 255]).astype(np.uint8)
        name = os.path.join(out_dir, '%s_%d.png' % (prefix, k))
        Image.fromarray(rgba, 'RGBA').save(name)
        print(k, (x0, y0, x1, y1), area, name)


if __name__ == '__main__':
    a = sys.argv
    cut(a[1], a[2], a[3], int(a[4]) if len(a) > 4 else 4000)
