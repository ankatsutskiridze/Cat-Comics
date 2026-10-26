"""The girl, animatable (v2): her own head art from the master sheet + a vector 3D body.

Anka (2026-10-26): the images are references to CREATE the character; in videos she must be
alive (sit, stand, move, emotions), never a pasted still. So:
- HEAD: the head + long hair of the master sheet's front figure
  (characters/girl/images/cut/stand_front.png), with the eyes and mouth painted out; eyes,
  brows, mouth and extras are drawn in vector per emotion (blink, look, surprised, annoyed...).
  The head tilts and nods on a neck pivot.
- BODY: a 3D capsule skeleton in the sheet's pixel units (height 1185 = standing), seen from
  the front with a slight downward camera pitch, so a seated pose shows the thighs coming
  toward us. Tee, sleeves, shorts with cuffs, legs, socks, sneakers, hands: flat colours
  sampled off the sheet with its dark outline.

draw_girl(ctx, x, y, scale, pose, face) - x, y = screen point of the floor under her middle,
scale = screen px per sheet px.
"""
import math
import os

import cairo
import numpy as np
from PIL import Image, ImageDraw

from girl import _capsule_poly, _catmull, _ellipse, _group, _line, _path, _taper

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, 'characters', 'girl', 'images', 'cut', 'stand_front.png')


def rgb(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))


LINE = rgb('#3a2420')
SKIN = rgb('#f9d1b8')
SKIN_SH = rgb('#eab59c')
SHIRT = rgb('#bbbb87')
SHIRT_SH = rgb('#a19f6e')
SHORTS = rgb('#da918b')
SHORTS_SH = rgb('#be736d')
WHITE = rgb('#f8f5f1')
WHITE_SH = rgb('#d9d0ca')
IRIS = rgb('#2b2222')
IRIS_LO = rgb('#6a5c5c')
LASH = rgb('#1c1312')
MOUTH = rgb('#9a3a3a')
TONGUE = rgb('#e37a7a')
LW = 3.2                      # outline half-width in sheet px

# head art landmarks (sheet px, image coords: y down)
NECK = (186, 268)             # the head pivots here
EYES = [(152, 174, 35, 20, -16), (238, 150, 27, 22, -18)]   # cx, cy, rx, ry, degrees
MOUTH_AT = (208, 201)

FACES = {
    'neutral':   dict(lid=0.0, look=(0.6, 0.1), mouth='smile'),
    'look_down': dict(lid=0.25, look=(0.2, 0.9), mouth='flat'),
    'bored':     dict(lid=0.45, look=(0.0, 0.3), mouth='flat'),
    'annoyed':   dict(lid=0.5, look=(-0.6, 0.4), mouth='frown', brows='down'),
    'angry':     dict(lid=0.35, look=(-0.6, 0.3), mouth='frown', brows='angry', vein=True),
    'surprised': dict(lid=-0.25, look=(-0.6, 0.2), iris=0.62, mouth='o', lines=True),
    'sigh':      dict(closed=True, mouth='flat'),
    'happy':     dict(happy=True, mouth='open'),
    'deadpan':   dict(lid=0.42, look=(-0.7, 0.2), mouth='flat'),
}

_cache = {}


# ------------------------------------------------------------------ head art

