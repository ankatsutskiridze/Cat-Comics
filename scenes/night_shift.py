"""Night shift: the cat wakes its human every half hour from a new spot, she finally sits up
and asks what it wants, it wants NOTHING, walks off, and meows once more from the door.

Premise adapted from a genre reference (research/reference-equmiart-channel.md); our
characters (characters/girl, characters/cat), our clock times, spots, caption and ending.

Art: the girl's scenes are generated images (characters/girl/scenes/, hair recoloured red);
the cat is cut-out poses (characters/cat/images/cut/) composited onto them.

Usage:
  python scenes/night_shift.py stills          -> output/night_shift_stills.png
  python scenes/night_shift.py video [out.mp4] -> silent 1080x1920 30 fps render
"""
import math
import os
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GIRL = os.path.join(ROOT, 'characters', 'girl', 'scenes')
CAT = os.path.join(ROOT, 'characters', 'cat', 'images', 'cut')
FONTS = 'C:/Windows/Fonts'

W, H = 1080, 1920
FPS = 30
SRC_W = 768                     # the generated scenes are 768x1376
S = W / SRC_W
DUR = 23.0
CAT_TINT = (0.80, 0.84, 1.0)    # moonlit: the cat was drawn on a neutral grey

CAPTION = "My cat's night shift:"

# ------------------------------------------------------------------ shots
# Each shot: start time, background image, clock text, cat (pose(s), source-px feet x/y,
# height in source px, mirror), meow times (relative), camera focus + zoom range.
SHOTS = [
    dict(t=0.0, bg='bed_sleep', clock='1:07 AM', cat=dict(open='sit_meow', shut='sit_up', x=118, y=1185, h=235),
         meows=[0.55, 1.6, 2.35], focus=(300, 900), zoom=(1.0, 1.04)),
    dict(t=3.0, bg='bed_awake', clock='1:43 AM', cat=dict(open='sit_meow', shut='sit_up', x=150, y=728, h=150),
         meows=[0.35, 1.25, 2.1], focus=(260, 760), zoom=(1.12, 1.17)),
    dict(t=6.0, bg='bed_awake', clock='2:19 AM', cat=dict(open='lean_meow', shut=None, x=470, y=602, h=195),
         meows=[0.3, 1.1, 1.9, 2.5], focus=(420, 700), zoom=(1.14, 1.2)),
    dict(t=9.0, bg='bed_annoyed', clock='2:56 AM', cat=dict(open='sit_meow', shut='sit_up', x=668, y=872, h=205),
         meows=[0.35, 1.3, 2.2], focus=(520, 790), zoom=(1.12, 1.18)),
    dict(t=12.0, bg='bed_annoyed', clock='3:33 AM', cat=dict(open='sit_meow_side', shut=None, x=400, y=1005, h=225,
                                                           mirror=False),
         meows=[0.3, 0.9, 1.5, 2.1, 2.6], focus=(400, 780), zoom=(1.22, 1.34)),
    dict(t=15.0, bg='sit_shout', clock=None, cat=dict(open=None, shut='sit_up', x=390, y=1010, h=250),
         meows=[], focus=(395, 700), zoom=(1.18, 1.26), bubble=('WHAT DO YOU\nWANT?!', 0.15)),
    dict(t=17.2, bg='closeup', clock=None, cat=None, meows=[], focus=None, zoom=(1.0, 1.06),
         bubble=('NOTHING.', 0.55)),
    dict(t=19.2, bg='bed_annoyed', clock='3:34 AM', cat='walk', meows=[], focus=(380, 860), zoom=(1.0, 1.02)),
    dict(t=21.4, bg='bed_awake', clock='3:34 AM', cat=dict(open='sit_meow', shut='sit_up', x=135, y=1250, h=235),
         meows=[0.05, 0.9], focus=(300, 880), zoom=(1.05, 1.1)),
]


def shot_at(t):
    cur = SHOTS[0]
    for s in SHOTS:
        if t >= s['t']:
            cur = s
    return cur


def shot_end(shot):
    i = SHOTS.index(shot)
    return SHOTS[i + 1]['t'] if i + 1 < len(SHOTS) else DUR


def ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


# ------------------------------------------------------------------ assets

_cache = {}


