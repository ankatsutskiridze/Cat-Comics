"""Alive test: how lively the image-based characters can be.

The girl walks in with her 4-frame walk cycle (with body bob and hair-led timing), passes
the cat; the cat (head-swap puppet) breathes, blinks, tilts its head, looks surprised, jumps
onto a stool along an arc, lands with a squash, sits and meows.

Usage: python scenes/alive_test.py stills | video [out.mp4]
"""
import math
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'lib'))
import puppet as P  # noqa: E402

W, H = 1080, 1920
FPS = 30
DUR = 7.5
GIRL_CUT = os.path.join(ROOT, 'characters', 'girl', 'images', 'cut')

FLOOR_Y = 1250
CAT_FLOOR = (690, 1600)            # feet of the cat sitting on the floor
STOOL = (905, 1335)                # top centre of the stool seat
CAT_H = 400                        # sitting cat height on screen
GIRL_H = 1300                      # walking girl height
GIRL_Y = 1790                      # her feet
T_IN, T_OUT = 0.8, 5.0             # she walks in from off-left
JUMP0, JUMP1 = 3.45, 3.95

INK = (43, 31, 30)
_cache = {}


def ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


# ------------------------------------------------------------------ room (drawn once)

def room():
    if 'room' in _cache:
        return _cache['room']
    im = Image.new('RGBA', (W, H), (240, 231, 218, 255))
    d = ImageDraw.Draw(im)
    # wall stripes, window with daylight, a framed picture
    for x in range(0, W, 120):
        d.rectangle((x, 0, x + 60, FLOOR_Y), fill=(236, 226, 211, 255))
    d.rounded_rectangle((120, 330, 520, 860), radius=10, fill=(178, 214, 236, 255), outline=INK, width=8)
    d.rectangle((300, 330, 340, 860), fill=(245, 238, 226, 255), outline=INK, width=6)
    d.rectangle((120, 575, 520, 615), fill=(245, 238, 226, 255), outline=INK, width=6)
    for (cx, cy, r) in [(210, 430, 46), (250, 450, 34), (430, 700, 40)]:
        d.ellipse((cx - r * 1.6, cy - r, cx + r * 1.6, cy + r), fill=(250, 252, 255, 255))
    d.rectangle((90, 860, 550, 892), fill=(222, 196, 160, 255), outline=INK, width=7)
    d.rectangle((690, 420, 930, 640), fill=(245, 211, 39, 255), outline=INK, width=8)
    d.ellipse((760, 470, 860, 590), fill=(240, 84, 27, 255), outline=INK, width=5)
    # floor boards
    d.rectangle((0, FLOOR_Y, W, H), fill=(214, 176, 132, 255))
    d.rectangle((0, FLOOR_Y - 34, W, FLOOR_Y), fill=(250, 246, 238, 255), outline=INK, width=7)
    for i, y in enumerate(range(FLOOR_Y + 90, H, 140)):
        d.line((0, y, W, y), fill=(186, 146, 104, 255), width=5)
        for x in range(-200 + 180 * (i % 2), W, 360):
            d.line((x, y - 140, x, y), fill=(186, 146, 104, 255), width=4)
    # a rug and the stool
    d.ellipse((60, 1640, 1020, 1880), fill=(232, 120, 132, 255), outline=INK, width=7)
    d.ellipse((140, 1680, 940, 1840), outline=(250, 180, 186, 255), width=6)
    sx, sy = STOOL
    for lx in (sx - 95, sx + 70):
        d.rounded_rectangle((lx, sy + 10, lx + 26, sy + 300), radius=8, fill=(160, 106, 62, 255), outline=INK, width=6)
    d.rounded_rectangle((sx - 140, sy - 22, sx + 140, sy + 30), radius=18, fill=(196, 134, 80, 255),
                        outline=INK, width=7)
    _cache['room'] = im
    return im


def shadow(frame, x, y, w, alpha=70):
    sh = Image.new('RGBA', (int(w), int(w * 0.16)), (0, 0, 0, 0))
    ImageDraw.Draw(sh).ellipse((0, 0, sh.width - 1, sh.height - 1), fill=(0, 0, 0, alpha))
    sh = sh.filter(ImageFilter.GaussianBlur(8))
    frame.alpha_composite(sh, (int(x - sh.width / 2), int(y - sh.height / 2)))


def paste(frame, im, x, y, h):
    """Bottom-centre of im at (x, y), scaled to height h."""
    k = h / im.height
    im2 = im.resize((max(1, int(im.width * k)), max(1, int(h))), Image.LANCZOS)
    frame.alpha_composite(im2, (int(x - im2.width / 2), int(y - im2.height)))


# ------------------------------------------------------------------ the girl