def _head_piece():
    """RGBA head + long hair with the eyes and mouth painted out (sheet px)."""
    if 'head' in _cache:
        return _cache['head']
    im = Image.open(SRC).convert('RGBA')
    a = np.asarray(im).copy()
    r, g, b = (a[..., i].astype(int) for i in range(3))
    hair = (r > g * 1.7) & (r > b * 1.7) & (r > 90) & (a[..., 3] > 60)
    from scipy import ndimage
    hair_d = ndimage.binary_dilation(hair, iterations=3)
    keep = np.zeros(hair.shape, bool)
    keep[:272] = True
    dark = (a[..., :3].max(-1) < 110) & (a[..., 3] > 60)
    low = np.zeros(hair.shape, bool)
    low[272:525] = (hair | (dark & hair_d))[272:525]
    lab, n = ndimage.label(low)
    if n:
        sizes = ndimage.sum(low, lab, range(1, n + 1))
        low = np.isin(lab, [i + 1 for i, z in enumerate(sizes) if z > 400])
    keep |= low
    a[~keep, 3] = 0
    # paint out the eyes and the mouth with skin (never over hair)
    skin = tuple(int(v) for v in np.median(a[190:200, 185:205, :3].reshape(-1, 3), axis=0)) + (255,)
    lid = Image.new('L', im.size, 0)
    d = ImageDraw.Draw(lid)
    for (cx, cy, rx, ry, deg) in EYES:
        ang = math.radians(deg)
        pts = [(cx + (rx + 7) * math.cos(t) * math.cos(ang) - (ry + 8) * math.sin(t) * math.sin(ang),
                cy + (rx + 7) * math.cos(t) * math.sin(ang) + (ry + 8) * math.sin(t) * math.cos(ang))
               for t in np.linspace(0, 2 * math.pi, 48)]
        d.polygon(pts, fill=255)
    mx, my = MOUTH_AT
    d.ellipse((mx - 20, my - 9, mx + 20, my + 9), fill=255)
    m = (np.asarray(lid) > 0) & ~hair
    a[m] = skin
    _cache['head'] = Image.fromarray(a, 'RGBA')
    _cache['skin'] = skin
    return _cache['head']


def _pil_to_cairo(im):
    a = np.asarray(im).astype(np.float32) / 255
    al = a[..., 3:4]
    bgra = np.dstack([a[..., 2:3] * al, a[..., 1:2] * al, a[..., 0:1] * al, al])
    data = np.ascontiguousarray((bgra * 255).astype(np.uint8))
    surf = cairo.ImageSurface.create_for_data(memoryview(data), cairo.FORMAT_ARGB32, im.width, im.height)
    return surf, data


def _head_surface():
    if 'hsurf' not in _cache:
        _cache['hsurf'] = _pil_to_cairo(_head_piece())
    return _cache['hsurf'][0]


# ------------------------------------------------------------------ face features (head px)

def _eye(ctx, cx, cy, rx, ry, deg, f, side):
    ctx.save()
    ctx.translate(cx, cy)
    ctx.rotate(math.radians(deg))
    if f.get('closed'):
        _taper(ctx, [(-rx * 0.95, 2), (0, ry * 0.45), (rx * 0.95, 0)], 3.0, 6.0, LASH)
        _taper(ctx, [(rx * 0.85, 1), (rx * 1.12, -6)], 5.0, 1.0, LASH)
        ctx.restore()
        return
    if f.get('happy'):
        _taper(ctx, [(-rx * 0.95, ry * 0.4), (0, -ry * 0.35), (rx * 0.95, ry * 0.35)], 3.0, 6.0, LASH)
        ctx.restore()
        return
    k = 1.12 if f.get('lid', 0) < 0 else 1.0
    erx, ery = rx * k, ry * k
    # almond eye: fuller top
    top = [(-erx, 3), (-erx * 0.6, -ery * 0.9), (0, -ery * 1.05), (erx * 0.6, -ery * 0.95), (erx, -ery * 0.2)]
    bot = [(erx, -ery * 0.2), (erx * 0.7, ery * 0.7), (0, ery * 1.0), (-erx * 0.6, ery * 0.75), (-erx, 3)]
    shape = _catmull(top + bot[1:-1], 6, closed=True)
    lid = f.get('lid', 0.0)
    ytop = -ery * 1.05 + max(0.0, lid) * ery * 2.05
    ctx.save()
    _path(ctx, shape)
    ctx.clip()
    ctx.rectangle(-erx * 2, ytop, erx * 4, ery * 4)
    ctx.clip()
    ctx.set_source_rgb(1, 1, 1)
    ctx.paint()
    lx, ly = f.get('look', (0.6, 0.1))
    ir = ery * f.get('iris', 0.95)
    ix, iy = lx * erx * 0.38, ly * ery * 0.25 + ery * 0.05
    _ellipse(ctx, ix, iy, ir * 0.9, ir)
    ctx.set_source_rgb(*IRIS)
    ctx.fill()
    _ellipse(ctx, ix, iy + ir * 0.5, ir * 0.62, ir * 0.38)
    ctx.set_source_rgb(*IRIS_LO)
    ctx.fill()
    if ir > ery * 0.7:
        _ellipse(ctx, ix + ir * 0.35, iy - ir * 0.42, ir * 0.24, ir * 0.24)
        ctx.set_source_rgb(1, 1, 1)
        ctx.fill()
        _ellipse(ctx, ix - ir * 0.3, iy + ir * 0.4, ir * 0.1, ir * 0.1)
        ctx.fill()
    ctx.restore()
    # thick upper lash along the lid line, outer flick toward the temple (screen-left eye
    # = her right: temple on the left)
    out = -1 if side < 0 else 1
    if lid > 0.02:
        _taper(ctx, [(-erx * 1.02, ytop + 6), (0, ytop), (erx * 1.0, ytop + 3)], 4.5, 7.0, LASH)
    else:
        _taper(ctx, top, 4.5, 7.5, LASH)
    tx = -erx if out < 0 else erx
    ty = 2 if out < 0 else -ery * 0.2
    _taper(ctx, [(tx, ty), (tx + out * 9, ty - 7), (tx + out * 13, ty - 7)], 5.0, 1.0, LASH)
    _line(ctx, [(-erx * 0.5, ery * 0.82), (erx * 0.3, ery * 0.98), (erx * 0.75, ery * 0.6)], 1.6, LINE, 0.8)
    ctx.restore()


