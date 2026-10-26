"""Alive test, rigged: the same room and idea as scenes/alive_test.py, with both characters
as animated mesh rigs built from the drawings (no pasted pictures):

the girl (lib/girl_stand.py, the master sheet's big standing drawing) strolls in with her
hands behind her back, stops, looks down at the cat with a head tilt, breathes and blinks,
her long hair swinging; the cat (lib/cat_rig.py) turns its head toward her, looks
surprised, meows at her, crouches, jumps onto the stool along an arc (stretching in the
air), lands with a squash and meows again from up there while her head follows it.

Usage: python scenes/alive_rig.py stills | video [out.mp4]
"""
import math
import os
import subprocess
import sys

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'lib'))
sys.path.insert(0, os.path.join(ROOT, 'scenes'))
import alive_test as A  # noqa: E402  (the room)
from cat_rig import CatSit  # noqa: E402
from girl_stand import GirlStand  # noqa: E402
from rig import ease  # noqa: E402

W, H, FPS = A.W, A.H, A.FPS
DUR = 8.4
CAT_FLOOR, STOOL = A.CAT_FLOOR, A.STOOL
GIRL_Y, GIRL_H = A.GIRL_Y, A.GIRL_H

# ------------------------------------------------------------------ the girl
T_IN, T_STOP = 0.2, 2.7
X_IN, X_STOP = -260, 330
GIRL = GirlStand(x=X_IN, y=GIRL_Y, height=GIRL_H, seed=3)
GIRL.x.key(T_IN, X_IN).key(T_STOP, X_STOP, lambda u: u if u < 0.8 else 0.8 + (1 - (1 - (u - 0.8) / 0.2) ** 2) * 0.2)
GIRL.walk.key(T_IN, 1.0, lambda u: 1.0).key(T_STOP - 0.35, 1.0).key(T_STOP + 0.05, 0.0)
_speed = (X_STOP - X_IN) / (T_STOP - T_IN)
GIRL.cadence = _speed / (2 * math.radians(15) * 520 * GIRL_H / 1180)
GIRL.tilt.key(2.9, 0).key(3.3, 7).key(4.6, 7).key(5.2, 2).key(6.4, 2).key(6.8, 8).key(7.6, 8)
GIRL.turn.key(2.9, 0).key(3.3, 0.5).key(4.7, 0.5).key(5.2, 0.9)
GIRL.nod.key(2.9, 0).key(3.3, 0.8).key(4.7, 0.8).key(5.2, -0.2)
GIRL.lean.key(3.0, 0).key(3.5, 2.5).key(4.8, 2.5).key(5.4, 0)
GIRL.blinks = [1.6, 3.6, 5.6, 7.2, 7.9]

# ------------------------------------------------------------------ the cat
CAT = CatSit(x=CAT_FLOOR[0], y=CAT_FLOOR[1], height=400, seed=8, mood='deadpan')
CAT.yaw.key(0.8, 0).key(1.2, -0.7).key(4.6, -0.7).key(5.4, -0.5)
CAT.mood.set(1.6, 'surprised').set(2.9, 'deadpan').set(5.3, 'smug')
CAT.tilt.key(1.6, 0).key(1.8, 9).key(2.2, 9).key(2.5, 0)
CAT.nod.key(2.6, 0).key(3.0, -0.6).key(4.5, -0.6).key(5.3, 0)
CAT.earR.key(1.55, 0).key(1.65, 12).key(2.6, 12).key(2.8, 0)
CAT.earL.key(1.55, 0).key(1.65, -12).key(2.6, -12).key(2.8, 0)
CAT.flick(0.5, 'R')
CAT.meow(3.6, 0.55)
CAT.meow(6.3, 0.6)
J0, J1 = 4.75, 5.2                          # take-off, landing
CAT.crouch.key(4.4, 0).key(J0, 0.75).key(J0 + 0.06, -0.85, lambda u: u).key(J1 - 0.1, -0.4) \
    .key(J1, 0.0, lambda u: u).key(J1 + 0.07, 0.5).key(J1 + 0.35, 0.0)
CAT.rot.key(J0, 0).key(J0 + 0.1, -24).key(J1 - 0.08, 16).key(J1, 0)


def _arc(u):
    (x0, y0), (x1, y1) = CAT_FLOOR, (STOOL[0], STOOL[1] + 10)
    return x0 + (x1 - x0) * u, y0 + (y1 - y0) * u - math.sin(u * math.pi) * 330


for k in range(13):
    u = k / 12
    x, y = _arc(u)
    t = J0 + (J1 - J0) * u
    CAT.x.key(t, x, lambda v: v)
    CAT.y.key(t, y, lambda v: v)


# ------------------------------------------------------------------ frame

def frame(t):
    f = A.room().copy()
    cx, cy = CAT.x(t), CAT.y(t)
    air = J0 < t < J1
    if air:
        u = (t - J0) / (J1 - J0)
        A.shadow(f, cx, A.FLOOR_Y + 380 if cx < 800 else STOOL[1] + 20, 260 * (1 - 0.4 * math.sin(u * math.pi)), 50)
    else:
        A.shadow(f, cx, cy + 4, 300, 70)
    CAT.draw(f, t)
    A.shadow(f, GIRL.x(t) + 20, GIRL_Y, 360, 60)
    GIRL.draw(f, t)
    return f.convert('RGB')


def stills():
    ts = [0.9, 1.9, 3.4, 3.8, 4.7, 4.95, 5.3, 6.5]
    tw, th = 270, 480
    sheet = Image.new('RGB', (len(ts) * (tw + 8) + 8, th + 16), 'white')
    for i, t in enumerate(ts):
        sheet.paste(frame(t).resize((tw, th), Image.LANCZOS), (8 + i * (tw + 8), 8))
    p = os.path.join(ROOT, 'output', 'alive_rig_stills.png')
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
        video(sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, 'output', 'alive_rig_silent.mp4'))
    else:
        stills()
