"""Measure the girl's vector model off the master sheet's big standing figure
(characters/rig/girl_src.png) -> characters/girl/girl3_model.npz, used by lib/girl3.py.

Every body part becomes vector shapes: a base fill (its silhouette, smoothed), shade and
light fills inside it, and its interior ink lines as centre-line strokes with widths. Parts
are separated by colour (hair red, skin, sage shirt, pink shorts, white socks / sneakers) and
by hand-drawn region polygons where colour alone cannot tell them apart (near / far leg,
fringe, the lock over the chest, the two eyes).

Usage: python tools/trace_girl3.py
"""
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'lib'))
from girl3_trace import _chains, _thin  # noqa: E402

SRC = os.path.join(ROOT, 'characters', 'rig', 'girl_src.png')
OUT = os.path.join(ROOT, 'characters', 'girl', 'girl3_model.npz')

# region polygons (src px)
FACE_HULL = [(116, 96), (175, 72), (250, 88), (272, 140), (268, 190), (240, 225), (196, 236), (160, 232),
             (122, 214), (112, 170)]
FRONT_LOCK = [(118, 200), (160, 222), (180, 262), (186, 330), (180, 455), (150, 462), (128, 340), (108, 240)]
EYE_N = [(112, 182), (122, 164), (142, 154), (168, 150), (194, 152), (196, 168), (190, 192), (172, 200),
         (144, 200), (126, 192)]
EYE_F = [(208, 154), (220, 138), (240, 128), (258, 122), (264, 128), (262, 152), (256, 174), (238, 178),
         (218, 174)]
MOUTH = [(188, 194), (230, 188), (230, 212), (188, 212)]
NOSE = [(205, 164), (224, 164), (224, 186), (205, 186)]
BROW_F = [(212, 112), (264, 104), (266, 126), (214, 136)]
# the far leg (viewer's right) from the shorts' hem down, and its foot
FAR_LEG = [(168, 640), (262, 640), (240, 760), (214, 880), (204, 990), (300, 990), (300, 1190), (150, 1190),
           (150, 990), (166, 880), (160, 760)]
NEAR_SHOE_OVER = [(80, 995), (150, 995), (160, 1040), (168, 1066), (186, 1100), (205, 1125), (218, 1150),
                  (221, 1190), (80, 1190)]


def poly_mask(shape, polys):
    m = Image.new('L', (shape[1], shape[0]), 0)
    d = ImageDraw.Draw(m)
    for p in polys:
        d.polygon(p, fill=255)
    return np.asarray(m) > 0