def _brows(ctx, f):
    kind = f.get('brows')
    if not kind:
        return
    for (cx, cy, rx, ry, deg) in EYES:
        ctx.save()
        ctx.translate(cx, cy - ry - 16)
        ctx.rotate(math.radians(deg))
        if kind == 'angry':
            pts = [(-rx * 0.8, -8), (rx * 0.8, 6)] if cx > 190 else [(-rx * 0.8, 6), (rx * 0.8, -8)]
        else:
            pts = [(-rx * 0.8, 2), (rx * 0.8, 2)]
        _taper(ctx, pts, 5.0, 3.0, rgb('#6b261d'))
        ctx.restore()


def _mouth(ctx, f):
    mx, my = MOUTH_AT
    m = f.get('mouth', 'smile')
    ctx.save()
    ctx.translate(mx, my)
    ctx.rotate(math.radians(-10))
    if m == 'smile':
        _taper(ctx, [(-13, -2), (0, 3), (13, -3)], 1.6, 2.6, LINE)
    elif m == 'flat':
        _line(ctx, [(-8, 0), (8, -1)], 2.2, LINE, smooth=False)
    elif m == 'frown':
        _line(ctx, [(-10, 3), (0, -1), (10, 2)], 2.2, LINE)
    elif m in ('o', 'open'):
        if m == 'o':
            _ellipse(ctx, 0, 2, 6, 8)
        else:
            _path(ctx, _catmull([(-12, -2), (12, -3), (8, 8), (0, 11), (-8, 8)], 5, closed=True))
        ctx.set_source_rgb(*MOUTH)
        ctx.fill_preserve()
        ctx.set_source_rgb(*LINE)
        ctx.set_line_width(1.8)
        ctx.stroke()
    ctx.restore()


def _extras(ctx, f, t=0.0):
    if f.get('vein'):
        cx, cy = 255, 75
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.set_line_width(5)
        ctx.set_source_rgb(0.86, 0.19, 0.16)
        for k in range(4):
            a = math.pi / 4 + k * math.pi / 2
            ctx.move_to(cx + math.cos(a) * 4, cy + math.sin(a) * 4)
            ctx.line_to(cx + math.cos(a) * 15, cy + math.sin(a) * 15)
        ctx.stroke()
    if f.get('lines'):
        ctx.set_line_cap(cairo.LINE_CAP_ROUND)
        ctx.set_line_width(5)
        ctx.set_source_rgb(*LINE)
        for a in (-120, -90, -60):
            r = math.radians(a)
            ctx.move_to(186 + math.cos(r) * 175, 130 + math.sin(r) * 150)
            ctx.line_to(186 + math.cos(r) * 205, 130 + math.sin(r) * 178)
        ctx.stroke()