def img(path):
    if path not in _cache:
        _cache[path] = Image.open(path).convert('RGBA')
    return _cache[path]


def bg(name):
    return img(os.path.join(GIRL, name + '.png'))


def cat_img(name, mirror=False):
    key = ('cat', name, mirror)
    if key not in _cache:
        im = img(os.path.join(CAT, name + '.png')).copy()
        a = np.asarray(im).astype(float)
        al = a[..., 3]
        inner = np.asarray(Image.fromarray(al.astype(np.uint8)).filter(ImageFilter.MinFilter(3))).astype(float)
        ring = (al > 0) & (inner < 250)
        a[ring, :3] = np.minimum(a[ring, :3], 50)        # the grey JPEG halo -> outline colour
        a[..., 3] = np.minimum(al, inner * 0.6 + al * 0.4)
        a[..., :3] *= np.array(CAT_TINT)
        im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA')
        if mirror:
            im = im.transpose(Image.FLIP_LEFT_RIGHT)
        _cache[key] = im
    return _cache[key]


def font(size, name='segoeuib.ttf'):
    key = ('font', name, size)
    if key not in _cache:
        _cache[key] = ImageFont.truetype(os.path.join(FONTS, name), size)
    return _cache[key]


# ------------------------------------------------------------------ camera

def cam_params(shot, t):
    lt = (t - shot['t']) / max(0.01, shot_end(shot) - shot['t'])
    z0, z1 = shot['zoom']
    z = z0 + (z1 - z0) * ease(lt)
    fx, fy = shot['focus'] or (SRC_W / 2, 688)
    # source px -> output px: scale S*z about the focus, focus lands at screen centre-ish
    sc = S * z
    ox = W / 2 - fx * sc
    oy = H * 0.52 - fy * sc
    # keep the image covering the frame
    ox = min(0, max(W - SRC_W * sc, ox))
    oy = min(0, max(H - 1376 * sc, oy))
    # a small shake on each meow
    shake = 0.0
    for m in shot['meows']:
        d = t - shot['t'] - m
        if 0 <= d < 0.25:
            shake = max(shake, 1 - d / 0.25)
    if shot['bg'] == 'sit_shout' and t - shot['t'] < 0.8:
        shake = max(shake, 1.6 * (1 - (t - shot['t']) / 0.8))
    rng = np.random.default_rng(int(t * FPS))
    ox += rng.normal(0, 6 * shake)
    oy += rng.normal(0, 6 * shake)
    return sc, ox, oy


def place(sc, ox, oy, x, y):
    return ox + x * sc, oy + y * sc


# ------------------------------------------------------------------ drawing helpers

def paste_cat(frame, im, sc, ox, oy, x, y, h, squash=1.0, shadow=True):
    """Feet of the cat at source (x, y), height h source px."""
    k = h * sc / im.height
    w2, h2 = max(1, int(im.width * k / squash ** 0.5)), max(1, int(im.height * k * squash))
    cim = im.resize((w2, h2), Image.LANCZOS)
    fx, fy = place(sc, ox, oy, x, y)
    if shadow:
        sh = Image.new('RGBA', (int(w2 * 0.9), max(4, int(h2 * 0.09))), (0, 0, 0, 0))
        ImageDraw.Draw(sh).ellipse((0, 0, sh.width - 1, sh.height - 1), fill=(0, 0, 0, 90))
        sh = sh.filter(ImageFilter.GaussianBlur(4))
        frame.alpha_composite(sh, (int(fx - sh.width / 2), int(fy - sh.height * 0.6)))
    frame.alpha_composite(cim, (int(fx - w2 / 2), int(fy - h2 * 0.985)))


def caption_box(frame, text, cx, cy, size=64, rot=-2.0):
    f = font(size, 'segoeprb.ttf')
    d0 = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    bb = d0.textbbox((0, 0), text, font=f)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    pw, ph = tw + 90, th + 70
    paper = Image.new('RGBA', (pw + 30, ph + 30), (0, 0, 0, 0))
    d = ImageDraw.Draw(paper)
    d.rectangle((12, 16, pw + 12, ph + 16), fill=(0, 0, 0, 70))
    d.rectangle((4, 4, pw + 4, ph + 4), fill=(255, 255, 255, 255))
    d.text((4 + 45 - bb[0], 4 + 35 - bb[1]), text, font=f, fill=(20, 16, 18, 255))
    for sx in (40, pw - 40):
        tape = Image.new('RGBA', (110, 38), (245, 211, 39, 190))
        tape = tape.rotate(-25 if sx < pw / 2 else 25, expand=True)
        paper.alpha_composite(tape, (int(sx - tape.width / 2 + 4), -6))
    paper = paper.rotate(rot, expand=True, resample=Image.BICUBIC)
    frame.alpha_composite(paper, (int(cx - paper.width / 2), int(cy - paper.height / 2)))


