"""Vector model of the girl's head and hair, measured off the master sheet
(characters/rig/girl_src.png, the big standing figure).

Built once into characters/rig/girl3_head.npz:
- FILLS: smooth flat-colour shapes (hair base, hair shadow, hair shine, skin, skin shadow,
  inner ear), each a ring set (outer + holes) in source px, tagged with a layer:
  'back' (hair behind the face), 'face' (skin, ear, neck), 'front' (the fringe and the locks
  that fall in front of the face and neck);
- LINES: the line art as centre-line strokes with a width per point (the sheet's ink lines,
  thinned to their skeleton), tagged with a layer the same way.
The face's eyes, brows, nose and mouth are left out: lib/girl3.py draws them procedurally.

Rebuild: python lib/girl3_trace.py
"""
import os

import cv2
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'characters', 'rig', 'girl_src.png')
CACHE = os.path.join(ROOT, 'characters', 'rig', 'girl3_head.npz')
NECK_CUT = 270                  # the procedural body (collar) starts here

# left out of the model (source px): eyes with lashes, brows, nose, mouth
FACE_HOLES = [
    [(114, 181), (122, 167), (142, 157), (165, 151), (192, 153), (194, 167), (189, 188), (174, 197), (146, 197),
     (128, 188)],
    [(210, 153), (220, 140), (240, 131), (259, 125), (268, 131), (264, 151), (258, 170), (240, 174), (220, 171)],
    [(204, 165), (223, 165), (223, 186), (204, 186)],
    [(188, 194), (228, 190), (228, 212), (188, 212)],
    [(148, 120), (178, 118), (178, 132), (148, 132)],                 # left brow (under the fringe)
    [(214, 118), (262, 112), (262, 130), (214, 134)],                 # right brow
]
# the face's hull: hair inside it is the fringe (drawn over the eyes)
FACE_HULL = [(118, 92), (175, 70), (250, 88), (272, 140), (268, 190), (240, 225), (190, 236), (160, 232),
             (122, 214), (112, 170)]
# the lock that falls over the neck / chest (in front)
FRONT_LOCK = [(118, 200), (160, 222), (178, 262), (186, 330), (178, 455), (150, 460), (128, 340), (110, 240)]

C_HAIR = (178, 8, 2)
C_HAIR_DK = (122, 4, 1)
C_HAIR_LT = (206, 96, 80)
C_SKIN = (248, 208, 183)
C_SKIN_SH = (228, 170, 150)
C_EAR = (222, 150, 140)


def _thin(mask):
    """Zhang-Suen thinning (numpy)."""
    img = mask.astype(np.uint8).copy()
    changed = True
    while changed:
        changed = False
        for step in (0, 1):
            P = np.pad(img, 1)
            p2, p3, p4 = P[:-2, 1:-1], P[:-2, 2:], P[1:-1, 2:]
            p5, p6, p7 = P[2:, 2:], P[2:, 1:-1], P[2:, :-2]
            p8, p9 = P[1:-1, :-2], P[:-2, :-2]
            nb = [p2, p3, p4, p5, p6, p7, p8, p9]
            B = sum(n.astype(int) for n in nb)
            seq = nb + [p2]
            A = sum(((seq[i] == 0) & (seq[i + 1] == 1)).astype(int) for i in range(8))
            if step == 0:
                c = (p2 * p4 * p6 == 0) & (p4 * p6 * p8 == 0)
            else:
                c = (p2 * p4 * p8 == 0) & (p2 * p6 * p8 == 0)
            rm = (img == 1) & (B >= 2) & (B <= 6) & (A == 1) & c
            if rm.any():
                img[rm] = 0
                changed = True
    return img.astype(bool)


def _chains(skel):
    """Skeleton pixels -> list of polylines (y, x) walking 8-connected paths."""
    sk = skel.copy()
    h, w = sk.shape
    nb = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]

    def neighbours(y, x):
        return [(y + dy, x + dx) for dy, dx in nb if 0 <= y + dy < h and 0 <= x + dx < w and sk[y + dy, x + dx]]
    deg = ndimage.convolve(sk.astype(int), np.ones((3, 3), int), mode='constant') - 1
    deg[~sk] = 0
    out = []
    starts = list(zip(*np.where(sk & (deg == 1)))) + list(zip(*np.where(sk)))
    for y, x in starts:
        if not sk[y, x]:
            continue
        path = [(y, x)]
        sk[y, x] = False
        cy, cx = y, x
        while True:
            n = neighbours(cy, cx)
            if not n:
                break
            n.sort(key=lambda p: abs(p[0] - cy) + abs(p[1] - cx))
            cy, cx = n[0]
            sk[cy, cx] = False
            path.append((cy, cx))
        if len(path) >= 4:
            out.append(np.array(path, np.float32))
    return out


