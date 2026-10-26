"""Character sheet for the cat (lib/cat.py) -> characters/cat/cat_sheet_v<N>.png

Usage: python tools/make_cat_sheet.py [version]
"""
import math
import os
import random
import sys

import cairo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'lib'))
import cat2 as cat  # noqa: E402

W, H = 2400, 3400
PAPER = cat.rgb('#efebe4')
FONT = 'Segoe Print'


def label(ctx, x, y, text, size=46, underline=True, center=False):
    ctx.select_font_face(FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(size)
    ext = ctx.text_extents(text)
    if center:
        x -= ext.width / 2
    ctx.move_to(x, y)
    ctx.set_source_rgb(*cat.INK)
    ctx.show_text(text)
    if underline:
        ctx.set_line_width(3)
        ctx.move_to(x, y + 14)
        ctx.curve_to(x + ext.width * 0.3, y + 20, x + ext.width * 0.7, y + 8, x + ext.width + 10, y + 16)
        ctx.stroke()


def splatter(ctx, x0, y0, x1, y1, seed=3):
    rnd = random.Random(seed)
    for col in (cat.PINK, cat.YELLOW, cat.BLUE, cat.YELLOW, cat.PINK, cat.ORANGE):
        cx, cy = rnd.uniform(x0, x1), rnd.uniform(y0, y1)
        ctx.set_source_rgba(*col, 0.55)
        for _ in range(26):
            r = rnd.uniform(4, 48) * rnd.random()
            ctx.arc(cx + rnd.gauss(0, 85), cy + rnd.gauss(0, 85), r, 0, 2 * math.pi)
            ctx.fill()
        for _ in range(3):                                   # drips
            dx = cx + rnd.uniform(-70, 70)
            w = rnd.uniform(5, 11)
            L = rnd.uniform(60, 220)
            ctx.rectangle(dx - w / 2, cy, w, L)
            ctx.fill()
            ctx.arc(dx, cy + L, w * 0.8, 0, 2 * math.pi)
            ctx.fill()


def panel(ctx, x, y, w, h):
    ctx.rectangle(x, y, w, h)
    ctx.set_source_rgb(*cat.rgb('#dedad3'))
    ctx.fill()


HEAD_ONLY = dict(torso=[], neck=[], legs=[], paws=[], tail=[], head=(0, 0, 0))


def main(version):
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    ctx.set_source_rgb(*PAPER)
    ctx.paint()

    # hero
    cat.draw_cat(surf, cat.pose_sit(), 620, 1430, 440, face='smug')
    label(ctx, 70, 120, 'the cat  -  character sheet v%d' % version, 54)

    # close-up
    px, py, pw, ph = 1230, 90, 1110, 700
    panel(ctx, px, py, pw, ph)
    sub = cairo.ImageSurface(cairo.FORMAT_ARGB32, pw, ph)
    cat.draw_cat(sub, cat.pose_bust(), pw / 2, 470 + 1.40 * 480, 480, face='smug', shadow=False)
    ctx.set_source_surface(sub, px, py)
    ctx.paint()

    # expressions
    label(ctx, 1230, 875, 'Expressions')
    names = ['smug', 'deadpan', 'surprised', 'sleepy', 'angry', 'silly', 'confused', 'love']
    for i, n in enumerate(names):
        cx = 1230 + 140 + (i % 4) * 277
        cy = 1060 + (i // 4) * 300
        cat.draw_cat(surf, HEAD_ONLY, cx, cy, 160, face=n, shadow=False)
        label(ctx, cx, cy + 135, n, 30, underline=False, center=True)

    # turnaround
    label(ctx, 70, 1590, 'Turnaround')
    for x, yaw, n in [(330, 0, 'front'), (900, 40, '3/4'), (1500, 90, 'side'), (2100, 180, 'back')]:
        cat.draw_cat(surf, cat.pose_stand(), x, 2330, 255, yaw=yaw, face='smug')
        label(ctx, x, 2410, n, 34, underline=False, center=True)

    # in action
    label(ctx, 70, 2520, 'In action')
    gy = 3130
    cat.draw_cat(surf, cat.pose_sit(), 200, gy, 150, yaw=25, face='deadpan')
    cat.draw_cat(surf, cat.pose_loaf(), 540, gy, 150, yaw=30, face='sleepy')
    cat.draw_cat(surf, cat.pose_stand(step=0.8, head_turn=-35), 905, gy, 150, yaw=90, face='smug')
    cat.draw_cat(surf, cat.pose_bow(), 1300, gy, 150, yaw=65, face='silly')
    cat.draw_cat(surf, cat.pose_leap(), 1740, gy - 20, 150, yaw=90, face='surprised')
    cat.draw_cat(surf, cat.pose_sit(head_turn=-140, tail='ground', tail_side=-1), 2190, gy, 150, yaw=180, face='deadpan')
    for x, n in [(200, 'sit'), (540, 'loaf'), (905, 'walk'), (1300, 'stretch'), (1740, 'leap'),
                 (2190, 'look back')]:
        label(ctx, x, gy + 80, n, 30, underline=False, center=True)

    # colours
    label(ctx, 1500, 3320, 'Colors', 38)
    for i, c in enumerate([cat.INK, cat.EYE, cat.NOSE]):
        ctx.arc(1690 + i * 100, 3305, 34, 0, 2 * math.pi)
        ctx.set_source_rgb(*c)
        ctx.fill_preserve()
        ctx.set_source_rgb(*cat.INK)
        ctx.set_line_width(2)
        ctx.stroke()

    out = os.path.join(ROOT, 'characters', 'cat', 'cat2_sheet_v%d.png' % version)
    surf.write_to_png(out)
    print(out)


if __name__ == '__main__':
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 1)