def clock_text(frame, text, pop):
    f = font(int(118 * (1 + 0.18 * pop)), 'segoeuib.ttf')
    d = ImageDraw.Draw(frame)
    bb = d.textbbox((0, 0), text, font=f, stroke_width=10)
    x = W / 2 - (bb[2] - bb[0]) / 2 - bb[0]
    y = 330 - (bb[3] - bb[1]) / 2 - bb[1]
    d.text((x, y), text, font=f, fill=(255, 255, 255, 255), stroke_width=10, stroke_fill=(18, 14, 24, 255))


def bubble(frame, text, cx, cy, size, tail, appear):
    """Comic speech bubble, scale-pops in over `appear` 0..1."""
    if appear <= 0:
        return
    k = 0.6 + 0.4 * ease(appear) + 0.08 * math.sin(min(1, appear) * math.pi)
    f = font(int(size * k), 'segoeuib.ttf')
    d0 = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    bb = d0.multiline_textbbox((0, 0), text, font=f, align='center', spacing=6)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    bw, bh = tw + 110 * k, th + 80 * k
    d = ImageDraw.Draw(frame)
    x0, y0 = cx - bw / 2, cy - bh / 2
    tx, ty = tail
    for wdt, col in ((10, (18, 14, 24, 255)), (0, (255, 255, 255, 255))):
        d.polygon([(cx - 40, cy + bh / 2 - 20 - wdt / 2), (cx + 30, cy + bh / 2 - 20 - wdt / 2), (tx, ty)],
                  fill=col if wdt == 0 else None, outline=col if wdt else None, width=wdt)
    d.rounded_rectangle((x0, y0, x0 + bw, y0 + bh), radius=int(min(bw, bh) * 0.45), fill=(255, 255, 255, 255),
                        outline=(18, 14, 24, 255), width=8)
    d.polygon([(cx - 36, cy + bh / 2 - 26), (cx + 26, cy + bh / 2 - 26), (tx, ty)], fill=(255, 255, 255, 255))
    d.line([(cx - 40, cy + bh / 2 - 4), (tx, ty), (cx + 30, cy + bh / 2 - 4)], fill=(18, 14, 24, 255), width=8,
           joint='curve')
    d.multiline_text((cx - tw / 2 - bb[0], cy - th / 2 - bb[1]), text, font=f, fill=(18, 14, 24, 255),
                     align='center', spacing=6)


def meow_lines(frame, mx, my, scale, strength):
    """Little burst lines from the cat's mouth while it meows."""
    if strength <= 0:
        return
    d = ImageDraw.Draw(frame)
    for a in (-150, -120, -60, -30):
        r = math.radians(a)
        r0, r1 = 70 * scale, (110 + 40 * strength) * scale
        d.line([(mx + math.cos(r) * r0, my + math.sin(r) * r0), (mx + math.cos(r) * r1, my + math.sin(r) * r1)],
               fill=(255, 255, 255, int(230 * strength)), width=max(3, int(7 * scale)))


# ------------------------------------------------------------------ frame

def closeup_bg():
    key = 'closeup_bg'
    if key not in _cache:
        b = bg('bed_annoyed').crop((0, 420, 420, 1167)).resize((W, H), Image.LANCZOS)
        b = b.filter(ImageFilter.GaussianBlur(22))
        a = np.asarray(b).astype(float)
        a[..., :3] *= 0.6
        _cache[key] = Image.fromarray(a.astype(np.uint8), 'RGBA')
    return _cache[key]