def _rings(mask, eps=0.7):
    mk = mask.astype(np.uint8)
    cs, hier = cv2.findContours(mk, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    shapes = []
    if hier is None:
        return shapes
    hier = hier[0]
    for i, c in enumerate(cs):
        if hier[i][3] != -1 or cv2.contourArea(c) < 6:
            continue
        group = [c]
        j = hier[i][2]
        while j != -1:
            if cv2.contourArea(cs[j]) >= 4:
                group.append(cs[j])
            j = hier[j][0]
        rings = [cv2.approxPolyDP(g, eps, True)[:, 0].astype(np.float32) + 0.5 for g in group]
        shapes.append([r for r in rings if len(r) >= 3])
    return shapes


def _smooth_mask(m, sigma=1.0):
    return ndimage.gaussian_filter(m.astype(np.float32), sigma) > 0.5


def _poly_mask(shape, polys):
    m = Image.new('L', (shape[1], shape[0]), 0)
    d = ImageDraw.Draw(m)
    for p in polys:
        d.polygon(p, fill=255)
    return np.asarray(m) > 0


def build():
    a = np.asarray(Image.open(SRC).convert('RGBA')).astype(int)
    h, w = a.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    op = a[..., 3] > 128
    lum = 0.3 * r + 0.59 * g + 0.11 * b
    hair = (r > g * 1.6) & (r > b * 1.6) & (r > 70) & op
    lab, n = ndimage.label(hair)
    sizes = ndimage.sum(hair, lab, range(1, n + 1))
    hair = np.isin(lab, [i + 1 for i, s in enumerate(sizes) if s > 300])
    ink = (lum < 62) & op & ~(hair & (lum > 40))
    holes = _poly_mask((h, w), FACE_HOLES)
    hull = _poly_mask((h, w), [FACE_HULL])
    front_lock = _poly_mask((h, w), [FRONT_LOCK])
    head_zone = (yy < NECK_CUT) & op
    # the hair silhouette (with its ink rim)
    hair_full = ndimage.binary_closing(hair | (ink & ndimage.binary_dilation(hair, iterations=3) & ~head_zone)
                                       | (ink & ndimage.binary_dilation(hair, iterations=2)), iterations=2)
    hair_full = ndimage.binary_fill_holes(hair_full) & ~(head_zone & ~hair & ~ink)
    hair_full &= ~(holes & ~hair)
    skin = head_zone & ~hair_full & op
    skin = _smooth_mask(skin | (holes & head_zone & ~hair), 0.8)
    front = hair_full & (hull | front_lock)
    fills = []                      # (layer, colour, rings)

    def add(layer, col, mask, eps=0.7, sigma=1.0):
        for rings in _rings(_smooth_mask(mask, sigma), eps):
            fills.append((layer, col, rings))
    back = hair_full & ~front
    add('back', C_HAIR, back)
    add('back', C_HAIR_DK, back & (lum < 47) & ~ink, sigma=1.4)
    add('back', C_HAIR_LT, back & (lum > 88), sigma=0.9)
    add('face', C_SKIN, skin)
    add('face', C_SKIN_SH, skin & (lum < 215) & (lum > 120) & ~holes, sigma=1.3)
    add('face', C_EAR, skin & (xx < 125) & (yy > 180) & (yy < 225) & (r - b > 60) & (lum < 200), sigma=1.0)
    add('front', C_HAIR, front)
    add('front', C_HAIR_DK, front & (lum < 47) & ~ink, sigma=1.4)
    add('front', C_HAIR_LT, front & (lum > 88), sigma=0.9)
    # line art: ink pixels (not the painted-out face), thinned to centre lines
    line = ink & (hair_full | head_zone) & ~holes
    line |= ndimage.binary_dilation(hair_full, iterations=1) & ~hair_full & op & (lum < 120)   # rim
    sk = _thin(line)
    dist = ndimage.distance_transform_edt(line | ndimage.binary_dilation(sk, iterations=1))
    lines = []
    for ch in _chains(sk):
        pts = cv2.approxPolyDP(ch[:, ::-1].reshape(-1, 1, 2).astype(np.float32), 0.6, False)[:, 0]
        if len(pts) < 2:
            continue
        wid = np.array([max(0.8, 2 * dist[int(p[1]), int(p[0])] - 0.4) for p in pts], np.float32)
        mid = pts[len(pts) // 2]
        lay = 'front' if front[int(mid[1]), int(mid[0])] else ('face' if skin[int(mid[1]), int(mid[0])] or
                                                               (int(mid[1]) < NECK_CUT and not hair_full[int(mid[1]), int(mid[0])]) else 'back')
        lines.append((lay, pts + 0.5, wid))
    # pack
    np.savez_compressed(
        CACHE,
        fill_layer=np.array([f[0] for f in fills]), fill_col=np.array([f[1] for f in fills], np.float32) / 255,
        fill_nr=np.array([len(f[2]) for f in fills]),
        ring_len=np.array([len(rg) for f in fills for rg in f[2]]),
        ring_pts=np.concatenate([rg for f in fills for rg in f[2]]),
        line_layer=np.array([l[0] for l in lines]), line_len=np.array([len(l[1]) for l in lines]),
        line_pts=np.concatenate([l[1] for l in lines]), line_w=np.concatenate([l[2] for l in lines]))
    return load()


def load():
    """-> dict(fills=[(layer, rgb, [rings])], lines=[(layer, pts (N,2), widths (N,))])"""
    if not os.path.exists(CACHE):
        return build()
    z = np.load(CACHE)
    rl, rp = z['ring_len'], z['ring_pts']
    fills, k, i = [], 0, 0
    for lay, col, nr in zip(z['fill_layer'], z['fill_col'], z['fill_nr']):
        rings = []
        for _ in range(nr):
            rings.append(rp[i:i + rl[k]])
            i += rl[k]
            k += 1
        fills.append((str(lay), tuple(col), rings))
    lines, i = [], 0
    for lay, L in zip(z['line_layer'], z['line_len']):
        lines.append((str(lay), z['line_pts'][i:i + L], z['line_w'][i:i + L]))
        i += L
    return dict(fills=fills, lines=lines)


if __name__ == '__main__':
    m = build()
    print(len(m['fills']), 'fills', len(m['lines']), 'lines')
