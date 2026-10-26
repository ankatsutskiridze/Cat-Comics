"""Sound for never_alone: our own synthesised effects (lib/sfx.py), no music, timed to
scenes/never_alone.py, mastered to -14 LUFS and muxed onto the silent render.

Usage: python scenes/never_alone_audio.py <silent.mp4> <out.mp4>
"""
import os
import sys

import numpy as np
import soundfile as sf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'lib'))
sys.path.insert(0, os.path.join(ROOT, 'scenes'))
import sfx  # noqa: E402
import never_alone as V  # noqa: E402
from litter_frenzy_audio import TARGET_LUFS, master, measure, mux  # noqa: E402


def jump(m, t0, t1, land_db=-12, pan=0.0):
    m.add(sfx.whoosh(t1 - t0 + 0.1), t0 - 0.05, db=-18, pan=pan)
    m.add(sfx.thump(0.16), t1, db=land_db, pan=pan)


def build():
    m = sfx.Mix(V.DUR)
    m.add(sfx.room_tone(V.DUR), 0.0, db=-34)
    for c in V.CUTS:                                             # each caption lands
        m.add(sfx.paper_slap(), c, db=-13)
    # 1. typing: a key click per tap, until the cat lands on the keys
    c1 = V.CUTS[0]
    rnd = np.random.default_rng(1)
    t = 0.05
    while t < V.J1[1]:
        m.add(sfx.tick(rnd.uniform(2400, 3600)), c1 + t, db=-22 + rnd.uniform(-3, 2), pan=-0.1)
        t += rnd.uniform(0.07, 0.13)
    jump(m, c1 + V.J1[0], c1 + V.J1[1], pan=0.2)
    m.add(sfx.crackle(0.35, density=160, seed=2), c1 + V.J1[1] + 0.01, db=-14, pan=0.1)   # keys mashed
    m.add(sfx.gasp(0.3), c1 + V.J1[1] + 0.05, db=-18, pan=-0.2)
    m.add(sfx.gasp(0.6), c1 + V.SIGH1, db=-14, pan=-0.2)                                 # the sigh
    # 2. crunches: the mat rustles each rep; the landing; her strain; the purr
    c2 = V.CUTS[1]
    for k in range(2):
        m.add(sfx.rustle(0.3, seed=20 + k), c2 + k * V.CRUNCH_T + 0.3, db=-22)
    jump(m, c2 + V.J2[0], c2 + V.J2[1], land_db=-9, pan=-0.1)
    m.add(sfx.gasp(0.25), c2 + V.J2[1] + 0.02, db=-12)                                   # oof
    m.add(sfx.gasp(0.45), c2 + V.TRY[0], db=-17)
    m.add(sfx.purr(1.6), c2 + V.J2[1] + 0.7, db=-10, pan=-0.1)
    # 3. brushing: short scrub bursts; the jump into the sink; the meow
    c3 = V.CUTS[2]
    t = 0.0
    while t < V.J3[1]:
        m.add(sfx.sand_hiss(0.1, seed=int(t * 100)), c3 + t, db=-24, pan=-0.2)
        t += 1 / 8.4
    jump(m, c3 + V.J3[0], c3 + V.J3[1], land_db=-11, pan=0.3)
    m.add(sfx.plink(900), c3 + V.J3[1] + 0.02, db=-20, pan=0.3)                          # porcelain
    a, d = V.MEOW3
    m.add(sfx.meow(d, f0=(560, 860, 480), vowels='iau', seed=7), c3 + a, db=-6, pan=0.3)
    # 4. the cuddle: bubble pops; it jumps to the shelf; her arms sink; the last line
    c4 = V.CUTS[3]
    m.add(sfx.plink(1800), c4 + V.ASK[0], db=-20, pan=-0.2)
    m.add(sfx.plink(2600), c4 + V.AWAY, db=-24, pan=0.3)                                 # it looks away
    jump(m, c4 + V.J4[0], c4 + V.J4[1], land_db=-14, pan=0.35)
    m.add(sfx.slide_whistle(700, 330, V.DROP[1] - V.DROP[0] + 0.2), c4 + V.DROP[0], db=-20)
    m.add(sfx.plink(1500), c4 + V.SAY4[0], db=-20, pan=-0.2)
    return m.render()


def main(silent, out):
    x = master(build())
    wav = os.path.join(ROOT, 'sound', 'never_alone_sfx.wav')
    for attempt in range(3):
        sf.write(wav, x, sfx.SR, subtype='FLOAT')
        mux(silent, wav, out)
        lufs, peak = measure(out)
        print('attempt %d: %.2f LUFS, peak %.2f dBFS' % (attempt, lufs, peak))
        if abs(lufs - TARGET_LUFS) <= 0.3 and peak < -1.0:
            break
        x = x * 10 ** ((TARGET_LUFS - lufs) / 20)
        if peak - (TARGET_LUFS - lufs) >= -1.0:
            x = x * 10 ** ((-1.2 - peak) / 20)
    print(out)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
