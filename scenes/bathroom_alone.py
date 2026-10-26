"""5 minutes alone: the cat waits at the bathroom door, the door opens, and the cat is
already inside, popping up somewhere new on every cut; then she is out and it waits again.

Premise adapted from a genre reference (research/reference-equmiart-channel.md); our
characters, room, beats, caption and looping ending. Test build from the images we already
have: the girl = the sitting cut-out with the chair keyed out (characters/girl/images/cut/
sit_side_nochair.png), the cat = the approved puppet (lib/puppet.py), the room drawn here.

Usage: python scenes/bathroom_alone.py stills | video [out.mp4]
"""
import math
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'lib'))
import puppet as P  # noqa: E402

W, H = 1080, 1920
FPS = 30
DUR = 11.6
INK = (43, 31, 30)
FONTS = 'C:/Windows/Fonts'
GIRL = os.path.join(ROOT, 'characters', 'girl', 'images', 'cut', 'stand_front.png')

# door frame (screen px) and the floor line
DX0, DY0, DX1, DY1 = 150, 300, 930, 1560
FLOOR = 1560
T_OPEN0, T_OPEN1 = 2.6, 3.05
T_BACK = 10.2                      # cut back to the closed door
CUTS = [3.05, 4.45, 5.85, 7.25, 8.7]  # a new cat spot on each

# inside the bathroom (screen px)
G_H = 1080                         # the standing girl's height on screen
G_X, G_Y = 390, 1505               # left edge / feet of the girl cut-out
SEAT_Y = 1150                      # toilet seat top
CAT_H = 250

_cache = {}


def ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def font(size, name='segoeprb.ttf'):
    key = ('f', name, size)
    if key not in _cache:
        _cache[key] = ImageFont.truetype(os.path.join(FONTS, name), size)
    return _cache[key]


# ------------------------------------------------------------------ backgrounds (drawn once)

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
    # door frame (casing)
    d.rectangle((DX0 - 40, DY0 - 40, DX1 + 40, DY1), fill=(176, 116, 70, 255), outline=INK, width=8)
    d.rectangle((DX0, DY0, DX1, DY1), fill=(40, 30, 28, 255))
    _cache['hall'] = im
    return im


