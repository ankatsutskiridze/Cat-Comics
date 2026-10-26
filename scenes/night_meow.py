"""Night meow: the cat meows at the sleeping girl from every corner of the room; she sits up
and yells "WHAT do you want?!", the cat stares back, deadpan; she lies down again, the cat
walks off... and meows again from the dark.

Premise adapted from a genre reference (research/reference-equmiart-channel.md, the
"night with the cat" family); our characters, our room tour, our ending.
Art: the girl's bedroom images (characters/girl/scenes/) with the cat's cut-out poses
(characters/cat/poses/) composited on top.

Usage:
  python scenes/night_meow.py stills            -> output/night_meow_stills.png (+ frames)
  python scenes/night_meow.py video [out.mp4]   -> silent 1080x1920 30 fps render
"""
import math
import os
import subprocess
import sys

import cairo
import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GIRL = os.path.join(ROOT, 'characters', 'girl', 'scenes')
POSES = os.path.join(ROOT, 'characters', 'cat', 'poses')

W, H = 1080, 1920
FPS = 30
DUR = 18.2
BG_SCALE = W / 768                       # the girl's images are 768x1376
BG_DY = -7                               # centre their 1935 px height in the 1920 frame
INK = (0.08, 0.04, 0.03)
CAT_TINT = (0.84, 0.86, 0.96)            # the cut-outs are lit for grey paper: sink them into the night
RIM = (0.55, 0.63, 0.88)                 # moonlight rim around the silhouette: a black cat vanishes on a navy wall
RIM_PAD = 24                             # source px around a pose for its rim
BG_H = round(1376 * BG_SCALE)

# shots: (start, name)
SHOTS = [(0.0, 'foot'), (3.2, 'headboard'), (5.6, 'window'), (8.0, 'shout'), (10.8, 'stare'),
         (12.6, 'leave'), (15.2, 'quiet'), (16.4, 'again')]
CLOCK = {'foot': '3:00 AM', 'headboard': '3:12 AM', 'window': '3:26 AM', 'shout': '3:41 AM',
         'stare': '3:41 AM', 'leave': '3:42 AM', 'quiet': '3:42 AM', 'again': '3:43 AM'}
# meows: (start, end) in clip seconds; the cat's mouth is open inside them
MEOWS = [(0.15, 0.95), (1.45, 2.25), (2.6, 3.2), (3.35, 4.15), (4.6, 5.5), (5.75, 6.55),
         (7.0, 7.95), (15.9, 16.9)]
SHOUT = (8.15, 10.6)                     # her speech bubble


def shot_at(t):
    cur = SHOTS[0]
    for s in SHOTS:
        if t >= s[0]:
            cur = s
    return cur


def shot_end(name):
    names = [s[1] for s in SHOTS]
    i = names.index(name)
    return SHOTS[i + 1][0] if i + 1 < len(SHOTS) else DUR


def ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def meow_at(t):
    """(index, phase 0..1) of the meow sounding at t, or None."""
    for i, (a, b) in enumerate(MEOWS):
        if a <= t < b:
            return i, (t - a) / (b - a)
    return None


# ------------------------------------------------------------------ images

