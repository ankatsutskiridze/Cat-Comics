"""Night shift, ALIVE: the same story, spots, clock times, captions, camera and timing as
scenes/night_shift.py, with both characters as animated rigs built from the drawings:

- the girl in bed (lib/girl_bed.py): breathes, rolls her head, twitches at every meow,
  sleeps / opens her eyes / gets annoyed and blinks; sits up with a spring, her jaw moving on
  "WHAT DO YOU WANT?!", head shaking, arms trembling, hair swaying;
- the cat (lib/cat_rig.py): breathes, blinks, tilts and turns its head, flicks its ears,
  crouches into every meow, lands on each new spot with a squash; says "NOTHING." with its
  mouth in the close-up (lib/cat_bust.py); walks off on four stepping legs (lib/cat_walk.py).

Usage:
  python scenes/night_shift_alive.py stills            -> output/night_shift_alive_stills.png
  python scenes/night_shift_alive.py video [out.mp4]   -> silent 1080x1920 30 fps render
"""
import math
import os
import subprocess
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'lib'))
sys.path.insert(0, os.path.join(ROOT, 'scenes'))
import night_shift as V  # noqa: E402  (shots, camera, captions)
import cat_rig  # noqa: E402
import cat_walk  # noqa: E402
from cat_bust import CatBust  # noqa: E402
from cat_rig import CatSit  # noqa: E402
from girl_bed import BedGirl, ShoutGirl  # noqa: E402

W, H, FPS, DUR = V.W, V.H, V.FPS, V.DUR
SHOTS = V.SHOTS
ease = V.ease
TINT = np.array(V.CAT_TINT, np.float32)

# ------------------------------------------------------------------ the cast

GIRL = BedGirl(seed=7)
GIRL.face.set(3.0, 'awake').set(9.0, 'annoyed').set(21.4, 'awake')
GIRL.head.key(0, 0).key(1.8, -3).key(3.0, 0).key(6.0, 0).key(6.6, 2).key(9.0, 2).key(10, -2).key(12, 0)
GIRL.blinks = [3.8, 5.2, 7.5, 8.6, 10.6, 13.6, 19.8, 20.9, 22.2]
CAT_SPOTS = []           # (shot index, CatSit in SOURCE px: x, y = feet, height = cat px)
for i, s in enumerate(SHOTS):
    c = s['cat']
    if not isinstance(c, dict) or s['bg'] == 'sit_shout':
        continue
    cat = CatSit(x=c['x'], y=c['y'], height=c['h'] * 0.93, seed=10 + i,
                 mood={0: 'deadpan', 1: 'smug', 2: 'smug', 3: 'deadpan', 4: 'deadpan', 8: 'smug'}.get(i, 'deadpan'))
    # it just jumped onto this spot: lands with a squash
    cat.crouch.key(s['t'], 0.55).key(s['t'] + 0.22, 0.0)
    for m in s['meows']:
        cat.meow(s['t'] + m, 0.42)
        if s['bg'] != 'sit_shout':
            GIRL.jolt(s['t'] + m + 0.05)
    cat.nod.key(s['t'], -0.5 if c['y'] > 900 else 0.3)
    cat.yaw.key(s['t'], 0.6 if c['x'] < 384 else -0.6)
    cat.flick(s['t'] + 1.0, 'R')
    cat.tilt.key(s['t'] + 1.5, 0).key(s['t'] + 1.65, 8).key(s['t'] + 1.9, 8).key(s['t'] + 2.05, 0)
    CAT_SPOTS.append((i, cat))

SHOUT_SHOT = next(s for s in SHOTS if s['bg'] == 'sit_shout')
T_SH = SHOUT_SHOT['t']
SHOUTER = ShoutGirl(t_up=T_SH)
SHOUTER.talk = [(T_SH + 0.2, T_SH + 1.7)]
SHOUTER.lunge.key(T_SH, 0).key(T_SH + 0.3, 1).key(T_SH + 2.2, 1)
CAT_SH = CatSit(x=390, y=1010, height=250 * 0.93, seed=40, mood='deadpan')
CAT_SH.nod.key(T_SH, -0.8)
CAT_SH.earL.key(T_SH + 0.1, 0).key(T_SH + 0.25, -18).key(T_SH + 1.6, -18).key(T_SH + 2.0, 0)
CAT_SH.earR.key(T_SH + 0.1, 0).key(T_SH + 0.25, 18).key(T_SH + 1.6, 18).key(T_SH + 2.0, 0)
CAT_SH.blink_at(T_SH + 1.9)

