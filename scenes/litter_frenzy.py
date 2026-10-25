"""Litter frenzy: the cat goes possessed in a fresh litter box and digs it empty.

Premise adapted from a genre reference (research/reference-equmiart-channel.md); our cat,
our room, our caption, our ending.

Usage:
  python scenes/litter_frenzy.py stills            -> output/litter_frenzy_stills.png (+ frames)
  python scenes/litter_frenzy.py video [out.mp4]   -> silent 1080x1920 30 fps render
"""
import math
import os
import subprocess
import sys

import cairo
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'lib'))
import cat  # noqa: E402

W, H = 1080, 1920
FPS = 30
DUR = 17.5
DRAW_FPS = 12                     # the cat is posed "on twos-ish": limited animation

WALL = cat.rgb('#efe9df')
FLOOR = cat.rgb('#cfd3da')
BOX = cat.rgb('#f2541b')
BOX_IN = cat.rgb('#b93d12')
SAND = cat.rgb('#e7d2a2')
SAND_D = cat.rgb('#cdb27a')
YELLOW = cat.YELLOW
INK = cat.INK

CAPTION = ['5 seconds after I', 'change the litter:']

# world layout (zoom 1 = canvas px)
FLOOR_Y = 1180
BACK_Y, FRONT_Y, BOTTOM_Y = 1250, 1420, 1545
BACK_X = (250, 830)
FRONT_X = (170, 910)
CAT_X, CAT_Y, CAT_H = 545, 1440, 290

# shots: (start, name)
SHOTS = [(0.0, 'face'), (1.8, 'stretch'), (4.6, 'turn'), (6.6, 'stiff'), (10.0, 'crouch'),
         (11.0, 'dig'), (14.5, 'flash'), (14.65, 'after')]
DIG0, DIG1 = 11.0, 14.5


def shot_at(t):
    cur = SHOTS[0]
    for s in SHOTS:
        if t >= s[0]:
            cur = s
    return cur


def ease(x):
    x = max(0.0, min(1.0, x))
    return x * x * (3 - 2 * x)


def rng_at(t, salt=0, step=1 / 12):
    return np.random.default_rng(int(t / step) * 7919 + salt)


# ------------------------------------------------------------------ camera

class Cam:
    def __init__(self, zoom, cx, cy, dx=0.0, dy=0.0):
        self.z, self.cx, self.cy, self.dx, self.dy = zoom, cx, cy, dx, dy

    def p(self, x, y):
        return ((x - self.cx) * self.z + W / 2 + self.dx, (y - self.cy) * self.z + H / 2 + self.dy)

    def apply(self, ctx):
        ctx.translate(W / 2 + self.dx, H / 2 + self.dy)
        ctx.scale(self.z, self.z)
        ctx.translate(-self.cx, -self.cy)


def camera(t):
    name = shot_at(t)[1]
    if name == 'face':
        return Cam(1.0 + 0.06 * ease(t / 1.8), 540, 1000)
    if name in ('stretch', 'turn'):
        return Cam(1.28 + 0.08 * ease((t - 1.8) / 4.8), 545, 990)
    if name == 'stiff':
        r = rng_at(t, 3, 1 / 30)
        return Cam(1.36, 545, 975, *(r.normal(0, 3, 2)))
    if name == 'crouch':
        return Cam(1.36 + 0.16 * ease((t - 10.0) / 0.5), 545, 1000 + 40 * ease((t - 10.0) / 0.5))
    if name == 'dig':
        r = rng_at(t, 5, 1 / 30)
        return Cam(1.52, 545, 1040, *(r.normal(0, 7, 2)))
    return Cam(1.15, 545, 1010)


# ------------------------------------------------------------------ the room and the box

def splats(ctx):
    r = np.random.default_rng(4)
    for col, (cx, cy) in [(cat.PINK, (150, 520)), (cat.YELLOW, (930, 380)), (cat.BLUE, (880, 760)),
                          (cat.PINK, (980, 1030)), (cat.YELLOW, (120, 900))]:
        ctx.set_source_rgba(*col, 0.32)
        for _ in range(22):
            rr = r.uniform(3, 34) * r.random()
            ctx.arc(cx + r.normal(0, 60), cy + r.normal(0, 60), rr, 0, 2 * math.pi)
            ctx.fill()
        for _ in range(2):
            x = cx + r.uniform(-40, 40)
            w = r.uniform(4, 8)
            L = r.uniform(50, 160)
            ctx.rectangle(x - w / 2, cy, w, L)
            ctx.arc(x, cy + L, w * 0.8, 0, 2 * math.pi)
            ctx.fill()


