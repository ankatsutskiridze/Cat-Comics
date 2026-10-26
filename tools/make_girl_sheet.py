"""Character sheet for the girl (lib/girl.py) -> characters/girl/girl_sheet_v<N>.png

Usage: python tools/make_girl_sheet.py [version]
"""
import math
import os
import sys

import cairo

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'lib'))
import girl  # noqa: E402

W, H = 2400, 2600
PAPER = girl.rgb('#ebe8e3')
FONT = 'Segoe Print'


def label(ctx, x, y, text, size=44, center=False, underline=True):
    ctx.select_font_face(FONT, cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
    ctx.set_font_size(size)
    e = ctx.text_extents(text)
    if center:
        x -= e.width / 2
    ctx.move_to(x, y)
    ctx.set_source_rgb(*girl.LINE)
    ctx.show_text(text)
    if underline:
        ctx.set_line_width(3)
        ctx.move_to(x, y + 13)
        ctx.curve_to(x + e.width * 0.3, y + 19, x + e.width * 0.7, y + 8, x + e.width + 8, y + 15)
        ctx.stroke()


def bust(ctx, x, y, w, h, face, yaw=20, turn=0, tilt=0, figure_h=1500):
    """A head-and-shoulders crop: the figure drawn big, clipped to a box."""
    ctx.save()
    ctx.rectangle(x, y, w, h)
    ctx.clip()
    eye_y = y + h * 0.60
    girl.draw_girl(ctx, x + w / 2, eye_y + girl.EYE_Y * figure_h, figure_h,
                   girl.pose_stand(head_turn=turn, head_tilt=tilt), face, yaw)
    ctx.restore()


def main(version):
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(surf)
    ctx.set_source_rgb(*PAPER)
    ctx.paint()
    label(ctx, 60, 90, 'the girl  -  character sheet v%d' % version, 50)

    # hero, 3/4 to the right, smiling
    girl.draw_girl(ctx, 380, 1640, 1480, girl.pose_stand(head_turn=-8), 'smile', 22)
    _ellipse_shadow(ctx, 380, 1645, 230, 26)

    # expressions
    label(ctx, 820, 200, 'Expressions')
    names = ['smile', 'look', 'laugh', 'bored', 'surprised', 'grumpy']
    bw, bh = 500, 430
    for i, n in enumerate(names):
        x = 820 + (i % 3) * (bw + 20)
        y = 240 + (i // 3) * (bh + 70)
        bust(ctx, x, y, bw, bh, n, yaw=12 if i % 2 else -10, figure_h=1350)
        label(ctx, x + bw / 2, y + bh + 45, n, 32, center=True, underline=False)

    # for the night video
    label(ctx, 820, 1260, 'Night video')
    for i, n in enumerate(['sleep', 'tired', 'annoyed', 'angry']):
        x = 820 + i * 385
        bust(ctx, x, 1300, 365, 330, n, yaw=0, figure_h=1050)
        label(ctx, x + 182, 1680, n, 32, center=True, underline=False)

    # turnaround
    label(ctx, 60, 1800, 'Turnaround')
    for x, yaw, n in [(330, 0, 'front'), (860, 90, 'side'), (1390, 180, 'back'), (1920, 40, '3/4')]:
        girl.draw_girl(ctx, x, 2450, 600, girl.pose_stand(), 'smile', yaw)
        _ellipse_shadow(ctx, x, 2452, 95, 12)
        label(ctx, x, 2540, n, 34, center=True, underline=False)

    # palette
    for i, c in enumerate(girl.PALETTE):
        ctx.new_path()
        ctx.arc(2300, 300 + i * 95, 36, 0, 2 * math.pi)
        ctx.set_source_rgb(*c)
        ctx.fill_preserve()
        ctx.set_source_rgb(*girl.LINE)
        ctx.set_line_width(2)
        ctx.stroke()

    out = os.path.join(ROOT, 'characters', 'girl', 'girl_sheet_v%d.png' % version)
    surf.write_to_png(out)
    print(out)


def _ellipse_shadow(ctx, x, y, rx, ry):
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(rx, ry)
    ctx.arc(0, 0, 1, 0, 2 * math.pi)
    ctx.restore()
    ctx.set_source_rgba(0, 0, 0, 0.06)
    ctx.fill()


if __name__ == '__main__':
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 1)
