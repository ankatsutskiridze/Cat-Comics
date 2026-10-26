"""Build a front-facing SITTING girl from the master sheet's standing figure (no new image):
the upper body (head to the shorts' hem) over the lower legs moved up, so the knees sit just
under the hem as they do when someone sits facing you. Also removes the sheet's floor shadow.

Usage: python tools/make_girl_sit_front.py  -> characters/girl/images/cut/sit_front.png
"""
import os

import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CUT = os.path.join(ROOT, 'characters', 'girl', 'images', 'cut')

HEM = 668          # bottom of the shorts (rows of master_0)
KNEE_TOP = 800     # a little above the knees
OVERLAP = -20      # the shins start just under the knee ends
KNEE_TOP_ROW = 60  # a row of the lower-leg crop where both legs are separate
SKIN = (247, 208, 184, 255)
SHADE = (232, 178, 152, 255)
LINE = (59, 38, 35, 255)


def main():
    im = Image.open(os.path.join(CUT, 'master_0.png')).convert('RGBA')
    a = np.asarray(im).copy()
    # drop the grey floor shadow under the shoes
    rgb = a[..., :3].astype(int)
    grey = (np.abs(rgb[..., 0] - rgb[..., 2]) < 14) & (rgb.min(-1) > 150) & (rgb.max(-1) < 222)
    grey[:1120] = False
    a[grey, 3] = 0
    im = Image.fromarray(a, 'RGBA')
    upper = im.crop((0, 0, im.width, HEM))
    lower = im.crop((0, KNEE_TOP, im.width, im.height))
    out = Image.new('RGBA', (im.width + 40, HEM - OVERLAP + lower.height), (0, 0, 0, 0))
    # knees slightly apart, as when sitting
    lw = lower.resize((int(lower.width * 1.06), lower.height), Image.LANCZOS)
    lx = 20 - (lw.width - lower.width) // 2
    out.alpha_composite(lw, (lx, HEM - OVERLAP))
    # the thighs come straight at the camera: two rounded knee/thigh ends under the hem
    la = np.asarray(lw)[..., 3] > 128
    row = la[KNEE_TOP_ROW]
    runs = np.flatnonzero(np.diff(np.concatenate([[0], row.astype(int), [0]])))
    legs = [(runs[i], runs[i + 1]) for i in range(0, len(runs), 2)]
    d = ImageDraw.Draw(out)
    for (x0, x1) in legs[:2]:
        cx = lx + (x0 + x1) / 2
        w = (x1 - x0) * 0.62 + 6
        y0, y1 = HEM - 30, HEM + 62
        d.ellipse((cx - w, y0, cx + w, y1), fill=SKIN, outline=LINE, width=3)
        d.arc((cx - w * 0.55, y1 - 34, cx + w * 0.55, y1 - 6), 20, 160, fill=SHADE, width=4)
    out.alpha_composite(upper, (20, 0))
    out = out.crop(out.getbbox())
    p = os.path.join(CUT, 'sit_front.png')
    out.save(p)
    print(p, out.size)


if __name__ == '__main__':
    main()