def frame(t):
    shot = shot_at(t)
    lt = t - shot['t']
    frame = Image.new('RGBA', (W, H), (10, 14, 30, 255))

    if shot['bg'] == 'closeup':
        frame.alpha_composite(closeup_bg())
        z = shot['zoom'][0] + (shot['zoom'][1] - shot['zoom'][0]) * ease(lt / 2.0)
        face = cat_img('face_deadpan')
        k = W * 0.95 * z / face.width
        fim = face.resize((int(face.width * k), int(face.height * k)), Image.LANCZOS)
        frame.alpha_composite(fim, (int(W / 2 - fim.width / 2), int(H - fim.height + 40)))
        txt, at = shot['bubble']
        bubble(frame, txt, W / 2, 520, 150, (W / 2 + 60, 760), (lt - at) / 0.25)
        return frame.convert('RGB')

    sc, ox, oy = cam_params(shot, t)
    b = bg(shot['bg'])
    frame.alpha_composite(b.resize((int(b.width * sc), int(b.height * sc)), Image.BILINEAR), (int(ox), int(oy)))

    c = shot['cat']
    if c == 'walk':                              # walks off along the floor toward the left
        k = ease((lt - 0.2) / 1.9)
        x = 560 - 520 * k
        bob = abs(math.sin(lt * 9)) * 8
        paste_cat(frame, cat_img('walk'), sc, ox, oy, x, 1330 - bob, 215)
    elif c:
        meowing = any(0 <= lt - m < 0.42 for m in shot['meows'])
        name = c['open'] if (meowing or not c['shut']) else c['shut']
        if name is None:
            name = c['shut']
        im = cat_img(name, c.get('mirror', False))
        # pop in on the first 0.18 s of the shot (it just jumped there), squash on each meow
        pop = ease(lt / 0.18)
        sq = 1.0
        for m in shot['meows']:
            d = lt - m
            if 0 <= d < 0.3:
                sq = 1.0 + 0.07 * math.sin(d / 0.3 * math.pi)
        breathe = 1 + 0.012 * math.sin(t * 3.2)
        y = c['y'] - (1 - pop) * 60
        paste_cat(frame, im, sc, ox, oy, c['x'], y, c['h'] * (0.85 + 0.15 * pop) * breathe, squash=sq)
        if meowing and c['open']:
            m = max(m for m in shot['meows'] if lt - m >= 0)
            s = 1 - (lt - m) / 0.42
            mx, my = place(sc, ox, oy, c['x'], c['y'] - c['h'] * 0.78)
            meow_lines(frame, mx, my, sc * c['h'] / 235, s)

    if shot.get('bubble'):
        txt, at = shot['bubble']
        hx, hy = place(sc, ox, oy, 395, 520)
        bubble(frame, txt, W / 2, 330, 96, (hx + 10, hy - 60), (lt - at) / 0.22)

    if shot['clock']:
        first = shot['clock'] != (SHOTS[SHOTS.index(shot) - 1]['clock'] if SHOTS.index(shot) else None)
        pop = max(0.0, 1 - lt / 0.25) if first else 0.0
        clock_text(frame, shot['clock'], pop)
    if t < 3.0:
        caption_box(frame, CAPTION, W / 2, 170)
    return frame.convert('RGB')


# ------------------------------------------------------------------ outputs

STILL_TIMES = [1.0, 4.0, 7.0, 10.0, 13.0, 16.0, 18.3, 20.0, 21.8]


def stills():
    tw, th = 300, 533
    cols = 5
    rows = math.ceil(len(STILL_TIMES) / cols)
    sheet = Image.new('RGB', (cols * (tw + 10) + 10, rows * (th + 10) + 10), 'white')
    d = ImageDraw.Draw(sheet)
    out = os.path.join(ROOT, 'output', 'night_shift')
    os.makedirs(out, exist_ok=True)
    for i, t in enumerate(STILL_TIMES):
        f = frame(t)
        f.save(os.path.join(out, 'still_%04.1fs.png' % t))
        x, y = 10 + (i % cols) * (tw + 10), 10 + (i // cols) * (th + 10)
        sheet.paste(f.resize((tw, th), Image.LANCZOS), (x, y))
        d.text((x + 8, y + th - 30), '%.1fs' % t, fill=(255, 0, 0), font=font(22))
    path = os.path.join(ROOT, 'output', 'night_shift_stills.png')
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
        video(sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, 'output', 'night_shift_silent.mp4'))
