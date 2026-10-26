"""Sound for bathroom_alone: our own synthesised effects (lib/sfx.py), no music.

Usage: python scenes/bathroom_alone_audio.py <silent.mp4> <out.mp4>
"""
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'lib'))
sys.path.insert(0, os.path.join(ROOT, 'scenes'))
import sfx  # noqa: E402
import bathroom_alone as V  # noqa: E402
from litter_frenzy_audio import master, measure, mux  # noqa: E402


def creak(dur=0.5):
    t = np.arange(int(dur * sfx.SR)) / sfx.SR
    f = 180 + 90 * np.sin(2 * np.pi * 3 * t) + 60 * t / dur
    x = np.sign(np.sin(2 * np.pi * np.cumsum(f) / sfx.SR)) * (0.5 + 0.5 * np.sin(2 * np.pi * 23 * t))
    return sfx.norm(sfx.band(x, 300, 3000) * np.sin(np.pi * t / dur))


def build():
    m = sfx.Mix(V.DUR)
    m.add(sfx.room_tone(V.DUR), 0, db=-34)
    m.add(sfx.paper_slap(), 0.0, db=-10)
    for k, t in enumerate((0.25, 0.42, 0.95, 1.12, 2.05, 2.22)):      # paw scratching the door
        m.add(sfx.scratch(seed=k), t, db=-9, pan=0.45)
    for t in (0.6, 1.55):
        m.add(sfx.meow(0.42, f0=(460, 700, 480), vowels='iau', seed=int(t * 10)), t, db=-7, pan=0.45)
    m.add(creak(0.5), V.T_OPEN0, db=-12)
    for i, c in enumerate(V.CUTS):                                    # the cat pops up somewhere new
        m.add(sfx.plink(1800 + 250 * i), c, db=-14)
        m.add(sfx.thump(0.14), c + 0.04, db=-16)
    m.add(sfx.purr(1.2), V.CUTS[2] + 0.1, db=-16)
    m.add(sfx.gasp(0.4), V.CUTS[3] + 0.3, db=-18)                     # her sigh
    m.add(sfx.meow(0.45, f0=(520, 760, 500), vowels='iau', seed=21), V.CUTS[4] + 0.5, db=-7, pan=0.5)
    m.add(sfx.whoosh(0.3), V.T_BACK - 0.1, db=-14)
    m.add(sfx.thump(0.25), V.T_BACK, db=-10)                          # the door shuts
    m.add(sfx.meow(0.5, f0=(480, 800, 520), vowels='iau', seed=33), V.T_BACK + 0.35, db=-5, pan=0.45)
    return m.render()


def main(silent, out):
    import soundfile as sf
    x = master(build())
    wav = os.path.join(ROOT, 'sound', 'bathroom_alone_sfx.wav')
    sf.write(wav, x, sfx.SR, subtype='FLOAT')
    mux(silent, wav, out)
    print(measure(out), out)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
