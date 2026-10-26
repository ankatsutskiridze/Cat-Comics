"""The girl in bed, alive: her bedroom drawings (characters/girl/scenes/, 768x1376) on mesh
rigs, so she breathes, shifts, blinks, opens her eyes and shouts IN the drawing.

- BedGirl: lying under the blanket (bed_sleep / bed_awake / bed_annoyed are the same drawing
  with different faces, so the faces are texture swaps on one mesh). Breathing lifts her
  chest and the blanket, the head rolls a little on the pillow, hands twitch; the awake
  faces blink with the sleeping face's closed eyes.
- ShoutGirl: sitting up, yelling, arms out (sit_shout). The jaw opens and closes on the
  words, the head shakes, the arms tremble, the messy hair sways, and she lunges in.

Both draw into a "world" image = the scene drawing scaled to the frame width (WORLD_SCALE),
returning the deformed crop and where it goes.
"""
import math
import os
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from rig import Rig, Track, Steps, ease  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCENES = os.path.join(ROOT, 'characters', 'girl', 'scenes')
WORLD_SCALE = 1080 / 768


def _load(name):
    return np.asarray(Image.open(os.path.join(SCENES, name + '.png')).convert('RGBA'))


def _ellipse(h, w, box, cx, cy, rx, ry, feather=8.0):
    """Soft ellipse mask in crop coords (box = crop origin in scene px)."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    xx += box[0]
    yy += box[1]
    d = np.sqrt(((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2)
    return np.clip((1 - d) * min(rx, ry) / feather + 0.5, 0, 1)


def _poly(h, w, box, pts, feather=4.0):
    from PIL import ImageDraw
    m = Image.new('L', (w, h), 0)
    ImageDraw.Draw(m).polygon([(x - box[0], y - box[1]) for x, y in pts], fill=255)
    a = np.asarray(m).astype(np.float32) / 255
    return ndimage.gaussian_filter(a, feather) if feather else a


def _static_rest(maps, h, w):
    """Everything no bone claims stays put (the room around her)."""
    s = np.ones((h, w), np.float32)
    for m in maps.values():
        s = np.minimum(s, 1 - np.clip(m, 0, 1))
    return s


def _border_pin(h, w, margin=24):
    """Weight that pins the crop's border so the deformed crop pastes back seamlessly."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    d = np.minimum.reduce([xx, yy, w - 1 - xx, h - 1 - yy])
    return np.clip(1 - d / margin, 0, 1)


# ================================================================== lying in bed

BED_BOX = (180, 560, 640, 1080)        # crop of the scene drawing (x0, y0, x1, y1)
BED_BONES = {
    'room': (None, (0.0, 0.0)),
    'chest': ('room', (395.0, 1040.0)),
    'head': ('chest', (392.0, 738.0)),
    'armL': ('chest', (308.0, 792.0)),
    'handL': ('armL', (283.0, 905.0)),
    'armR': ('chest', (492.0, 796.0)),
    'handR': ('armR', (420.0, 830.0)),
}
FACE_BOX = (318, 603, 474, 724)        # where the three bed drawings differ (the face)
EYE_BAND = (326, 636, 466, 694)

_bed = None