def door_panel(width):
    """The door leaf, hinged on the left, `width` px wide (full = closed)."""
    w = max(4, int(width))
    im = Image.new('RGBA', (w, DY1 - DY0), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    shade = int(40 * (1 - width / (DX1 - DX0)))
    col = (206 - shade, 146 - shade, 98 - shade, 255)
    d.rectangle((0, 0, w - 1, DY1 - DY0 - 1), fill=col, outline=INK, width=7)
    if w > 60:
        for (y0, y1) in [(70, 520), (640, 1150)]:
            d.rounded_rectangle((w * 0.14, y0, w * 0.86, y1), radius=10, outline=(150, 98, 60, 255), width=6)
        d.ellipse((w - w * 0.13 - 26, 620, w - w * 0.13 + 26, 672), fill=(240, 200, 90, 255), outline=INK, width=5)
    return im


def bathroom():
    """Inside the door frame: blue tiles, toilet in profile, a sink, a mat."""
    if 'bath' in _cache:
        return _cache['bath']
    w, h = DX1 - DX0, DY1 - DY0
    im = Image.new('RGBA', (w, h), (196, 226, 242, 255))
    d = ImageDraw.Draw(im)
    for x in range(0, w, 96):
        d.line((x, 0, x, h), fill=(160, 200, 224, 255), width=4)
    for y in range(0, h, 96):
        d.line((0, y, w, y), fill=(160, 200, 224, 255), width=4)
    fy = FLOOR - DY0 - 150
    d.rectangle((0, fy, w, h), fill=(146, 170, 214, 255))
    d.line((0, fy, w, fy), fill=INK, width=6)
    # sink on the right
    sx = w - 170
    d.rounded_rectangle((sx - 20, 520, w + 30, 600), radius=24, fill=(252, 252, 252, 255), outline=INK, width=7)
    d.rectangle((sx + 50, 600, sx + 110, fy), fill=(236, 236, 240, 255), outline=INK, width=7)
    d.rounded_rectangle((sx + 30, 260, w + 20, 470), radius=16, fill=(214, 236, 248, 255), outline=INK, width=7)
    d.rectangle((sx + 60, 470, sx + 76, 520), fill=(200, 200, 210, 255), outline=INK, width=5)
    # bath mat
    d.rounded_rectangle((120, fy + 160, 560, fy + 230), radius=30, fill=(206, 178, 232, 255), outline=INK, width=6)
    # toilet roll on the wall
    d.rectangle((40, 720, 150, 740), fill=(190, 190, 200, 255), outline=INK, width=4)
    d.ellipse((60, 700, 130, 790), fill=(250, 232, 236, 255), outline=INK, width=5)
    _cache['bath'] = im
    return im


def toilet(frame, ox, oy, front=False):
    """Toilet seen from the front, back-left of the room, behind her."""
    if front:
        return
    d = ImageDraw.Draw(frame)
    cx, base = DX0 + 190, FLOOR - 120
    d.rounded_rectangle((cx - 90, base - 420, cx + 90, base - 230), radius=16, fill=(252, 252, 252, 255),
                        outline=INK, width=7)
    d.rounded_rectangle((cx - 100, base - 438, cx + 100, base - 410), radius=10, fill=(244, 244, 248, 255),
                        outline=INK, width=6)
    d.ellipse((cx - 110, base - 250, cx + 110, base - 180), fill=(244, 244, 248, 255), outline=INK, width=7)
    d.polygon([(cx - 95, base - 215), (cx + 95, base - 215), (cx + 55, base), (cx - 55, base)],
              fill=(252, 252, 252, 255), outline=INK, width=7)


# ------------------------------------------------------------------ the girl (sitting)

def girl_img():
    if 'girl' not in _cache:
        _cache['girl'] = Image.open(GIRL).convert('RGBA')
    return _cache['girl']


# both eyes of stand_front.png as rotated ellipses (cx, cy, rx, ry, degrees), measured off it
EYES = [(152, 174, 35, 20, -16), (238, 150, 27, 22, -18)]
SKIN = (247, 212, 192, 255)


def girl_blink(im, amount):
    """Lids come down over both eyes as skin (never over hair); a lash line follows the lid;
    fully closed = a soft downward curve."""
    if amount <= 0:
        return im
    key = ('gb', round(amount, 1))
    if key in _cache:
        return _cache[key]
    base = np.asarray(im).astype(int)
    r, g, b = base[..., 0], base[..., 1], base[..., 2]
    hair = (r > g * 1.7) & (r > b * 1.7) & (r > 90)
    skin = tuple(int(v) for v in np.median(base[190:200, 185:205, :3].reshape(-1, 3), axis=0)) + (255,)
    lidimg = Image.new('L', im.size, 0)
    out = im.copy()
    lines = []
    for (cx, cy, rx, ry, deg) in EYES:
        ang = math.radians(deg)
        ca, sa = math.cos(ang), math.sin(ang)

        def T(u, v):
            return (cx + u * ca - v * sa, cy + u * sa + v * ca)
        lid = -ry - 4 + (2 * ry + 8) * min(1.0, amount)
        top = [T(u, -(ry + 6) * math.sqrt(max(0.0, 1 - (u / (rx + 5)) ** 2)))
               for u in np.linspace(-rx - 5, rx + 5, 40)]
        if amount > 0.85:
            # whole eye covered; the closed lid is a curve a little below the middle
            bot = [T(u, (ry + 4) * math.sqrt(max(0.0, 1 - (u / (rx + 5)) ** 2)))
                   for u in np.linspace(rx + 5, -rx - 5, 40)]
            lines.append([T(u, ry * 0.25 + 6 * (1 - (u / rx) ** 2)) for u in np.linspace(-rx * 0.95, rx * 0.95, 20)])
        else:
            half = (rx + 5) * math.sqrt(max(0.0, 1 - (lid / (ry + 6)) ** 2))
            bot = [T(u, lid) for u in np.linspace(half, -half, 20)]
            lines.append([T(u, lid) for u in np.linspace(-half * 0.95, half * 0.95, 20)])
        ImageDraw.Draw(lidimg).polygon(top + bot, fill=255)
    m = (np.asarray(lidimg) > 0) & ~hair
    a = np.asarray(out).copy()
    a[m] = skin
    out = Image.fromarray(a.astype(np.uint8), 'RGBA')
    d = ImageDraw.Draw(out)
    for L in lines:
        d.line(L, fill=(36, 24, 22, 255), width=5, joint='curve')
    _cache[key] = out
    return out


def draw_girl(frame, t):
    im = girl_img()
    blink = 0.0
    for b in (1.0, 4.0, 6.6, 9.4):
        dd = t - b
        if 0 <= dd < 0.18:
            blink = 1.0 - abs(dd - 0.09) / 0.09 * 0.6
    im = girl_blink(im, blink)
    k = G_H / im.height
    br = 1 + 0.006 * math.sin(t * 2.4)                       # breathing
    sigh = 0.0
    for c in CUTS[1:]:                                       # a little sag on each new cut
        dd = t - c
        if 0 <= dd < 0.6:
            sigh = max(sigh, math.sin(dd / 0.6 * math.pi))
    hh = int(G_H * br * (1 - 0.012 * sigh))
    ww = int(im.width * k)
    im2 = im.resize((ww, hh), Image.LANCZOS)
    frame.alpha_composite(im2, (G_X, G_Y - hh + int(8 * sigh)))


def annoyance(frame, t):
    """Her mood climbs with every cut: '...', then a vein mark."""
    n = sum(1 for c in CUTS if t >= c + 0.3)
    hx, hy = G_X + 300, G_Y - G_H + 60
    d = ImageDraw.Draw(frame)
    if n >= 2 and n < 4:
        for i in range(3):
            d.ellipse((hx + i * 30, hy - 10, hx + i * 30 + 16, hy + 6), fill=INK)
    if n >= 4:
        r = 34
        for k in range(4):
            a = math.pi / 4 + k * math.pi / 2
            c, s = math.cos(a), math.sin(a)
            d.line([(hx + 40 + c * 8, hy + s * 8), (hx + 40 + c * r, hy + s * r)], fill=(224, 48, 42), width=10)


# ------------------------------------------------------------------ the cat

def cat_spot(t):
    """Which spot the cat is in and how long it has been there."""
    if t < T_OPEN1:
        return 'hall', t
    if t >= T_BACK:
        return 'hall2', t - T_BACK
    i = max(i for i, c in enumerate(CUTS) if t >= c)
    return ['tank', 'feet', 'front', 'stretch', 'sink'][i], t - CUTS[i]


def puppet_at(frame, x, y, h, mood, t, lt, tilt=0.0, meows=()):
    blink = 0.0
    for b in (0.5, 1.9):
        dd = lt - b
        if 0 <= dd < 0.16:
            blink = 1.0 - abs(dd - 0.08) / 0.08 * 0.6
    m = mood
    for mt in meows:
        if 0 <= lt - mt < 0.45:
            m = 'meow'
    pop = ease(lt / 0.15)
    squash = 1 - 0.14 * math.exp(-lt * 10) * math.cos(lt * 24) if lt < 0.5 else 1.0
    im = P.cat_frame(m, tilt=tilt + 3 * math.sin(t * 1.4), breathe=math.sin(t * 2.6), squash=squash, blink=blink)
    k = h * pop / P.body().height
    im2 = im.resize((max(1, int(im.width * k)), max(1, int(im.height * k))), Image.LANCZOS)
    sh = Image.new('RGBA', (int(h * 0.7), int(h * 0.1)), (0, 0, 0, 0))
    ImageDraw.Draw(sh).ellipse((0, 0, sh.width - 1, sh.height - 1), fill=(0, 0, 0, 70))
    frame.alpha_composite(sh.filter(ImageFilter.GaussianBlur(6)), (int(x - sh.width / 2), int(y - sh.height / 2)))
    frame.alpha_composite(im2, (int(x - im2.width / 2), int(y - im2.height + 8 * k)))


def pose_at(frame, name, x, y, h, lt, flip=False, rot=0.0):
    im = P.pose(name)
    if flip:
        im = im.transpose(Image.FLIP_LEFT_RIGHT)
    pop = ease(lt / 0.15)
    br = 1 + 0.015 * math.sin(lt * 2.6)
    k = h * pop / im.height
    im2 = im.resize((max(1, int(im.width * k)), max(1, int(im.height * k * br))), Image.LANCZOS)
    if rot:
        im2 = im2.rotate(rot, resample=Image.BICUBIC, expand=True)
    frame.alpha_composite(im2, (int(x - im2.width / 2), int(y - im2.height)))


def draw_cat_inside(frame, t, spot, lt, layer):
    """layer 'back' = drawn behind the girl, 'front' = in front of her."""
    cx = DX0 + 190
    if spot == 'tank' and layer == 'back':
        puppet_at(frame, cx, FLOOR - 120 - 430, CAT_H * 0.95, 'deadpan', t, lt)
    elif spot == 'feet' and layer == 'front':
        pose_at(frame, 'lying', G_X + 230, G_Y + 30, 170, lt)
    elif spot == 'front' and layer == 'front':
        puppet_at(frame, G_X + 360, G_Y + 40, CAT_H * 1.15, 'smug', t, lt)
    elif spot == 'stretch' and layer == 'front':
        pose_at(frame, 'stretch', G_X + 210, G_Y + 45, 240, lt, flip=True)
    elif spot == 'sink' and layer == 'front':
        puppet_at(frame, DX1 - 105, DY0 + 525, CAT_H * 0.9, 'deadpan', t, lt, meows=(0.5,))


# ------------------------------------------------------------------ captions

def caption(frame, text, cx, cy, size=58, rot=-2.0):
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
    paper = paper.rotate(rot, expand=True, resample=Image.BICUBIC)
    frame.alpha_composite(paper, (int(cx - paper.width / 2), int(cy - paper.height / 2)))


# ------------------------------------------------------------------ frame

def frame(t):
    f = hallway().copy()
    spot, lt = cat_spot(t)
    inside_visible = T_OPEN0 <= t < T_BACK
    if inside_visible:
        room = bathroom().copy()
        f.alpha_composite(room, (DX0, DY0))
        toilet(f, G_X - 40, G_Y, front=False)
        draw_cat_inside(f, t, spot, lt, 'back')
        toilet(f, G_X - 40, G_Y, front=True)    # the bowl sits under her thighs
        draw_girl(f, t)
        draw_cat_inside(f, t, spot, lt, 'front')
        annoyance(f, t)
        # the door leaf swinging open, then standing open against the left jamb
        k = ease((t - T_OPEN0) / (T_OPEN1 - T_OPEN0))
        f.alpha_composite(door_panel((DX1 - DX0) * (1 - 0.88 * k)), (DX0, DY0))
    else:
        f.alpha_composite(door_panel(DX1 - DX0), (DX0, DY0))
    if spot in ('hall', 'hall2'):
        meows = (0.6, 1.55) if spot == 'hall' else (0.35,)
        puppet_at(f, DX1 - 60, FLOOR + 160, 330, 'deadpan', t, lt, tilt=-4, meows=meows)
    # tiny camera nudge on each cut
    nudge = 0.0
    for c in CUTS + [T_BACK]:
        dd = t - c
        if 0 <= dd < 0.2:
            nudge = 1 - dd / 0.2
    if nudge:
        z = 1 + 0.025 * nudge
        f = f.resize((int(W * z), int(H * z)), Image.BILINEAR).crop(
            (int((W * z - W) / 2), int((H * z - H) / 2), int((W * z - W) / 2) + W, int((H * z - H) / 2) + H))
    if t < 2.6:
        caption(f, 'Me: I just need 5 minutes alone', W / 2, 150, 50)
    elif t >= T_BACK:
        caption(f, 'Me: *leaves the bathroom*', W / 2, 150, 54)
    return f.convert('RGB')


# ------------------------------------------------------------------ outputs

def stills():
    ts = [1.2, 2.85, 3.8, 5.2, 6.6, 8.0, 9.5, 10.9]
    tw, th = 270, 480
    sheet = Image.new('RGB', (len(ts) * (tw + 8) + 8, th + 16), 'white')
    for i, t in enumerate(ts):
        sheet.paste(frame(t).resize((tw, th), Image.LANCZOS), (8 + i * (tw + 8), 8))
    p = os.path.join(ROOT, 'output', 'bathroom_alone_stills.png')
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
        video(sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, 'output', 'bathroom_alone_silent.mp4'))
    else:
        stills()