def draw_head(ctx, f, tilt=0.0, nod=0.0):
    """Head art in sheet px (image coords), pivoting at NECK."""
    ctx.save()
    ctx.translate(*NECK)
    ctx.rotate(math.radians(tilt))
    ctx.translate(0, nod)
    ctx.translate(-NECK[0], -NECK[1])
    ctx.set_source_surface(_head_surface(), 0, 0)
    ctx.paint()
    # soft blush under the eyes is already in the art; draw features
    for i, e in enumerate(EYES):
        _eye(ctx, *e, f, -1 if i == 0 else 1)
    _brows(ctx, f)
    _mouth(ctx, f)
    _extras(ctx, f)
    ctx.restore()


# ------------------------------------------------------------------ body (3D, sheet px, y up)

PITCH = math.radians(22)        # camera looks down a little


def pose_stand():
    return dict(sit=False, hands='down')


def pose_sit(hands='knees'):
    return dict(sit=True, hands=hands)


def _skeleton(p):
    """Joint positions (x, Y up, z toward camera) for a pose."""
    sit = p.get('sit')
    dy = -270 if sit else 0           # the whole upper body comes down onto the seat
    dz = -20 if sit else 0
    J = {}
    J['neck'] = (186, 905 + dy, 0 + dz)
    J['sh_l'], J['sh_r'] = (104, 880 + dy, dz), (262, 880 + dy, dz)
    J['chest'] = (182, 800 + dy, 4 + dz)
    J['waist'] = (180, 650 + dy, 2 + dz)
    J['hip_l'], J['hip_r'] = (140, 590 + dy, dz), (218, 590 + dy, dz)
    if sit:
        J['knee_l'], J['knee_r'] = (128, 330, 225), (222, 330, 225)
        J['ank_l'], J['ank_r'] = (124, 80, 240), (226, 80, 240)
    else:
        J['knee_l'], J['knee_r'] = (132, 355, 4), (190, 355, 4)
        J['ank_l'], J['ank_r'] = (128, 95, 0), (172, 95, 0)
    # arms
    for s, side in (('l', -1), ('r', 1)):
        S = np.array(J['sh_' + s], float)
        Wa = _wrist(p.get('hands', 'down'), J, s, side, S, sit, dy, dz)
        if p.get('hands2'):
            Wb = _wrist(p['hands2'], J, s, side, S, sit, dy, dz)
            k = p.get('mix', 0.0)
            Wp = Wa * (1 - k) + Wb * k
        else:
            Wp = Wa
        E = _ik(S, Wp, 150, 140, np.array([side * 1.0, 0, -0.4]))
        J['el_' + s], J['wr_' + s] = tuple(E), tuple(Wp)
    return J


def _wrist(hands, J, s, side, S, sit, dy, dz):
    if True:
        if hands == 'knees' and sit:
            Wp = np.array(J['knee_' + s], float) + np.array([10 * -side, 40, -10])
        elif hands == 'face':
            Wp = np.array([186 + side * 44, 1075 + dy, 115 + dz], float)
        elif hands == 'lap' and sit:
            Wp = np.array([180 + side * 30, 345, 130], float)
        else:
            Wp = S + np.array([side * 18, -275, 8])
        return Wp


def _ik(a, b, l1, l2, bend):
    d = b - a
    dist = max(1e-6, min(np.linalg.norm(d), l1 + l2 - 1e-3))
    u = d / (np.linalg.norm(d) + 1e-9)
    along = (l1 * l1 - l2 * l2 + dist * dist) / (2 * dist)
    h = math.sqrt(max(l1 * l1 - along * along, 0.0))
    perp = bend - np.dot(bend, u) * u
    perp /= (np.linalg.norm(perp) + 1e-9)
    return a + u * along + perp * h


class _Cam:
    def __init__(self, x, y, s):
        self.x, self.y, self.s = x, y, s
        self.cp, self.sp = math.cos(PITCH), math.sin(PITCH)

    def P(self, p):
        X, Y, Z = p
        return (self.x + (X - 180) * self.s, self.y - (Y * self.cp - Z * self.sp) * self.s)

    def depth(self, p):
        X, Y, Z = p
        return Z * self.cp + Y * self.sp


