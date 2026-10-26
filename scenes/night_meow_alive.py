"""Night meow, ALIVE: the same story, shots, clock times, captions and timing as
scenes/night_meow.py, but both characters are animated rigs built from the drawings
instead of pasted pictures:

- the girl = her bedroom drawings on mesh rigs (lib/girl_bed.py): she breathes, rolls her
  head on the pillow, twitches at every meow, opens her eyes and blinks; when she sits up
  she springs up, her jaw moves on the words, her head shakes, arms tremble, hair sways;
- the cat = the sheet's sitting cat on a mesh rig (lib/cat_rig.py): breathes, blinks, tilts
  and turns its head, flicks its ears, crouches into every meow; it walks off on four
  stepping legs (lib/cat_walk.py); the close-up stare blinks slowly (lib/cat_bust.py).

Timing is night_meow's, so the sound design lines up the same way.

Usage:
  python scenes/night_meow_alive.py stills            -> output/night_meow_alive_stills.png
  python scenes/night_meow_alive.py video [out.mp4]   -> silent 1080x1920 30 fps render
"""
import math
import os
import subprocess
import sys

import cairo
import cv2
import numpy as np
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'lib'))
sys.path.insert(0, os.path.join(ROOT, 'scenes'))
import night_meow as V  # noqa: E402  (shots, timing, captions)
from cat_bust import CatBust  # noqa: E402
from cat_rig import CatSit  # noqa: E402
from cat_walk import CatWalk  # noqa: E402
from girl_bed import BedGirl, ShoutGirl, WORLD_SCALE  # noqa: E402

W, H, FPS, DUR = V.W, V.H, V.FPS, V.DUR
SHOTS, CLOCK, MEOWS, SHOUT = V.SHOTS, V.CLOCK, V.MEOWS, V.SHOUT
BG_DY = V.BG_DY
ease = V.ease
TINT = np.array(V.CAT_TINT, np.float32)
RIM = np.array(V.RIM, np.float32) * 255

# ------------------------------------------------------------------ the cast


def _cat(x, y, h, meows, **kw):
    c = CatSit(x=x, y=y, height=h, **kw)
    for i in meows:
        a, b = MEOWS[i]
        c.meow(a, b - a)
    return c


GIRL = BedGirl(seed=4)
GIRL.face.set(3.2, 'awake').set(5.6, 'annoyed').set(12.6, 'sleep').set(16.4, 'awake')
GIRL.head.key(0.0, 0).key(1.6, -3).key(2.7, 2).key(3.3, 0).key(5.6, 0).key(6.2, 3).key(12.6, 3).key(13.4, -1)
GIRL.breath.key(12.6, 1.0).key(12.8, 2.4).key(14.2, 1.0)        # lies back down: a big sigh
for tj in (0.25, 1.55, 2.7, 3.42, 4.68, 5.82, 7.08, 15.95, 16.42):
    GIRL.jolt(tj)
GIRL.blinks = [3.9, 5.1, 6.6, 7.6, 17.3]

CAT_FOOT = _cat(560, 1460, 380, (0, 1, 2), seed=1, mood='deadpan')
CAT_FOOT.nod.key(0, -0.6)
CAT_FOOT.tilt.key(0.95, 0).key(1.15, 9).key(1.4, 9).key(1.6, 0).key(2.25, 0).key(2.4, -7).key(2.6, 0)
CAT_FOOT.flick(1.2, 'R').flick(2.3, 'L')

CAT_HEAD = _cat(668, 792, 290, (3, 4), seed=2, mood='smug')
CAT_HEAD.yaw.key(3.2, -0.6)
CAT_HEAD.nod.key(3.2, 0.4)
CAT_HEAD.tilt.key(4.15, 0).key(4.3, -8).key(4.55, -8).key(4.7, 0)
CAT_HEAD.flick(3.9, 'L')

CAT_WIN = _cat(925, 1195, 300, (5, 6), seed=3, mood='deadpan')
CAT_WIN.yaw.key(5.6, -0.7)
CAT_WIN.tilt.key(6.6, 0).key(6.75, 10).key(6.95, 0)
CAT_WIN.flick(6.2, 'R')

CAT_SHOUT = CatSit(x=545, y=1500, height=400, seed=5, mood='deadpan')
CAT_SHOUT.mood.set(8.1, 'surprised').set(9.4, 'deadpan')
CAT_SHOUT.nod.key(8.0, -0.4).key(8.2, -0.8)
CAT_SHOUT.earL.key(8.05, 0).key(8.2, -22).key(9.3, -22).key(9.6, 0)
CAT_SHOUT.earR.key(8.05, 0).key(8.2, 22).key(9.3, 22).key(9.6, 0)
CAT_SHOUT.crouch.key(8.05, 0).key(8.18, 0.35).key(9.2, 0.35).key(9.6, 0)
CAT_SHOUT.blink_at(10.2)

SHOUTER = ShoutGirl(t_up=8.0)
SHOUTER.talk = [(8.18, 8.62), (8.85, 9.95)]
SHOUTER.lunge.key(8.0, 0).key(8.3, 1.0).key(10.0, 1.0).key(10.8, 0.6)
SHOUTER.shake.key(8.0, 1.0).key(10.0, 1.0).key(10.6, 0.3)