def room(ctx):
    ctx.rectangle(-2000, -2000, 5000, FLOOR_Y + 2000)
    ctx.set_source_rgb(*WALL)
    ctx.fill()
    splats(ctx)
    ctx.rectangle(-2000, FLOOR_Y, 5000, 3000)
    ctx.set_source_rgb(*FLOOR)
    ctx.fill()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(5)
    ctx.move_to(-2000, FLOOR_Y)
    ctx.line_to(3000, FLOOR_Y)
    ctx.stroke()


def box_back(ctx, level):
    """Inner back wall, sand surface at `level` (1 full, 0 empty)."""
    (bl, br), (fl, fr) = BACK_X, FRONT_X
    ctx.move_to(bl, BACK_Y)
    ctx.line_to(br, BACK_Y)
    ctx.line_to(fr, FRONT_Y)
    ctx.line_to(fl, FRONT_Y)
    ctx.close_path()
    ctx.set_source_rgb(*BOX_IN)
    ctx.fill()
    # sand: its back edge drops toward the front as the box empties
    sy = BACK_Y + 12 + (1 - level) * 120
    if level > 0.02:
        ctx.move_to(bl + 8, sy)
        ctx.curve_to(450, sy - 10 * level, 640, sy + 8 * level, br - 8, sy)
        ctx.line_to(fr - 10, FRONT_Y)
        ctx.line_to(fl + 10, FRONT_Y)
        ctx.close_path()
        ctx.set_source_rgb(*SAND)
        ctx.fill()
        r = np.random.default_rng(9)
        ctx.set_source_rgb(*SAND_D)
        for _ in range(int(70 * level)):
            x = r.uniform(fl + 40, fr - 40)
            y = r.uniform(sy + 15, FRONT_Y - 5)
            ctx.arc(x, y, r.uniform(2, 5), 0, 2 * math.pi)
            ctx.fill()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(6)
    ctx.move_to(bl, BACK_Y)
    ctx.line_to(br, BACK_Y)
    ctx.stroke()


def box_front(ctx):
    (bl, br), (fl, fr) = BACK_X, FRONT_X
    ctx.move_to(fl, FRONT_Y)
    ctx.line_to(fr, FRONT_Y)
    ctx.line_to(fr - 22, BOTTOM_Y)
    ctx.line_to(fl + 22, BOTTOM_Y)
    ctx.close_path()
    ctx.set_source_rgb(*BOX)
    ctx.fill_preserve()
    ctx.set_source_rgb(*INK)
    ctx.set_line_width(6)
    ctx.set_line_join(cairo.LINE_JOIN_ROUND)
    ctx.stroke()
    for (a, b) in [((bl, BACK_Y), (fl, FRONT_Y)), ((br, BACK_Y), (fr, FRONT_Y))]:
        ctx.move_to(*a)
        ctx.line_to(*b)
    ctx.stroke()
    ctx.set_source_rgba(1, 1, 1, 0.35)          # rim highlight
    ctx.set_line_width(5)
    ctx.move_to(fl + 20, FRONT_Y + 12)
    ctx.line_to(fr - 20, FRONT_Y + 12)
    ctx.stroke()
    ctx.set_source_rgba(0, 0, 0, 0.10)          # contact shadow
    ctx.save()
    ctx.translate(540, BOTTOM_Y + 8)
    ctx.scale(400, 18)
    ctx.arc(0, 0, 1, 0, 2 * math.pi)
    ctx.restore()
    ctx.fill()


# ------------------------------------------------------------------ sand flying out

N_SAND = 520