def _cap(c, a, ra, b, rb):
    return _capsule_poly(c.P(a), ra * c.s, c.P(b), rb * c.s, 10)


def _shoe(ctx, c, ank, lw):
    """Chunky white sneaker seen from the front-ish: thick sole, toe cap, tongue, laces."""
    x, Y, z = ank
    out = 1 if x > 180 else -1
    cx, cy = c.P((x + out * 6, 0, z + 34))
    s = c.s
    up = _catmull([(-1.0, -0.15), (-1.05, -0.5), (-0.75, -0.9), (-0.3, -1.05), (0.3, -1.05), (0.75, -0.9),
                   (1.05, -0.5), (1.0, -0.15)], 6)
    w = 40 * s
    upper = [(cx + u * w, cy + v * 70 * s) for u, v in up] + [(cx + w, cy - 6 * s), (cx - w, cy - 6 * s)]
    sole = _catmull([(cx - 1.12 * w, cy - 22 * s), (cx + 1.12 * w, cy - 22 * s), (cx + 1.12 * w, cy - 4 * s),
                     (cx + 0.9 * w, cy + 4 * s), (cx - 0.9 * w, cy + 4 * s), (cx - 1.12 * w, cy - 4 * s)], 3, closed=True)
    _group(ctx, [upper], WHITE, lw)
    _group(ctx, [sole], WHITE, lw)
    _line(ctx, [(cx - 1.05 * w, cy - 12 * s), (cx + 1.05 * w, cy - 12 * s)], lw * 0.5, WHITE_SH, 1.0, False)
    _line(ctx, [(cx - 0.8 * w, cy - 30 * s), (cx, cy - 26 * s), (cx + 0.8 * w, cy - 30 * s)], lw * 0.55, LINE, 0.6)
    tw = 0.34 * w
    _group(ctx, [[(cx - tw, cy - 72 * s), (cx + tw, cy - 72 * s), (cx + tw * 1.1, cy - 38 * s),
                  (cx - tw * 1.1, cy - 38 * s)]], WHITE, lw * 0.7)
    for k in range(3):
        yy = cy - (64 - 9 * k) * s
        _line(ctx, [(cx - tw * 1.2, yy), (cx + tw * 1.2, yy - 4 * s)], lw * 0.6, LINE, 0.85, False)
        _line(ctx, [(cx - tw * 1.2, yy - 4 * s), (cx + tw * 1.2, yy)], lw * 0.6, LINE, 0.85, False)


def _hand(ctx, c, wr, el, lw):
    a, b = c.P(el), c.P(wr)
    ang = math.atan2(b[1] - a[1], b[0] - a[0])
    hx, hy = b[0] + math.cos(ang) * 16 * c.s, b[1] + math.sin(ang) * 16 * c.s
    from girl import _ellipse_pts
    palm = _ellipse_pts(hx, hy, 24 * c.s, 15 * c.s, 24, ang)
    _group(ctx, [palm], SKIN, lw)
    for f in (-0.4, 0.05, 0.45):
        p0 = (hx + math.cos(ang) * 6 * c.s - math.sin(ang) * f * 14 * c.s,
              hy + math.sin(ang) * 6 * c.s + math.cos(ang) * f * 14 * c.s)
        p1 = (p0[0] + math.cos(ang) * 14 * c.s, p0[1] + math.sin(ang) * 14 * c.s)
        _line(ctx, [p0, p1], lw * 0.45, LINE, 0.6, False)


