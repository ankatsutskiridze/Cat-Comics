"""Bathroom, following the reference reel beat by beat (Anka, 2026-10-26): no caption, no
extra gags. The cat waits at the closed door; the door opens on her sitting on the toilet
(deadpan); the cat is draped behind her shoulders, then sprawls on the floor in front of her,
then sits with its back to us looking up at her, then flops and sprawls again. She only
reacts with her face and eyes. Every move between spots is animated (walk / leap / flop).

Rigs: the cat = lib/cat2.py, the girl = lib/girl2.py.

Usage: python scenes/bathroom_ref.py stills | video [out.mp4]
"""
import math
import os
import subprocess
import sys

import cairo
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'lib'))
import cat2 as C  # noqa: E402
import girl2 as G  # noqa: E402

W, H = 1080, 1920
FPS = 30
DUR = 11.6
INK = (43, 31, 30)
FONTS = 'C:/Windows/Fonts'

DX0, DY0, DX1, DY1 = 150, 300, 930, 1560      # door opening
FLOOR = 1560                                   # hallway floor line
IN_FLOOR = 1410                                # bathroom floor line (inside the door)
GIRL_X, GIRL_Y, GIRL_S = 560, 1510, 1.0       # her floor point and scale
SEAT_Y = GIRL_Y - 330 * GIRL_S * math.cos(G.PITCH)

T_DOOR0, T_DOOR1 = 3.2, 3.7      # the door swings open
T_BACK = 99.0                    # (no back-to-the-door ending in this version)

_cache = {}


def ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def lerp(a, b, k):
    return a + (b - a) * k


# ------------------------------------------------------------------ static art (PIL -> cairo)

def _to_cairo(im):
    key = ('cs', id(im))
    if key not in _cache:
        a = np.asarray(im.convert('RGBA')).astype(np.float32) / 255
        al = a[..., 3:4]
        bgra = np.ascontiguousarray((np.dstack([a[..., 2:3] * al, a[..., 1:2] * al, a[..., 0:1] * al, al]) * 255)
                                    .astype(np.uint8))
        _cache[key] = (cairo.ImageSurface.create_for_data(memoryview(bgra), cairo.FORMAT_ARGB32, im.width, im.height),
                       bgra)
    return _cache[key][0]


def hallway():
    if 'hall' in _cache:
        return _cache['hall']
    im = Image.new('RGBA', (W, H), (244, 236, 222, 255))
    d = ImageDraw.Draw(im)
    for x in range(0, W, 110):
        d.rectangle((x, 0, x + 55, FLOOR), fill=(239, 230, 214, 255))
    d.rectangle((0, FLOOR, W, H), fill=(208, 170, 128, 255))
    d.rectangle((0, FLOOR - 30, W, FLOOR), fill=(250, 246, 238, 255), outline=INK, width=7)
    for i, y in enumerate(range(FLOOR + 80, H, 120)):
        d.line((0, y, W, y), fill=(182, 142, 100, 255), width=5)
        for x in range(-150 + 170 * (i % 2), W, 340):
            d.line((x, y - 120, x, y), fill=(182, 142, 100, 255), width=4)
    d.rectangle((DX0 - 40, DY0 - 40, DX1 + 40, DY1), fill=(176, 116, 70, 255), outline=INK, width=8)
    d.rectangle((DX0, DY0, DX1, DY1), fill=(40, 30, 28, 255))
    _cache['hall'] = im
    return im


def bathroom():
    """Inside the door: tiles, a mirror and sink on the right, the toilet's tank and seat
    (front view) behind and under her."""
    if 'bath' in _cache:
        return _cache['bath']
    w, h = DX1 - DX0, DY1 - DY0
    im = Image.new('RGBA', (w, h), (196, 226, 242, 255))
    d = ImageDraw.Draw(im)
    for x in range(0, w, 96):
        d.line((x, 0, x, h), fill=(160, 200, 224, 255), width=4)
    for y in range(0, h, 96):
        d.line((0, y, w, y), fill=(160, 200, 224, 255), width=4)
    fy = IN_FLOOR - DY0
    d.rectangle((0, fy, w, h), fill=(146, 170, 214, 255))
    d.line((0, fy, w, fy), fill=INK, width=6)
    # sink + mirror on the right
    sx = w - 150
    d.rounded_rectangle((sx - 10, 540, w + 30, 610), radius=22, fill=(252, 252, 252, 255), outline=INK, width=7)
    d.rectangle((sx + 50, 610, sx + 104, fy), fill=(236, 236, 240, 255), outline=INK, width=7)
    d.rounded_rectangle((sx + 10, 270, w + 20, 480), radius=16, fill=(214, 236, 248, 255), outline=INK, width=7)
    # a towel ring and towel on the left
    d.ellipse((40, 360, 120, 440), outline=INK, width=6)
    d.rounded_rectangle((40, 400, 120, 640), radius=14, fill=(245, 211, 39, 255), outline=INK, width=6)
    # toilet tank (behind her back)
    tx = GIRL_X - DX0
    ty = int(SEAT_Y - DY0)
    d.rounded_rectangle((tx - 150, ty - 360, tx + 150, ty - 90), radius=20, fill=(252, 252, 252, 255),
                        outline=INK, width=7)
    d.rounded_rectangle((tx - 165, ty - 384, tx + 165, ty - 350), radius=12, fill=(244, 244, 248, 255),
                        outline=INK, width=6)
    d.rounded_rectangle((tx + 80, ty - 330, tx + 120, ty - 312), radius=6, fill=(200, 200, 210, 255), outline=INK, width=4)
    # bath mat
    d.rounded_rectangle((tx - 230, fy + 70, tx + 230, fy + 135), radius=30, fill=(206, 178, 232, 255), outline=INK, width=6)
    _cache['bath'] = im
    return im


