"""Sheet for the animated girl (lib/girl2.py) next to the master reference.
Usage: python tools/make_girl2_sheet.py -> characters/girl/girl2_sheet.png"""
import os
import sys

import cairo
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'lib'))
import girl2 as G  # noqa: E402

W, H = 2600, 1500
s = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
c = cairo.Context(s)
c.set_source_rgb(0.93, 0.92, 0.9)
c.paint()
items = [(G.pose_stand(), 'neutral'), (G.pose_sit(), 'bored'), (G.pose_sit(), 'surprised'),
         (G.pose_sit(), 'annoyed'), (dict(G.pose_sit(), hands2='face', mix=1.0), 'sigh'),
         (G.pose_stand(), 'happy')]
for i, (p, f) in enumerate(items):
    G.draw_girl(c, 640 + i * 330, 1430, 1.0 if i == 0 else 0.92, p, f)
s.write_to_png(os.path.join(ROOT, 'output', '_g2sheet.png'))
sheet = Image.open(os.path.join(ROOT, 'output', '_g2sheet.png')).convert('RGB')
ref = Image.open(os.path.join(ROOT, 'characters', 'girl', 'images', 'cut', 'stand_front.png'))
bg = Image.new('RGB', ref.size, (236, 234, 230))
bg.paste(ref, (0, 0), ref)
sheet.paste(bg.resize((int(ref.width * 1185 / ref.height * 1.0), 1185)), (60, 245))
out = os.path.join(ROOT, 'characters', 'girl', 'girl2_sheet.png')
sheet.save(out)
print(out)