def _sage_shirt(im):
    """This walk cycle came out with a grey-green tee; pull it to the master sheet's sage."""
    a = np.asarray(im).astype(float) / 255
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mx, mn = a[..., :3].max(-1), a[..., :3].min(-1)
    shirt = (g >= r) & (g > b) & ((mx - mn) / (mx + 1e-6) < 0.35) & (mx > 0.3) & (a[..., 3] > 0.5)
    target = np.array([0xbb, 0xb9, 0x85]) / 255
    lum = (0.3 * r + 0.59 * g + 0.11 * b)[..., None]
    ref = 0.3 * target[0] + 0.59 * target[1] + 0.11 * target[2]
    a[shirt, :3] = np.clip(target * (lum[shirt] / ref), 0, 1)
    return Image.fromarray((a * 255).astype(np.uint8), 'RGBA')


def girl_frames():
    if 'girl' not in _cache:
        fr = []
        for i in range(4):
            im = Image.open(os.path.join(GIRL_CUT, 'walk4_%d.png' % i)).convert('RGBA')
            im = im.crop(im.getbbox())
            fr.append(_sage_shirt(im))
        _cache['girl'] = fr
    return _cache['girl']


# Walk cycle built from the 4 drawings: contact, down, passing, contact (other leg), then
# down + passing again for the second step. The body advances by exactly how far the planted
# foot moves back in the drawings, so the feet do not skate.
CYCLE = [0, 1, 2, 3, 1, 2]
HIP_X = [134, 110, 102, 158]               # hip column in each drawing (source px)
PLANT = [(0, 1, 151 - 0, 42), (1, 2, 42, -11), (2, 3, -11, -119),
         (3, 1, 137, 42), (1, 2, 42, -11), (2, 0, -11, -94)]
FRAME_T = 0.2                              # seconds per drawing (a relaxed stroll, ~1.7 steps a second)


def _walk_path():
    """Cumulative hip advance (source px) at the start of each drawing in the cycle."""
    adv = [0.0]
    for (_, _, a, b) in PLANT:
        adv.append(adv[-1] + (a - b))
    return adv                              # len 7; adv[6] = one full cycle


def girl_pos(t):
    """(screen hip x, drawing index) for time t, or None when she is off screen."""
    if t < T_IN:
        return None
    adv = _walk_path()
    k = GIRL_H / max(f.height for f in girl_frames())       # source px -> screen px
    n = (t - T_IN) / FRAME_T
    cyc, rem = divmod(n, len(CYCLE))
    j = int(rem)
    frac = rem - j
    frac = frac - 0.12 * math.sin(2 * math.pi * frac)    # a little ease within each drawing
    dist = (cyc * adv[-1] + adv[j] + (adv[j + 1] - adv[j]) * frac) * k
    x = -260 + dist
    if x > W + 300:
        return None
    return x, CYCLE[j]


def _hair_mask(im):
    a = np.asarray(im).astype(float) / 255
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mx, mn = a[..., :3].max(-1), a[..., :3].min(-1)
    sat = (mx - mn) / (mx + 1e-6)
    m = (r > g * 1.8) & (r > b * 1.8) & (sat > 0.55) & (a[..., 3] > 0.5)
    from scipy import ndimage
    lab, n = ndimage.label(m)                # keep the hair mass only (not shorts seams)
    if n:
        sizes = ndimage.sum(m, lab, range(1, n + 1))
        m = lab == (int(np.argmax(sizes)) + 1)
        m = ndimage.binary_closing(m, iterations=2)
    return m


def hair_swing(fr, amount):
    """Trail the lower hair behind her as she walks (she faces right, so it trails left).
    The swung hair is laid over the original, so nothing behind it is ever revealed."""
    if amount <= 0.01:
        return fr
    from scipy import ndimage
    key = ('hairmask', id(fr))
    if key not in _cache:
        _cache[key] = _hair_mask(fr)
    m = _cache[key]
    a = np.asarray(fr).astype(float)
    h, w = m.shape
    yy, xx = np.mgrid[0:h, 0:w]
    top = h * 0.16                           # roughly the ears: hair above stays put
    wgt = np.clip((yy - top) / (h * 0.32), 0, 1) ** 1.5
    dx = amount * 26 * wgt                   # source px, more at the tips
    src_x = xx + dx                          # sample from the right -> hair moves left
    hair = a * m[..., None]
    out = np.stack([ndimage.map_coordinates(hair[..., c], [yy, src_x], order=1, mode='constant')
                    for c in range(4)], -1)
    base = a.copy()
    al = out[..., 3:4] / 255
    base[..., :3] = out[..., :3] * al + base[..., :3] * (1 - al)
    base[..., 3] = np.maximum(base[..., 3], out[..., 3])
    return Image.fromarray(np.clip(base, 0, 255).astype(np.uint8), 'RGBA')