def draw_bowl(ctx):
    """Seat rim and pedestal of the toilet, front view, drawn just before her."""
    x, y = GIRL_X, SEAT_Y
    ctx.set_line_width(7)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.save()
    ctx.translate(x, y + 20)
    ctx.scale(175, 52)
    ctx.arc(0, 0, 1, 0, 2 * math.pi)
    ctx.restore()
    ctx.set_source_rgb(0.97, 0.97, 0.98)
    ctx.fill_preserve()
    ctx.set_source_rgb(*[v / 255 for v in INK])
    ctx.stroke()
    ctx.move_to(x - 120, y + 50)
    ctx.line_to(x + 120, y + 50)
    ctx.line_to(x + 80, IN_FLOOR + 80)
    ctx.line_to(x - 80, IN_FLOOR + 80)
    ctx.close_path()
    ctx.set_source_rgb(1, 1, 1)
    ctx.fill_preserve()
    ctx.set_source_rgb(*[v / 255 for v in INK])
    ctx.stroke()


def door_leaf(ctx, frac):
    """The door, hinged on the left; frac 1 = closed, ~0.12 = open against the jamb."""
    w = (DX1 - DX0) * frac
    shade = 0.16 * (1 - frac)
    ctx.rectangle(DX0, DY0, w, DY1 - DY0)
    ctx.set_source_rgb(0.81 - shade, 0.57 - shade, 0.38 - shade)
    ctx.fill_preserve()
    ctx.set_source_rgb(*[v / 255 for v in INK])
    ctx.set_line_width(7)
    ctx.stroke()
    if w > 80:
        ctx.set_source_rgb(0.59, 0.38, 0.23)
        ctx.set_line_width(6)
        for (y0, y1) in [(70, 520), (640, 1150)]:
            ctx.rectangle(DX0 + w * 0.14, DY0 + y0, w * 0.72, y1 - y0)
            ctx.stroke()
        ctx.arc(DX0 + w * 0.87, DY0 + 646, 26, 0, 2 * math.pi)
        ctx.set_source_rgb(0.94, 0.78, 0.35)
        ctx.fill_preserve()
        ctx.set_source_rgb(*[v / 255 for v in INK])
        ctx.set_line_width(5)
        ctx.stroke()


# ------------------------------------------------------------------ the cat's timeline

MEOW = dict(eyes='slit', open=0.62, slant=0.3, mouth='gasp')
MEOW_BIG = dict(eyes='slit', open=0.5, slant=0.35, mouth='scream')


def _blink(face, t, period=2.7, off=0.0):
    ph = (t + off) % period
    if ph < 0.13:
        return dict(eyes='closed', mouth=face.get('mouth', 'flat') if isinstance(face, dict) else 'flat')
    return face


CAT_H = 100                      # cat head px inside the bathroom
TANK_TOP = SEAT_Y - 384
PERCH = (GIRL_X + 95, 740)        # draped behind her shoulders, head out past her hair