STARE = CatBust()
STARE.blinks = [(11.45, 0.75)]
STARE.flicks = [12.15]
STARE.tilt.key(10.8, 0).key(12.6, 3)

WALK = CatWalk(430, -230, 1915, 420, 12.75, 15.15, amp=22)


# ------------------------------------------------------------------ helpers

_bg = {}


def world_bg(name):
    """The scene drawing at frame width (world px: y_img = y_world - BG_DY)."""
    if name not in _bg:
        im = Image.open(os.path.join(V.GIRL, name + '.png')).convert('RGBA')
        _bg[name] = im.resize((W, round(im.height * WORLD_SCALE)), Image.LANCZOS)
    return _bg[name].copy()


def paste(dst, img, x, y):
    x, y = int(round(x)), int(round(y))
    cx0, cy0 = max(0, -x), max(0, -y)
    cx1, cy1 = min(img.width, dst.width - x), min(img.height, dst.height - y)
    if cx1 <= cx0 or cy1 <= cy0:
        return
    dst.alpha_composite(img.crop((cx0, cy0, cx1, cy1)), (x + cx0, y + cy0))


def moonlit(img, rim_sigma=4.0, pad=16):
    """Sink a black cat into the night: cool tint + a soft moonlight rim behind it."""
    a = np.pad(np.asarray(img).astype(np.float32), ((pad, pad), (pad, pad), (0, 0)))
    a[..., :3] *= TINT
    rim = np.clip(cv2.GaussianBlur(a[..., 3], (0, 0), rim_sigma) * 0.75, 0, 255)[..., None]
    k = a[..., 3:4] / 255
    out = np.dstack([a[..., :3] * k + RIM * (1 - k), a[..., 3:4] + rim * (1 - k)])
    return Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), 'RGBA'), pad