CLOSE = next(s for s in SHOTS if s['bg'] == 'closeup')
BUST = CatBust()
BUST.words = [(CLOSE['t'] + 0.6, CLOSE['t'] + 1.05, 2)]           # "NO-THING."
BUST.blinks = [(CLOSE['t'] + 1.35, 0.6)]
BUST.flicks = [CLOSE['t'] + 0.25]

WALK_SHOT = next(s for s in SHOTS if s['cat'] == 'walk')
TW = WALK_SHOT['t']
WALK_X = (560, 180, TW + 0.2, TW + 2.2)       # source px: walks off toward the door (left)
WALK_H = 215 * 348 / 487                      # walk_side drawing: ear-to-paw share of its height
WALK_AMP = 28.0
WALK_CADENCE = abs(WALK_X[1] - WALK_X[0]) / (WALK_X[3] - WALK_X[2]) / (2 * math.radians(WALK_AMP) * 125 * WALK_H / cat_walk.SRC_H)


# ------------------------------------------------------------------ helpers

_bg = {}


def scene(name, t):
    """The scene drawing at source px with the living girl in it."""
    if name not in _bg:
        _bg[name] = Image.open(os.path.join(V.GIRL, name + '.png')).convert('RGBA')
    im = _bg[name].copy()
    if name == 'sit_shout':
        img, (x, y) = SHOUTER.render(t, 1.0)
    else:
        img, (x, y) = GIRL.render(t, 1.0)
    im.alpha_composite(img, (x, y))
    return im


def tinted(img):
    a = np.asarray(img).astype(np.float32)
    a[..., :3] *= TINT
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA')


def paste(dst, img, x, y):
    x, y = int(round(x)), int(round(y))
    cx0, cy0 = max(0, -x), max(0, -y)
    cx1, cy1 = min(img.width, dst.width - x), min(img.height, dst.height - y)
    if cx1 > cx0 and cy1 > cy0:
        dst.alpha_composite(img.crop((cx0, cy0, cx1, cy1)), (x + cx0, y + cy0))


def shadow(frame, x, y, w):
    sh = Image.new('RGBA', (max(4, int(w)), max(4, int(w * 0.12))), (0, 0, 0, 0))
    ImageDraw.Draw(sh).ellipse((0, 0, sh.width - 1, sh.height - 1), fill=(0, 0, 0, 90))
    from PIL import ImageFilter
    sh = sh.filter(ImageFilter.GaussianBlur(4))
    paste(frame, sh, x - sh.width / 2, y - sh.height * 0.6)


def draw_sit(frame, cat, t, sc, ox, oy):
    pose, tex, yaw, nod = cat.state(t)
    fx, fy = V.place(sc, ox, oy, cat.x(t), cat.y(t))
    h = cat.height(t) * sc
    shadow(frame, fx, fy, h * 0.75)
    img, (x0, y0) = cat_rig.rig().render(pose, h / cat_rig.SRC_H, (fx, fy), cat_rig.FEET, tex,
                                         warps=cat_rig._yaw_warp(yaw, nod))
    paste(frame, tinted(img), x0, y0)
    # where the mouth is, for the meow burst lines
    return V.place(sc, ox, oy, cat.x(t), cat.y(t) - cat.height(t) * 0.70)


def draw_walk(frame, t, sc, ox, oy):
    x0s, x1s, ta, tb = WALK_X
    u = min(1, max(0, (t - ta) / (tb - ta)))
    xs = x0s + (x1s - x0s) * u
    w = cat_walk.CatWalk(0, -1, 0, 0, ta, tb, cadence=WALK_CADENCE, amp=WALK_AMP)
    fx, fy = V.place(sc, ox, oy, xs, 1330)
    shadow(frame, fx, fy, WALK_H * sc * 1.1)
    img, (x0, y0) = cat_walk.rig().render(w.pose(t), WALK_H * sc / cat_walk.SRC_H, (fx, fy), cat_walk.FEET)
    paste(frame, tinted(img), x0, y0)