def draw_girl(frame, t):
    gp = girl_pos(t)
    if gp is None:
        return None
    x, i = gp
    phase = ((t - T_IN) / FRAME_T / 3.0) % 1.0          # one step = 3 drawings
    # hair trails most just after each push-off, settles at the passing pose
    fr = hair_swing(girl_frames()[i], 0.55 + 0.45 * math.cos(2 * math.pi * phase))
    k = GIRL_H / max(f.height for f in girl_frames())
    shadow(frame, x, GIRL_Y, 360, 60)
    im = fr.resize((max(1, int(fr.width * k)), max(1, int(fr.height * k))), Image.LANCZOS)
    frame.alpha_composite(im, (int(x - HIP_X[i] * k), int(GIRL_Y - im.height)))
    return x


# ------------------------------------------------------------------ the cat

def cat_state(t, girl_x):
    """mood, tilt, blink, position, squash for the sitting puppet; or the jump pose."""
    breathe = math.sin(t * 2.6)
    blink = 0.0
    for b in (0.9, 2.95, 5.4, 6.7):
        d = t - b
        if 0 <= d < 0.16:
            blink = 1.0 - abs(d - 0.08) / 0.08 * 0.6
    mood, tilt = 'deadpan', 3 * math.sin(t * 1.3)
    if girl_x is not None and 150 < girl_x < 1150 and t < JUMP0:
        mood = 'surprised'
        tilt = 8 * math.sin((t - 1.4) * 6) * math.exp(-(t - 1.4) * 1.5) if t > 1.4 else 0
    if JUMP0 - 0.25 <= t < JUMP0:           # crouch before the jump
        return dict(kind='sit', mood='angry', tilt=0, blink=0, breathe=0, pos=CAT_FLOOR,
                    squash=1 - 0.14 * ease((t - JUMP0 + 0.25) / 0.25))
    if JUMP0 <= t < JUMP1:
        return dict(kind='jump', k=(t - JUMP0) / (JUMP1 - JUMP0))
    pos = CAT_FLOOR if t < JUMP0 else STOOL
    squash = 1.0
    if t >= JUMP1:
        d = t - JUMP1
        squash = 1 - 0.16 * math.exp(-d * 9) * math.cos(d * 22)
        mood = 'smug' if t < 5.9 else 'deadpan'
        if 5.9 <= t < 6.6:
            mood = 'meow'
            tilt = -7
    return dict(kind='sit', mood=mood, tilt=tilt, blink=blink, breathe=breathe, pos=pos, squash=squash)


def draw_cat(frame, t, girl_x):
    s = cat_state(t, girl_x)
    if s['kind'] == 'jump':
        k = s['k']
        (x0, y0), (x1, y1) = CAT_FLOOR, STOOL
        x = x0 + (x1 - x0) * k
        y = y0 + (y1 - y0) * k - math.sin(k * math.pi) * 330
        im = P.pose('jump')
        shadow(frame, x, FLOOR_Y + 380 if x < 800 else STOOL[1] + 20, 260 * (1 - 0.4 * math.sin(k * math.pi)), 50)
        ang = 18 - 36 * k                   # nose up on take-off, down on landing
        im2 = im.rotate(ang, resample=Image.BICUBIC, expand=True)
        paste(frame, im2, x, y + 60, 300 * im2.height / im.height)
        return
    im = P.cat_frame(s['mood'], tilt=s['tilt'], breathe=s['breathe'], squash=s['squash'], blink=s['blink'])
    x, y = s['pos']
    shadow(frame, x, y + 4, 300, 70)
    paste(frame, im, x, y + 6, CAT_H * im.height / P.body().height)


# ------------------------------------------------------------------ frame + outputs

def frame(t):
    f = room().copy()
    gx = None
    # the girl walks IN FRONT of the floor cat (she is nearer the camera)
    if t < JUMP0:
        gp = girl_pos(t)
        draw_cat(f, t, gp[0] if gp else None)
        gx = draw_girl(f, t)
    else:
        gp = girl_pos(t)
        draw_cat(f, t, gp[0] if gp else None)
        draw_girl(f, t)
    return f.convert('RGB')


def stills():
    ts = [0.5, 1.6, 2.4, 3.3, 3.7, 4.2, 6.2]
    tw, th = 270, 480
    sheet = Image.new('RGB', (len(ts) * (tw + 8) + 8, th + 16), 'white')
    for i, t in enumerate(ts):
        sheet.paste(frame(t).resize((tw, th), Image.LANCZOS), (8 + i * (tw + 8), 8))
    p = os.path.join(ROOT, 'output', 'alive_test_stills.png')
    sheet.save(p)
    print(p)


def _bytes(i):
    return frame(i / FPS).tobytes()


def video(path, workers=4):
    from multiprocessing import Pool
    n = int(DUR * FPS)
    cmd = ['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % (W, H),
           '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p',
           '-movflags', '+faststart', path]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool(workers) as pool:
        for data in pool.imap(_bytes, range(n), chunksize=4):
            pr.stdin.write(data)
    pr.stdin.close()
    pr.wait()
    print(path)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'video':
        video(sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, 'output', 'alive_test.mp4'))
    else:
        stills()
