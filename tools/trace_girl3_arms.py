"""Trace the girl's arms and shirt sleeves into vectors -> characters/girl/girl3_arms.npz,
used by lib/girl3.py.

- Upper arm and forearm + hand: from Anka's parts sheet (characters/girl/images/parts_red.png,
  cut to characters/girl/images/cut/parts_3.png and parts_10.png): base fill, shade, ink.
  Each piece gets its joints measured off its silhouette (top cap centre, bottom cap centre /
  the wrist's narrowest row).
- The sleeves: cut out of the master figure's tee (characters/rig/girl_src.png), so a sleeve
  rides its upper arm instead of staying on the shirt when the arm moves.

Usage: python tools/trace_girl3_arms.py
"""
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from trace_girl3 import poly_mask, rings_of  # noqa: E402

CUT = os.path.join(ROOT, 'characters', 'girl', 'images', 'cut')
SRC = os.path.join(ROOT, 'characters', 'rig', 'girl_src.png')
OUT = os.path.join(ROOT, 'characters', 'girl', 'girl3_arms.npz')

# the master's sleeves (src px); each stops at the torso's side under it
SLEEVE_N = [(40, 290), (100, 276), (124, 284), (134, 320), (137, 446), (128, 454), (36, 424)]
SLEEVE_F = [(247, 292), (292, 298), (298, 462), (250, 464), (246, 400)]


def _fills(a, m, shade_rule, interior=False):
    r, g, b = (a[..., i] for i in range(3))
    al = a[..., 3] / 255.0
    lum = 0.3 * r + 0.59 * g + 0.11 * b
    base_col = tuple(int(v) for v in np.median(a[m & (lum > 150)][:, :3], axis=0))
    soft = ndimage.gaussian_filter(m.astype(np.float32), 0.7)
    out = [('base', base_col, rings_of(soft, 0, 0.4, 10))]
    sh_col, sh_mask = shade_rule(a, m, lum)
    out.append(('sh', sh_col, rings_of(sh_mask, 1.2, 0.6, 12)))
    ink = np.clip((135 - lum) / 50, 0, 1) * np.clip(al * 1.8, 0, 1) * ndimage.binary_dilation(m, iterations=2)
    if interior:            # only the lines inside (fingers, knuckles): the outline is drawn round the
        ink = ink * ndimage.binary_erosion(m, iterations=4)    # whole arm at once, so no joint shows
    out.append(('ink', (40, 14, 10), rings_of(ink, 0.45, 0.3, 2)))
    return out


def _skin_shade(a, m, lum):
    r, b = a[..., 0], a[..., 2]
    return (232, 176, 154), m & (lum < 196) & (lum > 120) & (r - b > 55)


def _shirt_shade(a, m, lum):
    return (172, 170, 124), m & (lum < 158) & (lum > 110)


def _joints(m, kind):
    ys = np.where(m.any(1))[0]
    y0, y1 = ys.min(), ys.max()

    def cx(y):
        xs = np.where(m[int(y)])[0]
        return (xs.min() + xs.max()) / 2, xs.max() - xs.min()
    top_x, top_w = cx(y0 + 30)
    top = (top_x, y0 + top_w * 0.5)
    if kind == 'upper':
        bx, bw = cx(y1 - 25)
        return top, (bx, y1 - bw * 0.5)
    # forearm + hand: the wrist is the narrowest row in the lower half before the hand flares
    best = None
    for y in range(int(y0 + (y1 - y0) * 0.45), int(y0 + (y1 - y0) * 0.75)):
        x, wdt = cx(y)
        if best is None or wdt < best[2]:
            best = (x, y, wdt)
    return top, (best[0], best[1])


def main():
    pieces = {}
    for name, fn, kind in (('upper', 'parts_3.png', 'upper'), ('fore', 'parts_10.png', 'fore')):
        a = np.asarray(Image.open(os.path.join(CUT, fn)).convert('RGBA')).astype(float)
        m = a[..., 3] > 128
        j0, j1 = _joints(m, kind)
        pieces[name] = dict(fills=_fills(a, m, _skin_shade, interior=True), j0=j0, j1=j1, h=float(m.shape[0]))
        print(name, 'joints', j0, j1)
    a = np.asarray(Image.open(SRC).convert('RGBA')).astype(float)
    r, g, b = a[..., 0], a[..., 2 - 1], a[..., 2]
    op = a[..., 3] > 128
    lum = 0.3 * a[..., 0] + 0.59 * a[..., 1] + 0.11 * a[..., 2]
    hair = (a[..., 0] > a[..., 1] * 1.6) & (a[..., 0] > a[..., 2] * 1.6) & (a[..., 0] > 70)
    shirt = (a[..., 1] >= a[..., 0] - 12) & (a[..., 1] > a[..., 2] + 22) & (lum > 100)
    for name, poly in (('sleeve_n', SLEEVE_N), ('sleeve_f', SLEEVE_F)):
        reg = poly_mask(op.shape, [poly]) & op & ~hair
        m = ndimage.binary_closing(reg & (shirt | (lum < 95)), iterations=2)
        m = ndimage.binary_fill_holes(m) & reg
        lab, n = ndimage.label(m)
        sizes = ndimage.sum(m, lab, range(1, n + 1))
        m = lab == (int(np.argmax(sizes)) + 1)
        pieces[name] = dict(fills=_fills(a, m, _shirt_shade))
    # pack
    rings, meta, fmeta, cols, tags = [], [], [], [], []
    names = list(pieces)
    for pi, name in enumerate(names):
        for fi, (tag, col, shapes) in enumerate(pieces[name]['fills']):
            fmeta.append((pi, fi))
            cols.append(col)
            tags.append(tag)
            for si, rr in enumerate(shapes):
                for ring in rr:
                    rings.append(ring)
                    meta.append((pi, fi, si))
    np.savez_compressed(
        OUT, names=np.array(names), fill_meta=np.array(fmeta), fill_col=np.array(cols, np.float32) / 255,
        fill_tag=np.array(tags), ring_len=np.array([len(x) for x in rings]), ring_pts=np.concatenate(rings),
        ring_meta=np.array(meta),
        joints=np.array([pieces['upper']['j0'] + pieces['upper']['j1'], pieces['fore']['j0'] + pieces['fore']['j1']],
                        np.float32),
        sleeve_n=np.array(SLEEVE_N, np.float32), sleeve_f=np.array(SLEEVE_F, np.float32))
    print(OUT, len(rings), 'rings')


if __name__ == '__main__':
    main()