def cat_state(t):
    """(pose, face, yaw, x, y, head_px, behind_her)."""
    hall_h = 96
    if t < 1.0:                                  # walks up to the door
        k = t / 1.0
        ph = t * 3.2 * 2 * math.pi
        p = C.pose_stand(step=math.sin(ph), head_turn=-25)
        return p, 'deadpan', 90, lerp(380, DX1 - 70, k), FLOOR + 230, hall_h, False
    if t < T_DOOR1:                              # sits and stares up at the door, tail swishing
        lt = t - 1.0
        p = C.pose_sit(head_turn=-55 + 8 * math.sin(lt * 1.7), head_roll=6 * math.sin(lt * 1.1),
                       tail='ground', tail_side=-1)
        sw = math.sin(lt * 3.0)
        p['tail'] = [(x_ + 0.10 * sw * i / 4, y_ + 0.05 * abs(sw) * i / 4, z_)
                     for i, (x_, y_, z_) in enumerate(p['tail'])]
        face = MEOW if 1.3 < lt < 1.7 else _blink('deadpan', t)
        return p, face, 30, DX1 - 70, FLOOR + 230, hall_h, False
    if t < 4.3:                                  # walks in toward the toilet (away from us)
        k = ease((t - T_DOOR1) / (4.3 - T_DOOR1))
        p = C.pose_stand(step=math.sin(t * 19))
        return (p, 'deadpan', 200, lerp(DX1 - 100, GIRL_X + 230, k), lerp(FLOOR + 230, IN_FLOOR + 40, k),
                lerp(hall_h, CAT_H, k), False)
    if t < 4.75:                                 # leaps up onto the tank, behind her shoulders
        k = (t - 4.3) / 0.45
        x = lerp(GIRL_X + 230, PERCH[0], k)
        y = lerp(IN_FLOOR + 40, PERCH[1], k) - math.sin(k * math.pi) * 160
        return C.pose_leap(), 'deadpan', -100, x, y, CAT_H, k > 0.5
    if t < 6.4:                                  # draped behind her shoulders, head by her cheek
        lt = t - 4.75
        sq = 1 - 0.1 * math.exp(-lt * 8) * math.cos(lt * 20)
        p = C.pose_loaf(head_turn=60 + 10 * math.sin(lt * 1.2), head_roll=-10)
        # the tail hangs down behind her far shoulder
        p['tail'] = [(0, 0.16, -0.68), (0.05, -0.05, -0.85), (0.08, -0.35, -0.95), (0.08, -0.62, -0.92),
                     (0.06, -0.80, -0.85)]
        return p, _blink('deadpan', t, 2.4), 90, PERCH[0], PERCH[1], 125 * sq, True
    if t < 6.85:                                 # hops down in front of her
        k = (t - 6.4) / 0.45
        x = lerp(PERCH[0], GIRL_X - 60, k)
        y = lerp(PERCH[1], IN_FLOOR + 150, k) - math.sin(k * math.pi) * 120
        return C.pose_leap(head_roll=-10), 'surprised', -90, x, y, CAT_H, k < 0.35
    if t < 8.2:                                  # sprawls long on the mat, stretching
        lt = t - 6.85
        reach = 0.5 + 0.5 * math.sin(lt * 2.2)
        p = C.pose_sprawl(head_turn=70, head_roll=-25 + 8 * math.sin(lt * 1.5), reach=reach)
        return p, _blink('smug', t, 2.1), -90, GIRL_X - 40, IN_FLOOR + 150, CAT_H, False
    if t < 8.65:                                 # gets up and turns to her
        k = ease((t - 8.2) / 0.45)
        p = C.pose_stand(step=math.sin(t * 18) * 0.5)
        return (p, 'deadpan', lerp(-90, 180, k), lerp(GIRL_X - 40, GIRL_X + 120, k), IN_FLOOR + 150,
                CAT_H, False)
    if t < 10.0:                                 # sits with its back to us, looking up at her
        lt = t - 8.65
        p = C.pose_sit(head_turn=-15 + 10 * math.sin(lt * 1.4), head_roll=8, tail='ground', tail_side=1)
        tip = math.sin(lt * 5)
        p['tail'][-1] = (p['tail'][-1][0], p['tail'][-1][1] + 0.12 * max(0, tip), p['tail'][-1][2])
        return p, 'deadpan', 180, GIRL_X + 120, IN_FLOOR + 150, CAT_H, False
    lt = t - 10.0                                # flops over and sprawls again, lazy paw wave
    k = ease(lt / 0.3)
    if k < 1:
        return C.pose_bow(head_roll=0), 'deadpan', lerp(180, 90, k), GIRL_X + 120, IN_FLOOR + 150, CAT_H, False
    p = C.pose_sprawl(head_turn=-70, head_roll=20 + 10 * math.sin(lt * 1.6), reach=1.0,
                      wave=math.sin(lt * 4.0))
    return p, _blink('smug', t, 2.0), 90, GIRL_X + 80, IN_FLOOR + 150, CAT_H, False


# ------------------------------------------------------------------ the girl's timeline