def bed_rig():
    global _bed
    if _bed is not None:
        return _bed
    x0, y0, x1, y1 = BED_BOX
    sl = (slice(y0, y1), slice(x0, x1))
    sleep, awake, annoyed = (_load(n)[sl] for n in ('bed_sleep', 'bed_awake', 'bed_annoyed'))
    h, w = sleep.shape[:2]
    box = (x0, y0)
    head = _ellipse(h, w, box, 393, 682, 112, 118, 10) * (1 - _poly(h, w, box, [(280, 800), (520, 800), (520, 1080), (280, 1080)], 6))
    torso = _poly(h, w, box, [(270, 735), (520, 735), (560, 860), (560, 990), (240, 990), (250, 860)], 30)
    armL = _poly(h, w, box, [(292, 785), (330, 790), (318, 860), (300, 945), (258, 945), (262, 880), (284, 820)], 3)
    handL = _poly(h, w, box, [(266, 880), (305, 885), (300, 945), (255, 945)], 3)
    armR = _poly(h, w, box, [(470, 785), (505, 790), (505, 840), (440, 845), (385, 840), (380, 812), (440, 805)], 3)
    handR = _poly(h, w, box, [(378, 805), (425, 808), (428, 845), (380, 845)], 3)
    maps = {'head': head, 'chest': torso * (1 - head), 'armL': armL * (1 - handL), 'handL': handL,
            'armR': armR * (1 - handR), 'handR': handR}
    pin = _border_pin(h, w)
    for k in maps:
        maps[k] = maps[k] * (1 - pin)
    maps['room'] = np.maximum(_static_rest(maps, h, w), pin)
    shift = lambda B: {k: (p, (q[0] - x0, q[1] - y0)) for k, (p, q) in B.items()}  # noqa: E731
    r = Rig(sleep, shift(BED_BONES), maps, step=8, blur=3.0)

    def face_swap(base, src, rect, feather=6):
        m = _poly(h, w, box, [(rect[0], rect[1]), (rect[2], rect[1]), (rect[2], rect[3]), (rect[0], rect[3])], feather)
        out = base.astype(np.float32) * (1 - m[..., None]) + src.astype(np.float32) * m[..., None]
        return out.astype(np.uint8)
    r.add_texture('sleep', sleep)
    r.add_texture('awake', face_swap(sleep, awake, FACE_BOX))
    r.add_texture('annoyed', face_swap(sleep, annoyed, FACE_BOX))
    r.add_texture('awake_blink', face_swap(face_swap(sleep, awake, FACE_BOX), sleep, EYE_BAND, 4))
    r.add_texture('annoyed_blink', face_swap(face_swap(sleep, annoyed, FACE_BOX), sleep, EYE_BAND, 4))
    _bed = r
    return r


class BedGirl:
    """Tracks: face (Steps: sleep / awake / annoyed), head (deg roll), nod, breath (amplitude),
    jolt times (a startled twitch), blinks (auto while awake)."""

    def __init__(self, seed=0):
        self.face = Steps('sleep')
        self.head, self.nod = Track(), Track()
        self.breath = Track(1.0)
        self.jolts = []
        rnd = np.random.default_rng(seed)
        self.blinks = list(np.cumsum(rnd.uniform(1.8, 3.6, 60)))
        self.phase = float(rnd.uniform(0, 6.28))

    def jolt(self, t):
        self.jolts.append(t)
        return self

    def state(self, t):
        face = self.face(t)
        rate = 2 * math.pi / (3.4 if face == 'sleep' else 2.6)
        b = math.sin(t * rate + self.phase) * self.breath(t)
        roll = self.head(t) + (0.8 * math.sin(t * 0.37 + self.phase) if face == 'sleep' else 0)
        nod = self.nod(t)
        lift = 0.0
        for tj in self.jolts:
            dt = t - tj
            if 0 <= dt < 0.5:
                lift = max(lift, math.exp(-dt * 9) * math.sin(min(1, dt / 0.06) * math.pi / 2))
        tex = face
        if face != 'sleep':
            for bt in self.blinks:
                if 0 <= t - bt < 0.12:
                    tex = face + '_blink'
        pose = {
            'chest': dict(sy=1 + 0.010 * b + 0.02 * lift, sx=1 + 0.004 * b),
            'head': dict(rot=roll, dy=-1.2 * b - 10 * lift - nod),
            'armL': dict(rot=0.6 * b),
            'handL': dict(rot=1.5 * math.sin(t * 0.8 + 1)),
            'armR': dict(rot=-0.8 * b - 4 * lift),
            'handR': dict(rot=-2 * lift),
        }
        return pose, tex

    def render(self, t, scale=WORLD_SCALE):
        """-> (RGBA crop at `scale` x the scene drawing, (x, y) in those px)."""
        r = bed_rig()
        pose, tex = self.state(t)
        x0, y0 = BED_BOX[:2]
        return r.render(pose, scale, (x0 * scale, y0 * scale), (0, 0), tex)


# ================================================================== sitting up, shouting

SHOUT_BOX = (170, 400, 650, 880)
SHOUT_BONES = {
    'room': (None, (0.0, 0.0)),
    'body': ('room', (400.0, 790.0)),
    'head': ('body', (396.0, 652.0)),
    'jaw': ('head', (391.0, 598.0)),
    'hairL': ('head', (330.0, 520.0)),
    'hairR': ('head', (470.0, 520.0)),
    'armL': ('body', (298.0, 672.0)),
    'armR': ('body', (498.0, 672.0)),
}
_shout = None


