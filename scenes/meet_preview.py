"""Preview of the code-drawn characters together (not an upload): the girl (lib/girl3.py)
walks into the room, stops by the cat (lib/cat3.py), the cat meows at her, she is surprised,
then laughs and talks to it; the cat looks smug. Every frame is drawn fresh.

Usage: python scenes/meet_preview.py stills | video [out.mp4]
"""
import math
import os
import subprocess
import sys

import cairo
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'lib'))
sys.path.insert(0, os.path.join(ROOT, 'scenes'))
import cat3  # noqa: E402
import girl3  # noqa: E402

W, H, FPS = 1080, 1920, 30
DUR = 9.0
GIRL_Y, GIRL_SCALE = 1790, 1.0
CAT_X, CAT_Y, CAT_SCALE = 760, 1640, 0.62
T_IN, T_STOP = 0.0, 3.0
X_IN, X_STOP = -200, 360


def ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def ease_out(x):
    x = max(0.0, min(1.0, x))
    return 1 - (1 - x) ** 2


_room = None


def room():
    global _room
    if _room is None:
        import alive_test as A
        im = np.asarray(A.room().convert('RGBA'))
        bgra = np.ascontiguousarray(np.dstack([im[..., 2], im[..., 1], im[..., 0], im[..., 3]]))
        s = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
        buf = np.ndarray((H, s.get_stride() // 4, 4), np.uint8, s.get_data())
        buf[:, :W] = bgra
        s.mark_dirty()
        _room = s
    return _room


def shadow(ctx, x, y, rx, ry, a=0.18):
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(rx, ry)
    ctx.arc(0, 0, 1, 0, 2 * math.pi)
    ctx.restore()
    ctx.set_source_rgba(0, 0, 0, a)
    ctx.fill()


# ------------------------------------------------------------------ the girl

def girl_state(t):
    u = (t - T_IN) / (T_STOP - T_IN)
    walking = 0 <= u < 1
    # position: steady stroll, settling in the last 15 %
    k = u / 0.85 if u < 0.85 else 1 - (1 - (u - 0.85) / 0.15) ** 2 * 0.15 / 0.85 * 0 + 0
    x = X_IN + (X_STOP - X_IN) * (min(1.0, u) if u < 0.85 else 0.85 + 0.15 * ease_out((u - 0.85) / 0.15)) \
        if u >= 0 else X_IN
    stride = 1.0 if u < 0.8 else max(0.0, 1 - (u - 0.8) / 0.2)
    p = 2 * math.pi * 1.7 * max(0.0, t - T_IN)            # step phase
    pose = {}
    if walking or stride > 0:
        s = stride if walking else 0.0
        ln, lf = max(0.0, math.sin(p)) * s, max(0.0, -math.sin(p)) * s
        pose['thigh_n'] = dict(rot=-5 * math.cos(p) * s, sy=1 - 0.05 * ln)
        pose['shin_n'] = dict(sy=1 - 0.14 * ln, rot=4 * ln)
        pose['thigh_f'] = dict(rot=5 * math.cos(p) * s, sy=1 - 0.05 * lf)
        pose['shin_f'] = dict(sy=1 - 0.14 * lf, rot=4 * lf)
        pose['root'] = dict(dy=-7 * abs(math.cos(p)) * s)
        pose['chest'] = dict(rot=1.2 * math.sin(p) * s)
        pose['head'] = dict(rot=-0.8 * math.sin(p) * s)
    # hair: lags behind the walk, swings when she stops
    sway = 3.0 * math.sin(p - 0.8) * (stride if walking else 0)
    settle = 0.0
    if t > T_STOP - 0.3:
        d = t - (T_STOP - 0.3)
        settle = 5 * math.exp(-d * 2.2) * math.sin(d * 6)
    hl = -2.5 * (1 if walking and stride > 0.5 else 0) + sway + settle
    pose['lockL'] = dict(rot=hl)
    pose['lockR'] = dict(rot=hl * 0.8)
    pose['lockF'] = dict(rot=hl * 0.9)
    expr, blink, look, talk = 'smile', 0.0, (0.0, 0.0), 0.0
    head_rot, turn, nod = 0.0, 0.0, 0.0
    breathe = math.sin(t * 2 * math.pi / 3.2)
    for b in (1.2, 3.4, 6.3, 8.2):
        d = t - b
        if 0 <= d < 0.16:
            blink = math.sin(d / 0.16 * math.pi)
    # 3.0: looks down at the cat
    look_down = ease((t - 3.0) / 0.4)
    head_rot += 7 * look_down
    nod += 0.8 * look_down
    look = (0.6 * look_down, 0.6 * look_down)
    # 4.2: the cat meows -> surprised (head pops back)
    if 4.25 <= t < 5.4:
        expr = 'surprised'
        k = ease((t - 4.25) / 0.12)
        head_rot -= 5 * k
        nod -= 0.6 * k
    # 5.4: laughs, then talks to the cat
    if 5.4 <= t < 6.2:
        expr = 'happy'
        head_rot += 2.5 * math.sin((t - 5.4) * 14) * (1 - (t - 5.4) / 0.8)
    if 6.4 <= t < 8.0:
        talk = abs(math.sin((t - 6.4) * math.pi * 4.2))
        head_rot += 2 * math.sin((t - 6.4) * 3)
    pose.setdefault('head', {})
    pose['head']['rot'] = pose['head'].get('rot', 0) + head_rot
    pose['chest'] = dict(pose.get('chest', {}), sy=1 + 0.006 * breathe)
    pose['turn'] = turn
    pose['nod'] = nod
    return x, pose, expr, blink, look, talk


# ------------------------------------------------------------------ the cat

def cat_state(t):
    mood, mouth, crouch, roll, yaw, look = 'deadpan', 1.0, 0.0, 1.5 * math.sin(t * 1.1), 0.0, (0.0, 0.0)
    blink = 0.0
    for b in (0.9, 2.4, 5.9, 7.6):
        d = t - b
        if 0 <= d < 0.18:
            blink = math.sin(d / 0.18 * math.pi)
    ear_l = ear_r = 0.0
    # she walks in: the cat's ear flicks, it turns its head toward her and follows her
    if 0.8 < t < 1.2:
        ear_l = -14 * math.sin((t - 0.8) / 0.4 * 2 * math.pi) * (1 - (t - 0.8) / 0.4)
    yaw = -0.75 * ease((t - 1.0) / 0.4)
    look = (-0.8 * ease((t - 1.0) / 0.4), -0.5 * ease((t - 2.6) / 0.4))
    # 3.6 crouch, 4.2 meow
    if 3.6 <= t < 4.2:
        crouch = 0.28 * ease((t - 3.6) / 0.6)
    if 4.2 <= t < 5.0:
        uu = (t - 4.2) / 0.8
        mood = 'meow'
        mouth = math.sin(min(1, uu) * math.pi) ** 0.6
        crouch = 0.28 * (1 - ease(uu * 3))
        roll += -7 * math.sin(uu * math.pi)
    if 5.0 <= t < 5.6:
        mood = 'deadpan'
    if t >= 5.6:
        mood = 'smug'
        roll += 4 * ease((t - 5.6) / 0.4)
    if 6.4 <= t < 8.0:                    # listens to her: an ear turns, a slow tilt
        ear_r = 8 * ease((t - 6.6) / 0.3)
    breathe = math.sin(t * 2 * math.pi / 2.4)
    return dict(mood=mood, blink=blink, look=look, head_roll=roll, head_yaw=yaw, breathe=breathe,
                crouch=crouch, ear_l=ear_l, ear_r=ear_r, mouth_open=mouth)


def frame(t):
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    c = cairo.Context(s)
    c.set_source_surface(room(), 0, 0)
    c.paint()
    shadow(c, CAT_X, CAT_Y + 4, 120, 16)
    cat3.draw_cat_front(c, CAT_X, CAT_Y, CAT_SCALE, **cat_state(t))
    x, pose, expr, blink, look, talk = girl_state(t)
    shadow(c, x + 10, GIRL_Y, 150, 20, 0.16)
    girl3.draw_girl(c, x, GIRL_Y, GIRL_SCALE, pose, expr, blink, look, talk)
    s.flush()
    return s


def stills():
    from PIL import Image
    ts = [0.4, 1.2, 2.2, 3.5, 4.5, 5.7, 6.8]
    tw, th = 270, 480
    sheet = Image.new('RGB', (len(ts) * (tw + 8) + 8, th + 16), 'white')
    for i, t in enumerate(ts):
        s = frame(t)
        a = np.ndarray((H, s.get_stride() // 4, 4), np.uint8, s.get_data())[:, :W]
        im = Image.fromarray(np.dstack([a[..., 2], a[..., 1], a[..., 0]]), 'RGB')
        sheet.paste(im.resize((tw, th), Image.LANCZOS), (8 + i * (tw + 8), 8))
    p = os.path.join(ROOT, 'output', 'meet_preview_stills.png')
    sheet.save(p)
    print(p)


def _bytes(i):
    return bytes(frame(i / FPS).get_data())


def video(path, workers=4):
    from multiprocessing import Pool
    n = int(DUR * FPS)
    cmd = ['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgra', '-s', '%dx%d' % (W, H),
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
        video(sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, 'output', 'meet_preview_silent.mp4'))
    else:
        stills()