def draw_girl(ctx, x, y, scale, pose=None, face='neutral', tilt=0.0, nod=0.0, breathe=0.0):
    pose = pose or pose_stand()
    f = FACES[face] if isinstance(face, str) else face
    c = _Cam(x, y, scale)
    J = _skeleton(pose)
    lw = LW * scale
    items = []

    # legs: thigh (skin), shin, sock, shoe
    for s in ('l', 'r'):
        H, K, A = J['hip_' + s], J['knee_' + s], J['ank_' + s]

        def leg(ctx, H=H, K=K, A=A):
            sock_top = tuple(np.array(A) + (np.array(K) - np.array(A)) * 0.2)
            calf = tuple(np.array(K) + (np.array(A) - np.array(K)) * 0.33)
            _group(ctx, [_cap(c, H, 40, K, 24), _cap(c, K, 24, calf, 26), _cap(c, calf, 26, A, 16)], SKIN, lw)
            kp = c.P(K)
            _line(ctx, [(kp[0] - 12 * scale, kp[1] + 6 * scale), (kp[0], kp[1] + 12 * scale),
                        (kp[0] + 12 * scale, kp[1] + 6 * scale)], lw * 0.6, SKIN_SH, 1.0)
            _group(ctx, [_cap(c, sock_top, 20, A, 19)], WHITE, lw)
            st = c.P(sock_top)
            for k in range(2):
                yy = st[1] + (6 + 7 * k) * scale
                _line(ctx, [(st[0] - 17 * scale, yy), (st[0] + 17 * scale, yy)], lw * 0.45, WHITE_SH, 1.0, False)
            _shoe(ctx, c, A, lw)
        items.append((c.depth(K) - 60, leg))

    # shorts: a waistband block + one tapered tube per leg ending in a rolled cuff
    def shorts(ctx):
        sit = pose.get('sit')
        hl, hr = np.array(J['hip_l'], float), np.array(J['hip_r'], float)
        mid = (hl + hr) / 2
        top_l, top_r = hl + [-46, 62, 0], hr + [46, 62, 0]
        shapes = [[c.P(tuple(top_l)), c.P(tuple(top_r)), c.P(tuple(hr + [48, -8, 0])),
                   c.P(tuple(mid + [0, -38, 6])), c.P(tuple(hl + [-48, -8, 0]))]]
        cuffs = []
        for s_, H_, out in (('l', hl, -1), ('r', hr, 1)):
            K = np.array(J['knee_' + s_], float)
            d = (K - H_) / (np.linalg.norm(K - H_) + 1e-9)
            end = H_ + (K - H_) * (0.40 if sit else 0.27)
            side = np.array([1.0, 0, 0])
            outer0, inner0 = H_ + side * 48 * out + [0, 10, 0], mid + [0, -30, 4]
            outer1, inner1 = end + side * 46 * out, end - side * 40 * out
            shapes.append([c.P(tuple(outer0)), c.P(tuple(outer1)), c.P(tuple(inner1)), c.P(tuple(inner0))])
            cuffs.append((end, d, out))
        _group(ctx, shapes, SHORTS, lw)
        for end, d, out in cuffs:
            side = np.array([1.0, 0, 0])
            a0, a1 = end - d * 18, end + d * 2
            cuff = [c.P(tuple(a0 + side * 48 * out)), c.P(tuple(a1 + side * 48 * out)),
                    c.P(tuple(a1 - side * 42 * out)), c.P(tuple(a0 - side * 42 * out))]
            _group(ctx, [cuff], SHORTS, lw * 0.9)
        top = c.P(tuple(mid + [0, 60, 30]))
        bot = c.P(tuple(mid + [2, -20, 30]))
        _line(ctx, [top, bot], lw * 0.6, SHORTS_SH, 1.0)
        for H_, out in ((hl, -1), (hr, 1)):
            a0 = c.P(tuple(H_ + [out * 8, 58, 30]))
            a1 = c.P(tuple(H_ + [out * 30, 24, 30]))
            a2 = c.P(tuple(H_ + [out * 46, 18, 30]))
            _line(ctx, [a0, a1, a2], lw * 0.6, LINE, 0.8)
    items.append((c.depth(J['hip_l']) + (40 if pose.get('sit') else 10), shorts))

    # torso (tee)
    def torso(ctx):
        nk = c.P(J['neck'])
        _group(ctx, [[(nk[0] - 22 * scale, nk[1] - 75 * scale), (nk[0] + 22 * scale, nk[1] - 75 * scale),
                      (nk[0] + 25 * scale, nk[1] + 18 * scale), (nk[0] - 25 * scale, nk[1] + 18 * scale)]], SKIN, lw)
        b = 1 + 0.015 * breathe
        L, R = J['sh_l'], J['sh_r']
        W_ = J['waist']
        pts = [c.P((L[0] + 6, L[1] + 8, L[2])), c.P((J['neck'][0] - 26, J['neck'][1] - 18, 0)),
               c.P((J['neck'][0] + 26, J['neck'][1] - 18, 0)), c.P((R[0] - 6, R[1] + 8, R[2])),
               c.P((R[0] + 6 * b, R[1] - 60, R[2])), c.P((W_[0] + 76 * b, W_[1] + 40, W_[2])),
               c.P((W_[0] + 80 * b, W_[1] - 10, W_[2])), c.P((W_[0] - 80 * b, W_[1] - 10, W_[2])),
               c.P((W_[0] - 76 * b, W_[1] + 40, W_[2])), c.P((L[0] - 6 * b, L[1] - 60, L[2]))]
        _group(ctx, [_catmull(pts, 4, closed=True)], SHIRT, lw)
        # collar
        _ellipse(ctx, nk[0], nk[1] + 16 * scale, 24 * scale, 9 * scale)
        ctx.set_source_rgb(*SKIN)
        ctx.fill()
        for k, (ww, hh) in enumerate([(24, 9), (31, 14)]):
            ctx.save()
            ctx.translate(nk[0], nk[1] + 16 * scale)
            ctx.scale(ww * scale, hh * scale)
            ctx.arc(0, 0, 1, 0, math.pi)
            ctx.restore()
            ctx.set_source_rgb(*LINE)
            ctx.set_line_width(lw * (1.0 if k else 0.7))
            ctx.stroke()
        # hem shade
        _line(ctx, [c.P((W_[0] - 70, W_[1] + 10, W_[2] + 1)), c.P((W_[0] + 70, W_[1] + 10, W_[2] + 1))],
              lw * 0.5, SHIRT_SH, 0.9, False)
    items.append((c.depth(J['chest']), torso))

    # arms (+ sleeves)
    for s in ('l', 'r'):
        S, E, Wr = J['sh_' + s], J['el_' + s], J['wr_' + s]

        def arm(ctx, S=S, E=E, Wr=Wr):
            _group(ctx, [_cap(c, S, 18, E, 15), _cap(c, E, 15, Wr, 12)], SKIN, lw)
            _hand(ctx, c, Wr, E, lw)
            d = np.array(E) - np.array(S)
            d = d / (np.linalg.norm(d) + 1e-9)
            p0, p1 = c.P(tuple(np.array(S) - d * 6)), c.P(tuple(np.array(S) + d * 92))
            ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0]) + math.pi / 2
            ca, sa = math.cos(ang), math.sin(ang)
            w0, w1 = 30 * scale, 36 * scale
            sleeve = [(p0[0] - ca * w0, p0[1] - sa * w0), (p0[0] + ca * w0, p0[1] + sa * w0),
                      (p1[0] + ca * w1, p1[1] + sa * w1), (p1[0] - ca * w1, p1[1] - sa * w1)]
            cap = [(p0[0] + ca * w0 * math.cos(t) - (p1[0] - p0[0]) * 0.28 * math.sin(t),
                    p0[1] + sa * w0 * math.cos(t) - (p1[1] - p0[1]) * 0.28 * math.sin(t))
                   for t in np.linspace(0, math.pi, 9)]
            _group(ctx, [sleeve, cap], SHIRT, lw)
            q = (p0[0] + (p1[0] - p0[0]) * 0.86, p0[1] + (p1[1] - p0[1]) * 0.86)
            _line(ctx, [(q[0] - ca * w1 * 0.95, q[1] - sa * w1 * 0.95), (q[0] + ca * w1 * 0.95, q[1] + sa * w1 * 0.95)],
                  lw * 0.6, LINE, 1, False)
        items.append((c.depth(Wr) + 30, arm))

    # head (with the long hair, over the tee)
    def head(ctx):
        ctx.save()
        nk = c.P(J['neck'])
        ctx.translate(nk[0], nk[1])
        ctx.scale(scale, scale)
        ctx.translate(-NECK[0], -(NECK[1] + 40))
        draw_head(ctx, f, tilt, nod)
        ctx.restore()
    items.append((c.depth(J['chest']) + 20, head))

    for dep, fn in sorted(items, key=lambda it: it[0]):
        fn(ctx)