def _particles():
    r = np.random.default_rng(21)
    P = []
    for i in range(N_SAND):
        t0 = DIG0 + 0.15 + (DIG1 - DIG0 - 0.35) * i / N_SAND + r.uniform(-0.02, 0.02)
        side = -1 if r.random() < 0.5 else 1
        x0 = CAT_X + side * r.uniform(20, 90)
        y0 = CAT_Y - 0.25 * CAT_H
        vx = side * r.uniform(250, 950)
        vy = -r.uniform(700, 1500)
        land = r.uniform(1460, 1880) if r.random() < 0.8 else r.uniform(1200, 1440)
        P.append((t0, x0, y0, vx, vy, land, r.uniform(5, 11), r.random() < 0.3))
    return P


PARTICLES = _particles()
G = 3000.0


def sand(ctx, t, landed_only=False):
    for (t0, x0, y0, vx, vy, land, rad, dark) in PARTICLES:
        if t < t0:
            continue
        dt = t - t0
        # time to land: y0 + vy*dt + G/2 dt^2 = land
        a, b, c = G / 2, vy, y0 - land
        if b * b - 4 * a * c < 0:                # too high to reach: lands just below its start
            land = y0 + 60
            c = y0 - land
        tl = (-b + math.sqrt(b * b - 4 * a * c)) / (2 * a)
        if dt >= tl:
            x, y = x0 + vx * tl, land
            if FRONT_X[0] + 30 < x < FRONT_X[1] - 30 and land < BOTTOM_Y + 10:
                continue                         # fell back into the box
            ctx.save()
            ctx.translate(x, y)
            ctx.scale(1.4, 0.7)
            ctx.arc(0, 0, rad, 0, 2 * math.pi)
            ctx.restore()
        elif not landed_only:
            ctx.arc(x0 + vx * dt, y0 + vy * dt + G / 2 * dt * dt, rad * 0.8, 0, 2 * math.pi)
        else:
            continue
        ctx.set_source_rgb(*(SAND_D if dark else SAND))
        ctx.fill()


def piles(ctx, k):
    """Heaps on the floor, grown by k (0..1)."""
    if k <= 0:
        return
    for (cx, w, h) in [(120, 230, 120), (965, 250, 135), (330, 200, 70), (760, 220, 80), (560, 160, 40)]:
        base = BOTTOM_Y + 110 if cx in (330, 760, 560) else BOTTOM_Y + 30
        hh = h * k
        ctx.move_to(cx - w * (0.6 + 0.4 * k), base)
        ctx.curve_to(cx - w * 0.4, base - hh * 0.9, cx - w * 0.15, base - hh, cx, base - hh)
        ctx.curve_to(cx + w * 0.15, base - hh, cx + w * 0.4, base - hh * 0.9, cx + w * (0.6 + 0.4 * k), base)
        ctx.close_path()
        ctx.set_source_rgb(*SAND)
        ctx.fill_preserve()
        ctx.set_source_rgb(*INK)
        ctx.set_line_width(4)
        ctx.stroke()


# ------------------------------------------------------------------ effects

def speed_lines(ctx, t, cx, cy):
    r = rng_at(t, 11, 1 / 15)
    ctx.set_source_rgba(*INK, 0.85)
    for _ in range(70):
        a = r.uniform(0, 2 * math.pi)
        r0 = r.uniform(430, 620)
        r1 = r0 + r.uniform(400, 900)
        w = r.uniform(3, 10)
        ca, sa = math.cos(a), math.sin(a)
        ctx.move_to(cx + ca * r0, cy + sa * r0)
        ctx.line_to(cx + ca * r1 - sa * w, cy + sa * r1 + ca * w)
        ctx.line_to(cx + ca * r1 + sa * w, cy + sa * r1 - ca * w)
        ctx.close_path()
        ctx.fill()