def girl_state(t):
    """She sits on the toilet the whole time; only her face and eyes act."""
    breathe = math.sin(t * 2.4)
    tilt = 2 * math.sin(t * 0.7)
    p = G.pose_sit('knees')
    base = dict(G.FACES['bored'])
    if t < 4.75:
        f = dict(base, look=(0.0, 0.3))
    elif t < 6.4:                                 # cat on her shoulders: eyes slide to it
        f = dict(G.FACES['annoyed'], look=(0.8, -0.2))
        tilt = -4
    elif t < 8.65:                                # stares down at the sprawl
        f = dict(base, lid=0.5, look=(-0.4, 0.9))
        tilt = 3
    elif t < 10.0:
        f = dict(base, lid=0.42, look=(0.4, 0.8))
    else:
        f = dict(G.FACES['deadpan'], look=(0.0, 0.2))
    ph = (t + 0.4) % 3.1
    if ph < 0.13:
        f = dict(f, closed=True)
    return p, f, tilt, 0.0, breathe


# ------------------------------------------------------------------ captions

def font(size, name='segoeprb.ttf'):
    key = ('f', name, size)
    if key not in _cache:
        _cache[key] = ImageFont.truetype(os.path.join(FONTS, name), size)
    return _cache[key]


def caption_img(text, size=54, rot=-2.0):
    key = ('cap', text)
    if key in _cache:
        return _cache[key]
    f = font(size)
    bb = ImageDraw.Draw(Image.new('RGB', (1, 1))).textbbox((0, 0), text, font=f)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    pw, ph = tw + 80, th + 60
    paper = Image.new('RGBA', (pw + 30, ph + 30), (0, 0, 0, 0))
    d = ImageDraw.Draw(paper)
    d.rectangle((12, 16, pw + 12, ph + 16), fill=(0, 0, 0, 60))
    d.rectangle((4, 4, pw + 4, ph + 4), fill=(255, 255, 255, 255))
    d.text((4 + 40 - bb[0], 4 + 30 - bb[1]), text, font=f, fill=(20, 16, 18, 255))
    for sx in (40, pw - 40):
        tape = Image.new('RGBA', (100, 36), (245, 211, 39, 190)).rotate(-25 if sx < pw / 2 else 25, expand=True)
        paper.alpha_composite(tape, (int(sx - tape.width / 2 + 4), -6))
    _cache[key] = paper.rotate(rot, expand=True, resample=Image.BICUBIC)
    return _cache[key]


# ------------------------------------------------------------------ frame

def frame(t):
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    ctx.set_source_surface(_to_cairo(hallway()), 0, 0)
    ctx.paint()
    pose, face, yaw, cx, cy, hpx, behind = cat_state(t)
    inside = t >= T_DOOR0
    cat_inside = t >= T_DOOR1
    if inside:
        ctx.save()
        ctx.rectangle(DX0, DY0, DX1 - DX0, DY1 - DY0)
        ctx.clip()
        ctx.set_source_surface(_to_cairo(bathroom()), DX0, DY0)
        ctx.paint()
        ctx.restore()
        if cat_inside and behind:
            surf.flush()
            C.draw_cat(surf, pose, cx, cy, hpx, yaw=yaw, face=face, shadow=False)
        ctx = cairo.Context(surf)
        ctx.rectangle(DX0, DY0, DX1 - DX0, DY1 - DY0)
        ctx.clip()
        draw_bowl(ctx)
        gp, gf, tilt, nod, br = girl_state(t)
        G.draw_girl(ctx, GIRL_X, GIRL_Y, GIRL_S, gp, gf, tilt=tilt, nod=nod, breathe=br)
        if cat_inside and not behind:
            surf.flush()
            C.draw_cat(surf, pose, cx, cy, hpx, yaw=yaw, face=face)
        ctx = cairo.Context(surf)
        k = ease((t - T_DOOR0) / (T_DOOR1 - T_DOOR0))
        door_leaf(ctx, 1 - 0.88 * k)
    else:
        door_leaf(ctx, 1.0)
    if not cat_inside:
        surf.flush()
        C.draw_cat(surf, pose, cx, cy, hpx, yaw=yaw, face=face)
    surf.flush()
    a = np.ndarray((H, W, 4), np.uint8, surf.get_data()).copy()
    return Image.fromarray(a[..., [2, 1, 0, 3]], 'RGBA').convert('RGB')


def stills():
    ts = [0.5, 2.2, 4.0, 4.55, 5.6, 7.5, 9.3, 10.8]
    tw, th = 240, 427
    sheet = Image.new('RGB', (len(ts) * (tw + 8) + 8, th + 16), 'white')
    for i, t in enumerate(ts):
        sheet.paste(frame(t).resize((tw, th), Image.LANCZOS), (8 + i * (tw + 8), 8))
    p = os.path.join(ROOT, 'output', 'bathroom_ref_stills.png')
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
        video(sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, 'output', 'bathroom_ref_silent.mp4'))
    else:
        stills()