def shout_rig():
    global _shout
    if _shout is not None:
        return _shout
    x0, y0, x1, y1 = SHOUT_BOX
    im = _load('sit_shout')[y0:y1, x0:x1]
    h, w = im.shape[:2]
    box = (x0, y0)
    head = _ellipse(h, w, box, 398, 555, 125, 120, 12)
    jaw = _ellipse(h, w, box, 391, 622, 34, 30, 5)
    hairL = _poly(h, w, box, [(250, 470), (335, 470), (330, 600), (330, 750), (240, 750), (230, 600)], 14)
    hairR = _poly(h, w, box, [(465, 470), (560, 470), (575, 600), (560, 750), (470, 750), (468, 600)], 14)
    armL = _poly(h, w, box, [(270, 650), (318, 660), (300, 720), (270, 800), (190, 810), (180, 740), (230, 700)], 3)
    armR = _poly(h, w, box, [(482, 660), (530, 650), (575, 700), (625, 740), (615, 810), (530, 805), (500, 720)], 3)
    body = _poly(h, w, box, [(240, 430), (560, 430), (600, 780), (200, 780)], 30)
    lower = np.clip((np.arange(h)[:, None] + y0 - 760) / 30, 0, 1) * np.ones((1, w))
    maps = {'jaw': jaw, 'hairL': hairL * (1 - jaw), 'hairR': hairR * (1 - jaw),
            'armL': armL, 'armR': armR}
    maps['head'] = head * (1 - np.maximum.reduce([jaw, hairL, hairR, armL, armR])) * (1 - lower)
    maps['body'] = body * (1 - np.maximum.reduce([head, armL, armR])) * (1 - lower)
    pin = _border_pin(h, w)
    for k in maps:
        maps[k] = maps[k] * (1 - pin)
    maps['room'] = np.maximum(_static_rest(maps, h, w), np.maximum(pin, lower))
    shift = {k: (p, (q[0] - x0, q[1] - y0)) for k, (p, q) in SHOUT_BONES.items()}
    _shout = Rig(im, shift, maps, step=7, blur=3.0)
    return _shout


class ShoutGirl:
    """Tracks: lunge (0 = sitting back, 1 = leaning in), talk = list of (t0, t1) when her
    jaw moves, shake (head anger shake amplitude)."""

    def __init__(self, t_up=0.0):
        self.t_up = t_up
        self.talk = []
        self.lunge = Track(0.0)
        self.shake = Track(1.0)

    def state(self, t):
        u = t - self.t_up
        # spring up: from slumped to upright with an overshoot
        up = 1 - math.exp(-max(0, u) * 10) * math.cos(max(0, u) * 14)
        up = min(1.15, up)
        lunge = self.lunge(t)
        jaw = 1.0
        for a, b in self.talk:
            if a <= t < b:
                # syllables: the mouth closes partway ~5x per second
                jaw = 0.55 + 0.45 * abs(math.sin((t - a) * math.pi * 4.6))
        shake = self.shake(t)
        hs = shake * (3.0 * math.sin(t * 23) + 1.5 * math.sin(t * 37))
        trem = shake * 1.6 * math.sin(t * 41)
        sway = 2.5 * math.sin(t * 5.1)
        pose = {
            'body': dict(sy=0.9 + 0.1 * up + 0.025 * lunge, sx=0.97 + 0.03 * up + 0.02 * lunge,
                         rot=-3 * (1 - min(1, up)), dy=-6 * lunge),
            'head': dict(rot=hs, dy=-3 * lunge),
            'jaw': dict(sy=jaw),
            'hairL': dict(rot=sway + 4 * (1 - min(1, up))),
            'hairR': dict(rot=-sway - 4 * (1 - min(1, up))),
            'armL': dict(rot=trem - 12 * (1 - min(1, up)) - 4 * lunge),
            'armR': dict(rot=-trem + 12 * (1 - min(1, up)) + 4 * lunge),
        }
        return pose

    def render(self, t, scale=WORLD_SCALE):
        r = shout_rig()
        x0, y0 = SHOUT_BOX[:2]
        return r.render(self.state(t), scale, (x0 * scale, y0 * scale), (0, 0))