def _surface(rgba):
    """uint8 RGBA (h, w, 4) -> premultiplied cairo ARGB32 surface."""
    h, w = rgba.shape[:2]
    a = rgba[..., 3:4].astype(np.float32) / 255
    pre = (rgba[..., :3].astype(np.float32) * a + 0.5).astype(np.uint8)
    bgra = np.dstack([pre[..., 2], pre[..., 1], pre[..., 0], rgba[..., 3]])
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
    buf = np.ndarray((h, s.get_stride() // 4, 4), np.uint8, s.get_data())
    buf[:, :w] = bgra
    s.mark_dirty()
    return s


_cache = {}


def bg(name):
    if name not in _cache:
        im = Image.open(os.path.join(GIRL, name + '.png')).convert('RGBA')
        im = im.resize((W, round(im.height * BG_SCALE)), Image.LANCZOS)
        _cache[name] = _surface(np.array(im))
    return _cache[name]


def pose(name, flip=False):
    key = (name, flip)
    if key not in _cache:
        im = Image.open(os.path.join(POSES, name + '.png')).convert('RGBA')
        if flip:
            im = im.transpose(Image.FLIP_LEFT_RIGHT)
        a = np.pad(np.array(im).astype(np.float32), ((RIM_PAD, RIM_PAD), (RIM_PAD, RIM_PAD), (0, 0)))
        a[..., :3] *= np.array(CAT_TINT, np.float32)
        rim = np.clip(ndimage.gaussian_filter(a[..., 3], 5) * 0.75, 0, 255)[..., None]
        k = a[..., 3:4] / 255                            # cat OVER its rim
        out = np.dstack([a[..., :3] * k + np.array(RIM, np.float32) * 255 * (1 - k),
                         a[..., 3:4] + rim * (1 - k)])
        _cache[key] = _surface(np.clip(out, 0, 255).astype(np.uint8))
    return _cache[key]


# ------------------------------------------------------------------ drawing helpers

class Cam:
    def __init__(self, zoom=1.0, cx=W / 2, cy=H / 2, dx=0.0, dy=0.0):
        self.zoom, self.cx, self.cy, self.dx, self.dy = zoom, cx, cy, dx, dy

    def apply(self, ctx):
        # never show past the background image's edges
        hw, hh = W / 2 / self.zoom, H / 2 / self.zoom
        self.cx = min(max(self.cx, hw), W - hw)
        self.cy = min(max(self.cy, BG_DY + hh), BG_DY + BG_H - hh)
        ctx.translate(W / 2 + self.dx, H / 2 + self.dy)
        ctx.scale(self.zoom, self.zoom)
        ctx.translate(-self.cx, -self.cy)


def draw_bg(ctx, name):
    ctx.save()
    ctx.translate(0, BG_DY)
    ctx.set_source_surface(bg(name), 0, 0)
    ctx.get_source().set_filter(cairo.FILTER_GOOD)
    ctx.paint()
    ctx.restore()


def draw_cat(ctx, name, x, y, h, flip=False, sx=1.0, sy=1.0, rot=0.0, shadow=True):
    """A cut-out pose with its paws (image bottom) centred at (x, y), h px tall."""
    s = pose(name, flip)
    k = h / (s.get_height() - 2 * RIM_PAD)
    w = (s.get_width() - 2 * RIM_PAD) * k
    if shadow:
        ctx.save()
        ctx.translate(x, y - 0.01 * h)
        ctx.scale(w * 0.42, 0.035 * h)
        g = cairo.RadialGradient(0, 0, 0, 0, 0, 1)
        g.add_color_stop_rgba(0, 0, 0, 0, 0.45)
        g.add_color_stop_rgba(1, 0, 0, 0, 0)
        ctx.set_source(g)
        ctx.arc(0, 0, 1, 0, 2 * math.pi)
        ctx.fill()
        ctx.restore()
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(rot)
    ctx.scale(k * sx, k * sy)
    ctx.set_source_surface(s, -s.get_width() / 2, -s.get_height() + RIM_PAD)
    ctx.get_source().set_filter(cairo.FILTER_GOOD)
    ctx.paint()
    ctx.restore()


def outlined_text(ctx, text, x, y, size, rot=0.0, fill=(1, 1, 1), stroke=INK, lw=None,
                  font='Segoe UI Black'):
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(rot)
    ctx.select_font_face(font, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(size)
    e = ctx.text_extents(text)
    ctx.move_to(-e.x_advance / 2, e.height / 2)
    ctx.text_path(text)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.set_line_width(lw or size * 0.16)
    ctx.set_source_rgb(*stroke)
    ctx.stroke_preserve()
    ctx.set_source_rgb(*fill)
    ctx.fill()
    ctx.restore()


def pop(p):
    """0..1 life of a text -> scale with a little overshoot."""
    if p < 0.18:
        return 0.4 + 0.75 * (p / 0.18)                   # quick grow past full size
    return 1.0 + 0.08 * math.exp(-(p - 0.18) * 12) * math.cos((p - 0.18) * 30)


def meow_text(ctx, t, x, y, size=64, rot=-0.12):
    m = meow_at(t)
    if not m:
        return
    i, p = m
    word = ['MEOW!', 'MEOOW!', 'MRRAOW!', 'MEOW!', 'MEOOOW!', 'MAAAU!', 'MEOW!!', 'MEOOOOW!!'][i]
    s = pop(p)
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(s, s)
    outlined_text(ctx, word, 0, 0, size, rot)
    ctx.restore()


def clock(ctx, text):
    """The setup caption: a clock on a taped paper strip, top centre (our caption style)."""
    ctx.save()
    ctx.select_font_face('Segoe Print', cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(76)
    e = ctx.text_extents('3:00 AM')
    w, h = e.x_advance + 90, 130
    ctx.translate(W / 2, 250)
    ctx.rotate(math.radians(-2.0))
    ctx.rectangle(-w / 2 + 8, -h / 2 + 10, w, h)
    ctx.set_source_rgba(0, 0, 0, 0.30)
    ctx.fill()
    ctx.rectangle(-w / 2, -h / 2, w, h)
    ctx.set_source_rgb(1, 1, 1)
    ctx.fill()
    e = ctx.text_extents(text)
    ctx.move_to(-e.x_advance / 2, 28)
    ctx.set_source_rgb(*INK)
    ctx.show_text(text)
    for sx in (-1, 1):
        ctx.save()
        ctx.translate(sx * (w / 2 - 30), -h / 2)
        ctx.rotate(sx * 0.5)
        ctx.rectangle(-45, -16, 90, 32)
        ctx.set_source_rgba(0.96, 0.83, 0.15, 0.75)
        ctx.fill()
        ctx.restore()
    ctx.restore()


def speech_bubble(ctx, t):
    a, b = SHOUT
    if not a <= t < b:
        return
    p = (t - a) / (b - a)
    s = pop(min(1.0, p * 4))
    jit = 3 * math.sin(t * 47)                       # she is shouting: the bubble trembles
    ctx.save()
    ctx.translate(W / 2 + jit, 470)
    ctx.scale(s, s)
    ctx.rotate(math.radians(-3))
    bw, bh = 820, 230
    ctx.new_path()
    ctx.save()
    ctx.scale(bw / 2, bh / 2)
    ctx.arc(0, 0, 1, 0, 2 * math.pi)
    ctx.restore()
    ctx.move_to(-40, bh / 2 - 12)                    # tail toward her mouth
    ctx.line_to(10, bh / 2 + 120)
    ctx.line_to(60, bh / 2 - 18)
    ctx.close_path()
    ctx.set_line_width(10)
    ctx.set_source_rgb(*INK)
    ctx.stroke_preserve()
    ctx.set_source_rgb(1, 1, 1)
    ctx.fill()
    ctx.select_font_face('Segoe UI Black', cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    for k, (line, size) in enumerate([('WHAT', 96), ('do you want?!', 72)]):
        ctx.set_font_size(size)
        e = ctx.text_extents(line)
        ctx.move_to(-e.x_advance / 2, -14 + k * 86)
        ctx.set_source_rgb(*INK)
        ctx.show_text(line)
    ctx.restore()


# ------------------------------------------------------------------ the shots

def frame(t):
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    ctx.set_source_rgb(0.05, 0.07, 0.13)
    ctx.paint()
    start, name = shot_at(t)
    u = (t - start) / (shot_end(name) - start)          # 0..1 through the shot
    m = meow_at(t)
    meowing = m is not None
    kick = math.exp(-m[1] * 9) if m else 0.0            # squash right as a meow starts

    ctx.save()
    if name == 'foot':
        Cam(1.0 + 0.05 * u, 540, 1150).apply(ctx)
        draw_bg(ctx, 'bed_sleep')
        draw_cat(ctx, 'sit_meow' if meowing else 'sit_look_up', 560, 1460, 400,
                 sx=1 + 0.03 * kick, sy=1 - 0.04 * kick + 0.05 * kick * (1 - kick))
        meow_text(ctx, t, 800, 1050, 70)
    elif name == 'headboard':
        Cam(1.0 + 0.05 * u, 560, 1000).apply(ctx)
        draw_bg(ctx, 'bed_awake')
        bob = 10 * kick
        draw_cat(ctx, 'lean_meow', 665, 808 + bob, 420, shadow=False)
        meow_text(ctx, t, 330, 560, 68, rot=0.1)
    elif name == 'window':
        Cam(1.0 + 0.05 * u, 640, 1050).apply(ctx)
        draw_bg(ctx, 'bed_annoyed')
        draw_cat(ctx, 'look_back_meow', 925, 1195, 360, flip=True,
                 sx=1 + 0.02 * kick, sy=1 + 0.03 * kick)
        meow_text(ctx, t, 760, 780, 64, rot=-0.1)
    elif name == 'shout':
        shake = 6 * math.sin(t * 53) * (1 - ease((t - SHOUT[0]) / 0.6)) if t >= SHOUT[0] else 0
        Cam(1.0 + 0.04 * u, 540, 1100, dx=shake).apply(ctx)
        draw_bg(ctx, 'sit_shout')
        draw_cat(ctx, 'sit_look_up', 545, 1500, 420)
    elif name == 'stare':
        # the punchline beat: the cat's face, deadpan, slow push-in, silence
        Cam(1.9, 540, 1250).apply(ctx)
        draw_bg(ctx, 'sit_shout')
        ctx.restore()
        ctx.save()
        ctx.set_source_rgba(0.03, 0.04, 0.09, 0.55)        # push the room back
        ctx.paint()
        z = 1.0 + 0.06 * ease(u)
        ctx.translate(W / 2, H)
        ctx.scale(z, z)
        draw_cat(ctx, 'face_deadpan', 0, 40, 1330, shadow=False)
    elif name == 'leave':
        Cam(1.0, 540, 960).apply(ctx)
        draw_bg(ctx, 'bed_sleep')
        x = 760 - 1050 * ease(u * 1.15)
        step = abs(math.sin(t * 7.5))
        draw_cat(ctx, 'walk_side', x, 1915 - 10 * step, 430, rot=0.02 * math.sin(t * 7.5))
    elif name == 'quiet':
        Cam(1.0 + 0.03 * u, 540, 960, dx=(8 * math.sin(t * 61) if meowing else 0)).apply(ctx)
        draw_bg(ctx, 'bed_sleep')
        meow_text(ctx, t, 470, 1580, 120, rot=-0.15)
    elif name == 'again':
        z = 1.0 + 0.45 * ease(u * 1.6)
        Cam(z, 530, 950 + 30 * ease(u * 1.6)).apply(ctx)
        draw_bg(ctx, 'bed_awake')
    ctx.restore()

    if name == 'shout':
        speech_bubble(ctx, t)
    if name != 'stare':
        clock(ctx, CLOCK[name])
    return surf


# ------------------------------------------------------------------ outputs

STILL_TIMES = [0.5, 2.4, 3.7, 6.0, 9.2, 11.6, 13.8, 16.2, 17.6]


def stills():
    out = os.path.join(ROOT, 'output', 'night_meow')
    os.makedirs(out, exist_ok=True)
    tw, th = 360, 640
    cols = 5
    rows = (len(STILL_TIMES) + cols - 1) // cols
    sheet = cairo.ImageSurface(cairo.FORMAT_ARGB32, cols * (tw + 10) + 10, rows * (th + 10) + 10)
    sc = cairo.Context(sheet)
    sc.set_source_rgb(1, 1, 1)
    sc.paint()
    for i, t in enumerate(STILL_TIMES):
        s = frame(t)
        s.write_to_png(os.path.join(out, 'still_%04.1fs.png' % t))
        x, y = 10 + (i % cols) * (tw + 10), 10 + (i // cols) * (th + 10)
        sc.save()
        sc.translate(x, y)
        sc.scale(tw / W, th / H)
        sc.set_source_surface(s, 0, 0)
        sc.paint()
        sc.restore()
        sc.select_font_face('Segoe UI', cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        sc.set_font_size(22)
        sc.move_to(x + 8, y + th - 10)
        sc.set_source_rgb(1, 0, 0)
        sc.show_text('%.1fs' % t)
    path = os.path.join(ROOT, 'output', 'night_meow_stills.png')
    sheet.write_to_png(path)
    print(path)


def _frame_bytes(i):
    s = frame(i / FPS)
    s.flush()
    return bytes(s.get_data())


def video(path, workers=4):
    """Frames are independent, so they render in a small process pool (the PC is shared:
    keep `workers` modest), piped in order into one ffmpeg."""
    from multiprocessing import Pool
    n = int(DUR * FPS)
    cmd = ['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgra', '-s', '%dx%d' % (W, H),
           '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p',
           '-movflags', '+faststart', path]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool(workers) as pool:
        for i, data in enumerate(pool.imap(_frame_bytes, range(n), chunksize=2)):
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
        video(sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, 'output', 'night_meow_silent.mp4'))