# ------------------------------------------------------------------ frame

def frame(t):
    shot = V.shot_at(t)
    lt = t - shot['t']
    fr = Image.new('RGBA', (W, H), (10, 14, 30, 255))

    if shot['bg'] == 'closeup':
        fr.alpha_composite(V.closeup_bg())
        z = shot['zoom'][0] + (shot['zoom'][1] - shot['zoom'][0]) * ease(lt / 2.0)
        k = W * 0.95 * z / 394
        img, (x0, y0) = BUST.render(t, k, (W / 2, H + 40))
        paste(fr, tinted(img), x0, y0)
        txt, at = shot['bubble']
        V.bubble(fr, txt, W / 2, 520, 150, (W / 2 + 60, 760), (lt - at) / 0.25)
        return fr.convert('RGB')

    sc, ox, oy = V.cam_params(shot, t)
    b = scene(shot['bg'], t)
    fr.alpha_composite(b.resize((int(b.width * sc), int(b.height * sc)), Image.BILINEAR), (int(ox), int(oy)))

    i = SHOTS.index(shot)
    if shot['cat'] == 'walk':
        draw_walk(fr, t, sc, ox, oy)
    elif shot['bg'] == 'sit_shout':
        draw_sit(fr, CAT_SH, t, sc, ox, oy)
    else:
        cat = next((c for j, c in CAT_SPOTS if j == i), None)
        if cat:
            mx, my = draw_sit(fr, cat, t, sc, ox, oy)
            for m in shot['meows']:
                d = lt - m
                if 0 <= d < 0.42:
                    V.meow_lines(fr, mx, my, sc * shot['cat']['h'] / 235, 1 - d / 0.42)

    if shot.get('bubble'):
        txt, at = shot['bubble']
        hx, hy = V.place(sc, ox, oy, 395, 520)
        V.bubble(fr, txt, W / 2, 330, 96, (hx + 10, hy - 60), (lt - at) / 0.22)
    if shot['clock']:
        first = shot['clock'] != (SHOTS[i - 1]['clock'] if i else None)
        pop = max(0.0, 1 - lt / 0.25) if first else 0.0
        V.clock_text(fr, shot['clock'], pop)
    if t < 3.0:
        V.caption_box(fr, V.CAPTION, W / 2, 170)
    return fr.convert('RGB')


# ------------------------------------------------------------------ outputs

STILL_TIMES = [1.0, 4.0, 7.0, 10.0, 13.0, 15.2, 16.0, 18.0, 20.0, 21.8]


def stills():
    tw, th = 300, 533
    cols = 5
    rows = math.ceil(len(STILL_TIMES) / cols)
    sheet = Image.new('RGB', (cols * (tw + 10) + 10, rows * (th + 10) + 10), 'white')
    d = ImageDraw.Draw(sheet)
    for k, t in enumerate(STILL_TIMES):
        f = frame(t)
        x, y = 10 + (k % cols) * (tw + 10), 10 + (k // cols) * (th + 10)
        sheet.paste(f.resize((tw, th), Image.LANCZOS), (x, y))
        d.text((x + 8, y + th - 30), '%.1fs' % t, fill=(255, 0, 0), font=V.font(22))
    path = os.path.join(ROOT, 'output', 'night_shift_alive_stills.png')
    sheet.save(path)
    print(path)


def _frame_bytes(i):
    return frame(i / FPS).tobytes()


def video(path, workers=4):
    from multiprocessing import Pool
    n = int(DUR * FPS)
    cmd = ['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', '%dx%d' % (W, H),
           '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p',
           '-movflags', '+faststart', path]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool(workers) as pool:
        for i, data in enumerate(pool.imap(_frame_bytes, range(n), chunksize=4)):
            pr.stdin.write(data)
            if i % 90 == 0:
                print('frame %d/%d' % (i, n), flush=True)
    pr.stdin.close()
    pr.wait()
    print(path)


if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'stills'
    if mode == 'stills':
        stills()
    else:
        video(sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, 'output', 'night_shift_alive_silent.mp4'))
