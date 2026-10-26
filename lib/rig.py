"""Mesh rig: brings a single character drawing to life (Live2D-style).

The drawing itself is the character. A triangle mesh is laid over it, every vertex is bound
to bones with smooth weights, and a pose (bone rotations / scales / offsets) bends the mesh;
the drawing is resampled through the bent mesh with one cv2.remap, so there are no seams.
Faces change by swapping the TEXTURE (same geometry): blinks, mouths and moods are painted
into copies of the drawing, so the warp carries them along with the head.

    rig = Rig(rgba, bones, weight_maps, step=8)
    img, (x0, y0) = rig.render(pose, scale, anchor_screen, anchor_src, texture='base')

Bones are given in source px: name -> (parent, pivot_xy). A pose maps name ->
dict(rot=deg, sx=1, sy=1, dx=0, dy=0); each bone's transform is
G_parent . T(pivot) . R(rot) . S(sx, sy) . T(-pivot) . T(dx, dy), i.e. it rotates and scales
the rest drawing about its own pivot and inherits everything its parent did.
"""
import math

import cv2
import numpy as np
from scipy import ndimage


def ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def ease_out(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 3


def ease_in(x):
    x = max(0.0, min(1.0, x))
    return x ** 3


def _mat(rot=0.0, sx=1.0, sy=1.0, dx=0.0, dy=0.0, px=0.0, py=0.0):
    c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    # T(p) R S T(-p) T(d)
    a = np.array([[c * sx, -s * sy], [s * sx, c * sy]])
    p = np.array([px, py])
    t = p + a @ (np.array([dx, dy]) - p)
    m = np.eye(3)
    m[:2, :2] = a
    m[:2, 2] = t
    return m


def premultiply(rgba_u8):
    a = rgba_u8.astype(np.float32) / 255.0
    a[..., :3] *= a[..., 3:4]
    return a


class Rig:
    def __init__(self, rgba, bones, weight_maps, step=8, blur=5.0, extra_alpha=(), layers=None):
        """rgba: HxWx4 uint8 drawing. bones: ordered dict name -> (parent|None, (px, py)),
        parents before children. weight_maps: name -> HxW float (any scale; blurred and
        normalised here). extra_alpha: other alpha masks the mesh must also cover (texture
        variants whose outline differs). layers: [(name, HxW 0..1 pixel mask)] back to
        front; each layer draws only its own pixels with only the triangles touching them,
        so parts that swing over each other (near / far legs) never punch holes."""
        self.h, self.w = rgba.shape[:2]
        self.bones = list(bones.items())
        self.index = {n: i for i, (n, _) in enumerate(self.bones)}
        self.textures = {'base': premultiply(rgba)}
        self._scaled = {}
        cover = rgba[..., 3] > 0
        for m in extra_alpha:
            cover |= m > 0
        cover = ndimage.binary_dilation(cover, iterations=step + 2)
        # grid mesh over the covered area
        xs = np.arange(-step, self.w + 2 * step, step, dtype=np.float32)
        ys = np.arange(-step, self.h + 2 * step, step, dtype=np.float32)
        gx, gy = np.meshgrid(xs, ys)
        nx, ny = len(xs), len(ys)
        verts = np.stack([gx.ravel(), gy.ravel()], 1)
        tris = []
        for j in range(ny - 1):
            for i in range(nx - 1):
                x0, y0 = int(xs[i]), int(ys[j])
                cx0, cy0 = max(0, x0), max(0, y0)
                cx1, cy1 = min(self.w, x0 + step + 1), min(self.h, y0 + step + 1)
                if cx1 <= cx0 or cy1 <= cy0 or not cover[cy0:cy1, cx0:cx1].any():
                    continue
                a, b, c, d = j * nx + i, j * nx + i + 1, (j + 1) * nx + i, (j + 1) * nx + i + 1
                tris += [(a, b, d), (a, d, c)]
        tris = np.array(tris, np.int32)
        used = np.unique(tris)
        remap = -np.ones(len(verts), np.int32)
        remap[used] = np.arange(len(used))
        self.verts = verts[used]
        self.tris = remap[tris]
        # weights: blur each map, sample at the vertices, normalise
        self.W = self._weights(weight_maps, blur)
        # layers: which triangles each one draws
        if layers is None:
            layers = [('all', None)]
        self.layers = []
        self.layer_W = {}
        tv = self.verts[self.tris]                               # (M,3,2)
        lo = np.floor(tv.min(1)).astype(int)
        hi = np.ceil(tv.max(1)).astype(int)
        x0 = np.clip(lo[:, 0], 0, self.w)
        y0 = np.clip(lo[:, 1], 0, self.h)
        x1 = np.clip(hi[:, 0] + 1, 0, self.w)
        y1 = np.clip(hi[:, 1] + 1, 0, self.h)

        def box_sum(img):
            ii = np.zeros((self.h + 1, self.w + 1), np.float64)
            ii[1:, 1:] = np.cumsum(np.cumsum(img, 0), 1)
            return ii[y1, x1] - ii[y0, x1] - ii[y1, x0] + ii[y0, x0]
        alpha = rgba[..., 3].astype(np.float64) / 255
        area = np.maximum(1, (x1 - x0) * (y1 - y0))
        for spec in layers:
            name, m = spec[0], spec[1]
            allowed = spec[2] if len(spec) > 2 else None
            mm = np.ones((self.h, self.w), np.float32) if m is None else np.asarray(m, np.float32)
            occ = ndimage.binary_dilation(mm > 0.02, iterations=2)
            idx = np.nonzero(box_sum(occ.astype(np.float64)) > 0)[0]
            # where the mesh folds, the more opaque triangle must win: draw emptier ones first
            cov = box_sum(alpha * mm)[idx] / area[idx]
            self.layers.append((name, None if m is None else mm, idx[np.argsort(cov, kind='stable')]))
            if isinstance(allowed, dict):
                # this layer has its own weight maps (two touching legs must not drag each
                # other's edges along)
                self.layer_W[name] = self._weights(allowed, blur)
            elif allowed is not None:
                keep = np.zeros(len(self.bones), np.float32)
                keep[[self.index[b] for b in allowed]] = 1
                Wl = self.W * keep
                s_ = Wl.sum(1, keepdims=True)
                self.layer_W[name] = np.where(s_ > 1e-6, Wl / np.maximum(s_, 1e-6), self.W)

    def _weights(self, weight_maps, blur):
        names = [n for n, _ in self.bones]
        W = np.zeros((len(self.verts), len(names)), np.float32)
        vx = np.clip(self.verts[:, 0], 0, self.w - 1)
        vy = np.clip(self.verts[:, 1], 0, self.h - 1)
        for n, m in weight_maps.items():
            m = ndimage.gaussian_filter(np.asarray(m, np.float32), blur) if blur else np.asarray(m, np.float32)
            W[:, self.index[n]] = ndimage.map_coordinates(m, [vy, vx], order=1, mode='nearest')
        s = W.sum(1, keepdims=True)
        W[s[:, 0] < 1e-6, self.index[names[0]]] = 1.0
        return W / np.maximum(W.sum(1, keepdims=True), 1e-6)

    # ------------------------------------------------------------- textures

    def add_texture(self, name, rgba):
        self.textures[name] = premultiply(rgba)
        base = name.split('@')[0]
        self._scaled = {k: v for k, v in self._scaled.items() if k[0] != base}

    def _tex(self, name, f, layer=0):
        """Texture `name` masked to `layer`, resampled by factor f (mip when small)."""
        f = 1.0 if f >= 0.8 else round(f, 2)
        key = (name, f, layer)
        if key not in self._scaled:
            # a layer may have its own version of a texture: '<name>@<layer>'
            t = self.textures.get('%s@%s' % (name, self.layers[layer][0]), self.textures[name])
            m = self.layers[layer][1]
            if m is not None:
                t = t * m[..., None]
            if f != 1.0:
                t = cv2.resize(t, (max(1, int(self.w * f)), max(1, int(self.h * f))),
                               interpolation=cv2.INTER_AREA)
            self._scaled[key] = t
        return self._scaled[key], f

    # ------------------------------------------------------------- posing

    def transforms(self, pose):
        G = {}
        for n, (parent, piv) in self.bones:
            p = pose.get(n, {})
            m = _mat(p.get('rot', 0.0), p.get('sx', 1.0), p.get('sy', 1.0),
                     p.get('dx', 0.0), p.get('dy', 0.0), piv[0], piv[1])
            G[n] = (G[parent] @ m) if parent else m
        return G

    def deform(self, pose, warps=(), W=None):
        G = self.transforms(pose)
        W = self.W if W is None else W
        V = np.c_[self.verts, np.ones(len(self.verts), np.float32)]
        out = np.zeros((len(self.verts), 2), np.float64)
        for n, _ in self.bones:
            w = W[:, self.index[n]]
            if not w.any():
                continue
            out += w[:, None] * (V @ G[n].T)[:, :2]
        for fn in warps:          # extra deformers on the rest positions -> offsets
            out += fn(self.verts)
        return out

    def point(self, pose, xy, bone):
        """Where a rest-space point riding on `bone` ends up (source px, posed)."""
        G = self.transforms(pose)[bone]
        return tuple((G @ np.array([xy[0], xy[1], 1.0]))[:2])

    # ------------------------------------------------------------- rendering

    def render(self, pose, scale, at, anchor, texture='base', warps=(), flip=False):
        """Draw the posed character. scale = screen px per source px; `anchor` (source px,
        posed) lands on screen point `at`. Returns (PIL RGBA image, (x0, y0))."""
        from PIL import Image
        ax, ay = anchor

        def to_screen(P):
            D = np.empty_like(P)
            D[:, 0] = (P[:, 0] - ax) * scale * (-1 if flip else 1) + at[0]
            D[:, 1] = (P[:, 1] - ay) * scale + at[1]
            return D
        Ds = {None: to_screen(self.deform(pose, warps))}
        for name, Wl in self.layer_W.items():
            Ds[name] = to_screen(self.deform(pose, warps, Wl))
        allD = np.concatenate(list(Ds.values()))
        x0, y0 = int(math.floor(allD[:, 0].min())) - 1, int(math.floor(allD[:, 1].min())) - 1
        x1, y1 = int(math.ceil(allD[:, 0].max())) + 2, int(math.ceil(allD[:, 1].max())) + 2
        bw, bh = x1 - x0, y1 - y0
        acc = np.zeros((bh, bw, 4), np.float32)
        yy, xx = np.mgrid[0:bh, 0:bw].astype(np.float32)
        for li, (lname, _, tri_idx) in enumerate(self.layers):
            Dl = (Ds[lname if lname in self.layer_W else None] - [x0, y0]).astype(np.float32)
            tex, f = self._tex(texture, scale, li)
            out = self._warp(Dl, tex, f, self.tris[tri_idx], bw, bh, xx, yy)
            acc = out + acc * (1 - out[..., 3:4])
        al = acc[..., 3:4]
        rgb = np.where(al > 1e-4, acc[..., :3] / np.maximum(al, 1e-4), 0)
        img = np.dstack([rgb, al])
        img = (np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8)
        return Image.fromarray(img, 'RGBA'), (x0, y0)

    def _warp(self, Dl, tex, f, t, bw, bh, xx, yy):
        S = (self.verts * f).astype(np.float64)
        # per-triangle affine dest -> src
        a, b, c = Dl[t[:, 0]], Dl[t[:, 1]], Dl[t[:, 2]]
        A, B, C = S[t[:, 0]], S[t[:, 1]], S[t[:, 2]]
        dm = np.stack([b - a, c - a], 2)                     # (M,2,2) columns
        sm = np.stack([B - A, C - A], 2)
        det = dm[:, 0, 0] * dm[:, 1, 1] - dm[:, 0, 1] * dm[:, 1, 0]
        ok = np.abs(det) > 1e-9
        inv = np.zeros_like(dm)
        inv[ok, 0, 0] = dm[ok, 1, 1] / det[ok]
        inv[ok, 1, 1] = dm[ok, 0, 0] / det[ok]
        inv[ok, 0, 1] = -dm[ok, 0, 1] / det[ok]
        inv[ok, 1, 0] = -dm[ok, 1, 0] / det[ok]
        L = np.einsum('mij,mjk->mik', sm, inv)               # src = A + L (p - a)
        off = A - np.einsum('mij,mj->mi', L, a)
        aff = np.concatenate([L.reshape(-1, 4), off], 1).astype(np.float32)  # l00 l01 l10 l11 ox oy
        # triangle id per pixel (later triangles win where the mesh folds)
        ids = np.full((bh, bw), -1, np.int32)
        pts = np.round(Dl[t] * 16).astype(np.int32)
        for k in np.nonzero(ok)[0]:
            cv2.fillConvexPoly(ids, pts[k], int(k), lineType=cv2.LINE_8, shift=4)
        m = ids >= 0
        k = ids[m]
        px, py = xx[m] + 0.0, yy[m] + 0.0
        mx = np.full((bh, bw), -10, np.float32)
        my = np.full((bh, bw), -10, np.float32)
        af = aff[k]
        mx[m] = af[:, 0] * px + af[:, 1] * py + af[:, 4]
        my[m] = af[:, 2] * px + af[:, 3] * py + af[:, 5]
        return cv2.remap(tex, mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)


# ------------------------------------------------------------------ secondary motion

class Pendulum:
    """A damped angular spring that lags behind its anchor: hair locks, tails, ears.

    step(dt, target, accel_x, accel_y) -> angle (deg). accel = the anchor's acceleration in
    source px/s^2 (moving the anchor right swings the tip left)."""

    def __init__(self, length, stiffness=60.0, damping=7.0, gain=1.0):
        self.L, self.k, self.c, self.g = length, stiffness, damping, gain
        self.a = 0.0
        self.v = 0.0

    def step(self, dt, target, ax=0.0, ay=0.0):
        n = 4
        h = dt / n
        for _ in range(n):
            th = math.radians(self.a)
            torque = -(ax * math.cos(th) + ay * math.sin(th)) / self.L * 57.3 * self.g
            acc = -self.k * (self.a - target) - self.c * self.v + torque
            self.v += acc * h
            self.a += self.v * h
        return self.a


class Track:
    """Keyframed scalar: key(t, value, ease_fn). Holds before the first / after the last."""

    def __init__(self, value=0.0):
        self.keys = [(-1e9, value, ease)]

    def key(self, t, value, fn=ease):
        self.keys.append((t, value, fn))
        self.keys.sort(key=lambda k: k[0])
        return self

    def __call__(self, t):
        ks = self.keys
        if t <= ks[0][0]:
            return ks[0][1]
        for (t0, v0, _), (t1, v1, fn) in zip(ks, ks[1:]):
            if t < t1:
                return v0 + (v1 - v0) * fn((t - t0) / max(1e-9, t1 - t0))
        return ks[-1][1]


class Steps:
    """Piecewise-constant value (texture names, moods): set(t, value)."""

    def __init__(self, value):
        self.keys = [(-1e9, value)]

    def set(self, t, value):
        self.keys.append((t, value))
        self.keys.sort(key=lambda k: k[0])
        return self

    def __call__(self, t):
        v = self.keys[0][1]
        for t0, val in self.keys:
            if t >= t0:
                v = val
        return v