def draw_cat(world, cat, t):
    """A CatSit into the world image (cat x/y are world coords, as in night_meow)."""
    tmp = Image.new('RGBA', (1, 1))
    from cat_rig import rig, SRC_H, FEET, _yaw_warp
    pose, tex, yaw, nod = cat.state(t)
    img, (x0, y0) = rig().render(pose, cat.height(t) / SRC_H, (cat.x(t), cat.y(t) - BG_DY), FEET, tex,
                                 warps=_yaw_warp(yaw, nod), flip=cat.flip(t))
    del tmp
    # a soft contact shadow, then the moonlit cat
    sh = Image.new('RGBA', (int(cat.height(t) * 0.75), int(cat.height(t) * 0.09)), (0, 0, 0, 0))
    m = np.zeros((sh.height, sh.width), np.float32)
    cv2.ellipse(m, (sh.width // 2, sh.height // 2), (sh.width // 2 - 2, sh.height // 2 - 2), 0, 0, 360, 1.0, -1)
    m = cv2.GaussianBlur(m, (0, 0), sh.height / 4)
    sh = Image.fromarray(np.dstack([np.zeros((sh.height, sh.width, 3), np.uint8), (m * 110).astype(np.uint8)]), 'RGBA')
    paste(world, sh, cat.x(t) - sh.width / 2, cat.y(t) - BG_DY - sh.height * 0.6)
    lit, pad = moonlit(img)
    paste(world, lit, x0 - pad, y0 - pad)


def camera(world, zoom, cx, cy, dx=0.0, dy=0.0):
    """night_meow's Cam on the world image -> BGRA frame array."""
    hw, hh = W / 2 / zoom, H / 2 / zoom
    bg_h = world.height
    cx = min(max(cx, hw), W - hw)
    cy = min(max(cy, BG_DY + hh), BG_DY + bg_h - hh)
    M = np.array([[zoom, 0, -zoom * cx + W / 2 + dx], [0, zoom, zoom * (BG_DY - cy) + H / 2 + dy]], np.float32)
    a = np.asarray(world)
    out = cv2.warpAffine(a, M, (W, H), flags=cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    return out


def girl_into(world, t):
    img, (x, y) = GIRL.render(t)
    paste(world, img, x, y)


# ------------------------------------------------------------------ frames

def frame(t):
    start, name = V.shot_at(t)
    u = (t - start) / (V.shot_end(name) - start)
    m = V.meow_at(t)
    meowing = m is not None
    overlay_face = None
    if name == 'foot':
        world = world_bg('bed_sleep')
        girl_into(world, t)
        draw_cat(world, CAT_FOOT, t)
        rgba = camera(world, 1.0 + 0.05 * u, 540, 1150)
    elif name == 'headboard':
        world = world_bg('bed_sleep')
        girl_into(world, t)
        draw_cat(world, CAT_HEAD, t)
        rgba = camera(world, 1.0 + 0.05 * u, 560, 1000)
    elif name == 'window':
        world = world_bg('bed_sleep')
        girl_into(world, t)
        draw_cat(world, CAT_WIN, t)
        rgba = camera(world, 1.0 + 0.05 * u, 640, 1050)
    elif name == 'shout':
        world = world_bg('sit_shout')
        img, (x, y) = SHOUTER.render(t)
        paste(world, img, x, y)
        draw_cat(world, CAT_SHOUT, t)
        shake = 6 * math.sin(t * 53) * (1 - ease((t - SHOUT[0]) / 0.6)) if t >= SHOUT[0] else 0
        rgba = camera(world, 1.0 + 0.04 * u, 540, 1100, dx=shake)
    elif name == 'stare':
        world = world_bg('sit_shout')
        img, (x, y) = SHOUTER.render(t)
        paste(world, img, x, y)
        rgba = camera(world, 1.9, 540, 1250)
        rgba = (rgba.astype(np.float32) * 0.45 + np.array([0.03, 0.04, 0.09, 0]) * 255 * 0.55)
        rgba[..., 3] = 255
        rgba = rgba.astype(np.uint8)
        z = 1.0 + 0.06 * ease(u)
        img, (x, y) = STARE.render(t, 1330 / 542 * z, (W / 2, H + 40 * z))
        overlay_face = moonlit(img, rim_sigma=8, pad=30) + ((x, y),)
    elif name == 'leave':
        world = world_bg('bed_sleep')
        girl_into(world, t)
        img, (x, y) = WALK.draw(None, t)
        lit, pad = moonlit(img)
        paste(world, lit, x - pad, y - BG_DY - pad)
        rgba = camera(world, 1.0, 540, 960)
    elif name == 'quiet':
        world = world_bg('bed_sleep')
        girl_into(world, t)
        rgba = camera(world, 1.0 + 0.03 * u, 540, 960, dx=(8 * math.sin(t * 61) if meowing else 0))
    else:  # again
        world = world_bg('bed_sleep')
        girl_into(world, t)
        z = 1.0 + 0.45 * ease(u * 1.6)
        rgba = camera(world, z, 530, 950 + 30 * ease(u * 1.6))

    fr = Image.fromarray(rgba, 'RGBA')
    if overlay_face:
        lit, pad, (x, y) = overlay_face
        paste(fr, lit, x - pad, y - pad)
    # captions and words on top (night_meow's own drawing code)
    a = np.asarray(fr.convert('RGB'))
    bgra = np.dstack([a[..., 2], a[..., 1], a[..., 0], np.full(a.shape[:2], 255, np.uint8)])
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    buf = np.ndarray((H, surf.get_stride() // 4, 4), np.uint8, surf.get_data())
    buf[:, :W] = bgra
    surf.mark_dirty()
    ctx = cairo.Context(surf)
    if name == 'foot':
        V.meow_text(ctx, t, 800, 1050, 70)
    elif name == 'headboard':
        V.meow_text(ctx, t, 330, 560, 68, rot=0.1)
    elif name == 'window':
        V.meow_text(ctx, t, 760, 780, 64, rot=-0.1)
    elif name == 'quiet':
        V.meow_text(ctx, t, 470, 1580, 120, rot=-0.15)
    if name == 'shout':
        V.speech_bubble(ctx, t)
    if name != 'stare':
        V.clock(ctx, CLOCK[name])
    surf.flush()
    return surf


# ------------------------------------------------------------------ outputs

STILL_TIMES = [0.5, 1.3, 3.7, 6.0, 8.1, 9.2, 11.6, 13.5, 16.2, 17.6]


def stills():
    tw, th = 360, 640
    cols = 5
    rows = (len(STILL_TIMES) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * (tw + 10) + 10, rows * (th + 10) + 10), (255, 255, 255))
    from PIL import ImageDraw
    d = ImageDraw.Draw(sheet)
    for i, t in enumerate(STILL_TIMES):
        s = frame(t)
        a = np.ndarray((H, s.get_stride() // 4, 4), np.uint8, s.get_data())[:, :W]
        im = Image.fromarray(np.dstack([a[..., 2], a[..., 1], a[..., 0]]), 'RGB')
        x, y = 10 + (i % cols) * (tw + 10), 10 + (i // cols) * (th + 10)
        sheet.paste(im.resize((tw, th), Image.LANCZOS), (x, y))
        d.text((x + 8, y + th - 24), '%.1fs' % t, fill=(255, 0, 0))
    path = os.path.join(ROOT, 'output', 'night_meow_alive_stills.png')
    sheet.save(path)
    print(path)


def _frame_bytes(i):
    s = frame(i / FPS)
    return bytes(s.get_data())


def video(path, workers=4):
    from multiprocessing import Pool
    n = int(DUR * FPS)
    cmd = ['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgra', '-s', '%dx%d' % (W, H),
           '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p',
           '-movflags', '+faststart', path]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool(workers) as pool:
        for i, data in enumerate(pool.imap(_frame_bytes, range(n), chunksize=4)):
            pr.stdin.write(data)
            if i % 60 == 0:
                print('frame %d/%d' % (i, n), flush=True)
    pr.stdin.close()
    pr.wait()
    print(path)


if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'stills'
    if mode == 'stills':
        stills()
    else:
        video(sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, 'output', 'night_meow_alive_silent.mp4'))
