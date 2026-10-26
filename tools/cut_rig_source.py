"""Cut one figure out of a sheet with a flat light background, keeping light parts INSIDE it.

Background = pixels near the sheet colour (or near a drop-shadow colour) that are connected to
the crop's border. Nothing enclosed by the figure's outline is removed (eye whites, socks,
sneakers stay), unlike tools/cutout.py which drops big enclosed light areas.

Usage: python tools/cut_rig_source.py <sheet> <x0,y0,x1,y1> <out.png> [shadow r,g,b]
"""
import sys

import numpy as np
from PIL import Image
from scipy import ndimage


def cut(path, box, out, shadow=None, tol=22):
    x0, y0, x1, y1 = box
    im = np.asarray(Image.open(path).convert('RGB')).astype(float)[y0:y1, x0:x1]
    bg = np.median(np.concatenate([im[:4].reshape(-1, 3), im[:, :4].reshape(-1, 3)]), axis=0)
    near = np.linalg.norm(im - bg, axis=-1) < tol
    if shadow is not None:
        near |= np.linalg.norm(im - np.array(shadow, float), axis=-1) < 16
    lab, _ = ndimage.label(near)
    border = np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))
    fg = ~np.isin(lab, border[border > 0])
    fg = ndimage.binary_opening(fg, iterations=1)
    figs, n = ndimage.label(fg)
    sizes = ndimage.sum(fg, figs, range(1, n + 1))
    fg = figs == (int(np.argmax(sizes)) + 1)
    fg = ndimage.binary_fill_holes(fg) & (fg | ~near)
    # 1 px soft edge; the light halo on the rim is pulled toward the outline colour
    dist = ndimage.distance_transform_edt(~fg)
    a = np.clip(1.0 - dist, 0, 1)
    rows, cols = np.where(a > 0)
    sl = (slice(max(0, rows.min() - 4), rows.max() + 5), slice(max(0, cols.min() - 4), cols.max() + 5))
    rgba = np.dstack([im, a * 255])[sl].astype(np.uint8)
    Image.fromarray(rgba, 'RGBA').save(out)
    print(out, rgba.shape[1], 'x', rgba.shape[0], 'offset', (x0 + sl[1].start, y0 + sl[0].start))


if __name__ == '__main__':
    box = tuple(int(v) for v in sys.argv[2].split(','))
    sh = tuple(int(v) for v in sys.argv[4].split(',')) if len(sys.argv) > 4 else None
    cut(sys.argv[1], box, sys.argv[3], sh)
