"""Cut the cat's poses out of a Gemini pose sheet (flat light-grey background).

Usage: python tools/cut_cat_poses.py <sheet.jpg> <name1> <name2> ...
Names are given in reading order (top-to-bottom, then left-to-right, by each pose's
top-left corner); each pose -> characters/cat/poses/<name>.png (RGBA, trimmed, 8 px pad).
Blobs smaller than MIN_AREA (labels, specks) are dropped; enclosed background gaps stay
transparent.
"""
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, 'characters', 'cat', 'poses')
MIN_AREA = 5000
PAD = 8


def main(sheet, names):
    im = np.array(Image.open(sheet).convert('RGB')).astype(np.float32)
    bg = np.median(np.concatenate([im[:8].reshape(-1, 3), im[-8:].reshape(-1, 3)]), 0)
    d = np.abs(im - bg).max(2)
    warm = im[..., 0] - im[..., 2]                 # cream eyes, pink, skin: warm, the grey is not
    m = ndimage.binary_closing((d > 40) | (warm > 18), iterations=1)
    holes, nh = ndimage.label(ndimage.binary_fill_holes(m) & ~m)
    for i in range(1, nh + 1):                     # fill specks, keep background gaps (between legs)
        h = holes == i
        if h.sum() < 40 or d[h].mean() > 20:
            m |= h
    # light pixels joined to the outer background (e.g. a forearm fading into the grey) keep a
    # soft alpha from their warmth instead of turning solid
    light, nl = ndimage.label(im.mean(2) > 160)
    border = np.unique(np.concatenate([light[0], light[-1], light[:, 0], light[:, -1]]))
    fade = np.isin(light, border[border > 0])
    soft = np.clip(np.maximum((warm - 8) / 30.0, d / 150.0), 0, 1)
    lab, n = ndimage.label(m)
    objs = [(s, i + 1) for i, s in enumerate(ndimage.find_objects(lab)) if (lab[s] == i + 1).sum() >= MIN_AREA]
    # reading order: rows of poses whose tops are within 150 px, left to right inside a row
    objs.sort(key=lambda o: (o[0][0].start // 150, o[0][1].start))
    if len(objs) != len(names):
        sys.exit('found %d poses, got %d names' % (len(objs), len(names)))
    for (s, k), name in zip(objs, names):
        body = lab == k
        inner = ndimage.binary_erosion(body, iterations=2)
        edge = ndimage.binary_dilation(body, iterations=1) & ~inner
        # antialiased rim: a dark outline over grey -> alpha from the distance to the grey
        a = np.where(inner, 1.0, np.where(edge, soft, 0.0))
        a = np.where(body & fade, soft, a)
        rgb = np.where(a[..., None] > 0.02,
                       (im - (1 - a[..., None]) * bg) / np.maximum(a[..., None], 1e-3), 0)
        y0, y1 = max(0, s[0].start - PAD), min(im.shape[0], s[0].stop + PAD)
        x0, x1 = max(0, s[1].start - PAD), min(im.shape[1], s[1].stop + PAD)
        out = np.dstack([np.clip(rgb, 0, 255), a * 255])[y0:y1, x0:x1].astype(np.uint8)
        path = os.path.join(OUT, name + '.png')
        Image.fromarray(out, 'RGBA').save(path)
        print(path, out.shape[1], 'x', out.shape[0])


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2:])