def zaps(ctx, t, cx, cy, spread):
    r = rng_at(t, 13, 1 / 10)
    for _ in range(7):
        a = r.uniform(-math.pi, 0.2)
        d = spread * r.uniform(0.75, 1.1)
        x, y = cx + math.cos(a) * d * 0.8, cy + math.sin(a) * d
        pts = [(x, y)]
        ang = a + r.uniform(-0.6, 0.6)
        for k in range(4):
            step = r.uniform(22, 38)
            off = (-1) ** k * r.uniform(12, 22)
            x += math.cos(ang) * step - math.sin(ang) * off
            y += math.sin(ang) * step + math.cos(ang) * off
            pts.append((x, y))
        for col, wd in [(INK, 11), (YELLOW, 6)]:
            ctx.move_to(*pts[0])
            for p in pts[1:]:
                ctx.line_to(*p)
            ctx.set_source_rgb(*col)
            ctx.set_line_width(wd)
            ctx.set_line_cap(cairo.LINE_CAP_ROUND)
            ctx.set_line_join(cairo.LINE_JOIN_ROUND)
            ctx.stroke()


def sparkle(ctx, x, y, s):
    ctx.move_to(x, y - s)
    for k in range(4):
        a = math.pi / 2 * (k + 1)
        ctx.curve_to(x, y, x, y, x + math.sin(a) * s, y - math.cos(a) * s)
    ctx.close_path()
    ctx.set_source_rgb(*INK)
    ctx.fill()