def rings_of(mask, sigma=1.0, eps=0.7, min_area=10, up=4):
    """Mask (bool or soft 0..1) -> smooth sub-pixel rings: blur a little, upsample, contour."""
    m = mask.astype(np.float32)
    if sigma:
        m = ndimage.gaussian_filter(m, sigma)
    if not (m > 0.5).any():
        return []
    ys, xs = np.where(m > 0.05)
    y0, y1 = max(0, ys.min() - 3), min(m.shape[0], ys.max() + 4)
    x0, x1 = max(0, xs.min() - 3), min(m.shape[1], xs.max() + 4)
    sub = m[y0:y1, x0:x1]
    big = cv2.resize(sub, ((x1 - x0) * up, (y1 - y0) * up), interpolation=cv2.INTER_LINEAR)
    cs, hier = cv2.findContours((big > 0.5).astype(np.uint8), cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    out = []
    if hier is None:
        return out
    hier = hier[0]
    amin = min_area * up * up
    for i, c in enumerate(cs):
        if hier[i][3] != -1 or cv2.contourArea(c) < amin:
            continue
        group = [c]
        j = hier[i][2]
        while j != -1:
            if cv2.contourArea(cs[j]) >= amin / 2:
                group.append(cs[j])
            j = hier[j][0]
        rr = []
        for g in group:
            q = cv2.approxPolyDP(g, eps * up * 0.6, True)[:, 0].astype(np.float32)
            if len(q) >= 3:
                rr.append((q + 0.5) / up - 0.5 + np.array([x0, y0], np.float32) + 0.5 / up)
        if rr:
            out.append(rr)
    return out


def main():
    a = np.asarray(Image.open(SRC).convert('RGBA')).astype(np.float32)
    h, w = a.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    r, g, b, al = a[..., 0], a[..., 1], a[..., 2], a[..., 3]
    op = al > 128
    lum = 0.3 * r + 0.59 * g + 0.11 * b
    mx = a[..., :3].max(-1)
    sat = (mx - a[..., :3].min(-1)) / (mx + 1e-6)

    hair = (r > g * 1.6) & (r > b * 1.6) & (r > 70) & op & (yy < 540)
    lab, n = ndimage.label(hair)
    sizes = ndimage.sum(hair, lab, range(1, n + 1))
    hair = np.isin(lab, [i + 1 for i, s in enumerate(sizes) if s > 300])
    shirt = (g >= r - 12) & (g > b + 22) & op & (lum > 100)
    white = (lum > 195) & (sat < 0.16) & op & (yy > 980)
    cuff = np.where(xx < 165, 648 + (xx - 50) * 0.06, 662)          # the shorts' cuff bottom (src px)
    shorts = (r > 150) & (r - g > 35) & (sat > 0.25) & (yy > 515) & (yy < cuff) & op & ~hair
    skin = (r > 190) & (g > 130) & (r - b > 35) & (r - b < 110) & op & ~hair & ~shirt & ~shorts & (lum > 150)
    feat = poly_mask((h, w), [EYE_N, EYE_F, MOUTH, NOSE, BROW_F])
    far = poly_mask((h, w), [FAR_LEG]) & ~poly_mask((h, w), [NEAR_SHOE_OVER])
    hull = poly_mask((h, w), [FACE_HULL])
    lock = poly_mask((h, w), [FRONT_LOCK])

    # ---- partition: every opaque pixel belongs to one part --------------------------
    names = ['hair_back', 'leg_far', 'leg_near', 'arms', 'shorts', 'shirt', 'neck', 'face', 'hair_front']
    seed = np.full((h, w), -1, np.int32)
    seed[hair & ~(hull | lock)] = 0
    seed[hair & (hull | lock)] = 8
    seed[shirt & (yy < 690)] = 5
    seed[shorts] = 4
    sk = skin | white
    seed[sk & (yy >= 640) & far] = 1
    seed[sk & (yy >= 640) & ~far] = 2
    seed[skin & (yy >= 380) & (yy < 640) & ((xx < 95) | (xx > 230))] = 3
    seed[skin & (yy < 272) & ((hull & (yy < 236)) | (xx < 130))] = 7
    seed[skin & (yy >= 200) & (yy < 300) & (xx > 150) & (xx < 205) & (seed == -1)] = 6
    seed[feat] = 7
    idx = ndimage.distance_transform_edt(seed < 0, return_distances=False, return_indices=True)
    part = seed[idx[0], idx[1]]
    part[~op] = -1
    base_col = {'hair_back': (178, 10, 4), 'hair_front': (178, 10, 4), 'shirt': (187, 186, 137),
                'shorts': (216, 146, 140), 'neck': (244, 204, 180)}
    redhair = (r > 90) & (r > g * 1.6) & (r > b * 1.6)
    alpha = al / 255.0
    alpha_k = np.clip(alpha * 1.8, 0, 1)
    ink_soft = np.where(redhair, np.clip((38 - lum) / 16, 0, 1), np.clip((135 - lum) / 50, 0, 1)) * alpha_k
    data = {}
    for pi, name in enumerate(names):
        m = part == pi
        if not m.any():
            data[name] = ([], [])
            continue
        if name == 'face':
            m = ndimage.binary_fill_holes(m | (feat & op))
        # a part continues a little under the parts drawn after it (revealed when they move)
        reach = 26 if name == 'leg_far' else 8
        under = ndimage.binary_dilation(m, iterations=reach) & (part > pi) & op
        if name == 'leg_far':
            under &= (yy > 650) & (yy < 990)        # skin only: never a skin blob in the near shoe
        m_ext = m | under
        if name == 'leg_far':          # the far foot is drawn as a copy of the near one (lib/girl3.py)
            m = m & (yy < 1004)
            m_ext = m_ext & (yy < 1004)
        own = m & (seed == pi)
        col = base_col.get(name)
        if col is None:
            col = tuple(int(v) for v in np.median(a[own & skin][:, :3], axis=0)) if (own & skin).any() else (248, 208, 184)
        soft = ndimage.gaussian_filter(ndimage.binary_dilation(m_ext, iterations=1).astype(np.float32), 0.7)
        soft = np.where(ndimage.binary_erosion(op, iterations=2), soft, np.minimum(soft * 2, 1) * alpha)
        fills = [('base', col, rings_of(soft, 0, 0.4, 12))]
        L = lum
        base_l = 0.3 * col[0] + 0.59 * col[1] + 0.11 * col[2]
        notfeat = ~feat if name == 'face' else np.ones_like(m)
        if name.startswith('hair'):
            fills.append(('dk', (126, 6, 2), rings_of(m & hair & (L < 47), 1.2, 0.6, 12)))
            fills.append(('lt', (212, 102, 86), rings_of(m & hair & (L > 86), 0.8, 0.5, 6)))
            inkm = ndimage.gaussian_filter(ndimage.binary_dilation(m, iterations=2).astype(np.float32), 0.8) * ink_soft
        else:
            if name.startswith('leg'):
                fills.append(('white', (244, 238, 233), rings_of(m & white, 0.9, 0.5, 10)))
                fills.append(('whsh', (216, 205, 199), rings_of(m & (yy > 980) & (L > 185) & (L < 224) & (sat < 0.2),
                                                                1.1, 0.6, 10)))
                fills.append(('wline', (150, 136, 132), rings_of((m & (yy > 980) & (sat < 0.3)) * np.clip((200 - L) / 30, 0, 1),
                                                                 0.4, 0.3, 2)))
            if name in ('face', 'neck', 'arms', 'leg_far', 'leg_near'):
                fills.append(('sksh', (230, 172, 152), rings_of(m & skin & notfeat & (L < base_l - 14), 1.3, 0.7, 14)))
                fills.append(('blush', (238, 168, 156), rings_of(m & notfeat & (r - g > 62) & (r > 225) & (L > 150)
                                                                  & (yy < 260), 1.6, 0.8, 14)))
            if name == 'face':
                fills.append(('ear', (222, 148, 138), rings_of(m & (xx < 125) & (yy > 180) & (yy < 226) & (r - b > 60)
                                                               & (L < 200) & (L > 110), 1.0, 0.5, 8)))
            if name == 'shirt':
                fills.append(('sh', (160, 156, 116), rings_of(m & shirt & (L < 168), 1.3, 0.7, 14)))
            if name == 'shorts':
                fills.append(('sh', (198, 120, 114), rings_of(m & shorts & (L < 162), 1.3, 0.7, 14)))
                fills.append(('dk', (204, 96, 90), rings_of(m & shorts & (r - g > 105), 2.2, 0.6, 20)))
            inkm = ndimage.gaussian_filter((ndimage.binary_dilation(m, iterations=2) & notfeat).astype(np.float32), 0.8) * ink_soft
        fills.append(('ink', (40, 14, 10), rings_of(inkm, 0.45, 0.3, 2)))
        data[name] = (fills, [])
    # ---- the face features, traced as their own shapes (they animate) ----------------
    feats = {}
    for fname, poly in (('eye_n', EYE_N), ('eye_f', EYE_F)):
        reg = poly_mask((h, w), [poly]) & op & ~hair
        lid = reg & (lum < 175)
        eye_all = ndimage.binary_fill_holes(ndimage.binary_closing(reg & ((lum < 120) | ((lum > 175) & (sat < 0.14))), iterations=1))
        white_m = eye_all & ~(ndimage.binary_erosion(~((lum > 175) & (sat < 0.16)) | ~reg, iterations=0) & False)
        dark = reg * np.clip((80 - lum) / 35, 0, 1)
        iris = reg * np.clip((185 - lum) / 40, 0, 1) * (sat < 0.3)
        hi = (reg & ndimage.binary_erosion(eye_all, iterations=2)) * np.clip((lum - 225) / 20, 0, 1) *             ndimage.binary_dilation(lum < 150, iterations=2)
        feats[fname] = dict(white=rings_of(eye_all, 0.6, 0.35, 6), iris=rings_of(iris, 0.5, 0.3, 4),
                            ink=rings_of(dark, 0.4, 0.3, 2), hi=rings_of(hi, 0.4, 0.3, 1))
        iris_col = np.median(a[reg & (lum > 70) & (lum < 150)][:, :3], axis=0)
        print(fname, 'iris colour', iris_col)
    for fname, poly in (('mouth', MOUTH), ('nose', NOSE), ('brow_f', BROW_F)):
        reg = poly_mask((h, w), [poly])
        feats[fname] = dict(ink=rings_of((reg & ~hair) * np.clip((185 - lum) / 70, 0, 1), 0.4, 0.3, 2))
    # ---- pack -------------------------------------------------------------------------
    blob = dict(parts=names)
    rings_all, ring_meta = [], []      # meta: part, fill index, shape index
    lines_all, line_w, line_meta = [], [], []
    fill_meta = []
    for pi, name in enumerate(names):
        fills, lines = data[name]
        for fi, (tag, col, shapes) in enumerate(fills):
            fill_meta.append((pi, fi, col[0], col[1], col[2], hash(tag) % 1000))
            for si, rr in enumerate(shapes):
                for ring in rr:
                    rings_all.append(ring)
                    ring_meta.append((pi, fi, si))
        for (pts, wid) in lines:
            lines_all.append(pts)
            line_w.append(wid)
            line_meta.append(pi)
    fi_names = []
    for name in names:
        for tag, col, _ in data[name][0]:
            fi_names.append(tag)
    feat_rings, feat_meta = [], []
    for fname, d in feats.items():
        for kind, shapes in d.items():
            for si, rr in enumerate(shapes):
                for ring in rr:
                    feat_rings.append(ring)
                    feat_meta.append('%s|%s|%d' % (fname, kind, si))
    np.savez_compressed(
        OUT, parts=np.array(names), fill_tags=np.array(fi_names), fill_meta=np.array(fill_meta),
        ring_len=np.array([len(x) for x in rings_all]), ring_pts=np.concatenate(rings_all),
        ring_meta=np.array(ring_meta),
        line_len=np.array([len(x) for x in lines_all], int), line_pts=np.concatenate(lines_all) if lines_all else np.zeros((0, 2), np.float32),
        line_w=np.concatenate(line_w) if line_w else np.zeros(0, np.float32), line_meta=np.array(line_meta, int),
        feat_len=np.array([len(x) for x in feat_rings]), feat_pts=np.concatenate(feat_rings),
        feat_meta=np.array(feat_meta))
    print(OUT, len(rings_all), 'rings', len(lines_all), 'lines', len(feat_rings), 'feature rings')


if __name__ == '__main__':
    main()