def caption(ctx):
    ctx.select_font_face('Segoe Print', cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(58)
    exts = [ctx.text_extents(s) for s in CAPTION]
    w = max(e.x_advance for e in exts) + 70
    h = 78 * len(CAPTION) + 44
    ctx.save()
    ctx.translate(W / 2, 250)
    ctx.rotate(math.radians(-2.0))
    ctx.rectangle(-w / 2 + 8, -h / 2 + 10, w, h)       # paper strip with a drop shadow
    ctx.set_source_rgba(0, 0, 0, 0.18)
    ctx.fill()
    ctx.rectangle(-w / 2, -h / 2, w, h)
    ctx.set_source_rgb(1, 1, 1)
    ctx.fill()
    for k, (s, e) in enumerate(zip(CAPTION, exts)):
        ctx.move_to(-e.x_advance / 2, -h / 2 + 22 + 58 + k * 78)
        ctx.set_source_rgb(*INK)
        ctx.show_text(s)
    for sx in (-1, 1):                                   # two bits of tape
        ctx.save()
        ctx.translate(sx * (w / 2 - 30), -h / 2)
        ctx.rotate(sx * 0.5)
        ctx.rectangle(-45, -16, 90, 32)
        ctx.set_source_rgba(*cat.rgb('#f5d327'), 0.75)
        ctx.fill()
        ctx.restore()
    ctx.restore()


# ------------------------------------------------------------------ the cat over time

def cat_state(t):
    """(pose, face, yaw, ox, oy, H) in world coords for time t (posed at DRAW_FPS)."""
    tq = math.floor(t * DRAW_FPS) / DRAW_FPS
    name = shot_at(t)[1]
    sway = math.sin(tq * 2.2)
    if name == 'face':
        f = dict(cat.FACES['deadpan'])
        if 1.15 < tq < 1.30:
            f = dict(eyes='closed', mouth='flat')
        return cat.pose_bust(head_roll=2 * sway), f, 0, 540, 1960, 620
    if name == 'stretch':
        p = cat.pose_stretch_splay(head_turn=30, head_roll=3 * sway)
        p['tail'] = [(x + 0.06 * sway * k, y, z) for k, (x, y, z) in enumerate(p['tail'])]
        return p, 'deadpan', -32, CAT_X, CAT_Y, CAT_H
    if name == 'turn':
        k = ease((tq - 4.9) / 0.5)
        p = cat.pose_stretch_splay(rise=0.6 * ease((tq - 5.0) / 1.2), head_turn=30)
        p['tail_puff'] = ease((tq - 5.0) / 0.35)
        if tq < 4.9:
            f = 'deadpan'
        else:
            f = dict(eyes='blank', open=0.45 - 0.05 * k, slant=0.0,
                     mouth='gasp' if tq > 5.7 else 'flat')
        return p, f, -32, CAT_X, CAT_Y, CAT_H
    if name == 'stiff':
        p = cat.pose_stiff(head_turn=26, head_roll=4 * math.sin(tq * 9), shake=0.02 * math.sin(tq * 31))
        p['tail_puff'] = 1.0
        return p, 'possessed', -30, CAT_X, CAT_Y, CAT_H
    if name == 'crouch':
        p = cat.pose_dig(0.0, head_turn=28)
        p['tail_puff'] = 1.0
        return p, 'possessed', -30, CAT_X, CAT_Y, CAT_H
    if name == 'dig':
        p = cat.pose_dig(((tq - DIG0) * 4.0) % 1.0, head_turn=28, head_roll=5 * math.sin(tq * 20))
        p['tail_puff'] = 1.0
        return p, 'frenzy', -30, CAT_X, CAT_Y, CAT_H
    # after
    f = dict(cat.FACES['proud'])
    if 16.3 < tq < 16.5:
        f = dict(eyes='closed', mouth='smile')
    p = cat.pose_sit(head_turn=22, head_roll=-4)
    p['tail'] = [(x, y + 0.03 * math.sin(tq * 3 + k), z) for k, (x, y, z) in enumerate(p['tail'])]
    return p, f, -22, CAT_X, CAT_Y + 10, CAT_H


def sand_level(t):
    if t < DIG0 + 0.1:
        return 1.0
    if t < DIG1:
        return 1.0 - 0.95 * (t - DIG0) / (DIG1 - DIG0)
    return 0.0


# ------------------------------------------------------------------ frame

def frame(t):
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    name = shot_at(t)[1]
    if name == 'flash':
        ctx.set_source_rgb(1, 1, 1)
        ctx.paint()
        return surf
    cam = camera(t)
    ctx.save()
    cam.apply(ctx)
    room(ctx)
    if name != 'face':
        if name == 'after':
            piles(ctx, 1.0)
            sand(ctx, DIG1 + 2, landed_only=True)
        elif name == 'dig':
            piles(ctx, ease((t - DIG0 - 0.6) / (DIG1 - DIG0 - 0.6)))
        box_back(ctx, sand_level(t))
    ctx.restore()

    if name == 'dig':
        speed_lines(ctx, t, *cam.p(CAT_X, CAT_Y - 0.7 * CAT_H))

    pose, face, yaw, ox, oy, h = cat_state(t)
    if name == 'face':
        sx, sy = cam.p(ox, oy)
        cat.draw_cat(surf, pose, sx, sy, h * cam.z, yaw=yaw, face=face, shadow=False)
    else:
        sx, sy = cam.p(ox, oy)
        cat.draw_cat(surf, pose, sx, sy, h * cam.z, yaw=yaw, face=face, shadow=False)

    ctx = cairo.Context(surf)
    ctx.save()
    cam.apply(ctx)
    if name != 'face':
        if name == 'dig':
            sand(ctx, t)
        box_front(ctx)
    ctx.restore()
    if name == 'stiff':
        zaps(ctx, t, *cam.p(CAT_X - 20, CAT_Y - 1.5 * CAT_H), 1.25 * CAT_H * cam.z)
    if name == 'after':
        for (x, y, s, ph) in [(CAT_X - 250, CAT_Y - 1.75 * CAT_H, 26, 0.0), (CAT_X + 230, CAT_Y - 2.0 * CAT_H, 18, 0.7)]:
            k = 0.6 + 0.4 * math.sin(t * 5 + ph)
            sparkle(ctx, *cam.p(x, y), s * k * cam.z)
    caption(ctx)
    return surf


# ------------------------------------------------------------------ outputs

STILL_TIMES = [0.9, 3.0, 5.9, 8.2, 10.6, 12.7, 16.0]


def stills():
    out = os.path.join(ROOT, 'output', 'litter_frenzy')
    os.makedirs(out, exist_ok=True)
    tw, th = 360, 640
    sheet = cairo.ImageSurface(cairo.FORMAT_ARGB32, tw * 4 + 50, th * 2 + 30)
    sc = cairo.Context(sheet)
    sc.set_source_rgb(1, 1, 1)
    sc.paint()
    for i, t in enumerate(STILL_TIMES):
        s = frame(t)
        s.write_to_png(os.path.join(out, 'still_%04.1fs.png' % t))
        x, y = 10 + (i % 4) * (tw + 10), 10 + (i // 4) * (th + 10)
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
    path = os.path.join(ROOT, 'output', 'litter_frenzy_stills.png')
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
        video(sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, 'output', 'litter_frenzy_silent.mp4'))
