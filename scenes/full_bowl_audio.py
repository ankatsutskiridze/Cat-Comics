"""Sound for full_bowl: our own synthesised effects (lib/sfx.py), no music, timed to
scenes/full_bowl.py, mastered to -14 LUFS and muxed onto the silent render.

Usage: python scenes/full_bowl_audio.py <silent.mp4> <out.mp4>
"""
import math
import os
import sys

import numpy as np
import soundfile as sf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'lib'))
sys.path.insert(0, os.path.join(ROOT, 'scenes'))
import sfx  # noqa: E402
import full_bowl as V  # noqa: E402
from litter_frenzy_audio import TARGET_LUFS, master, measure, mux  # noqa: E402

# one voice per meow: pitch contour, vowels, level
VOICES = [((540, 820, 500), 'iau', -8), ((520, 860, 480), 'iaou', -7), ((580, 920, 520), 'iau', -6),
          ((470, 600, 430), 'eau', -5), ((480, 640, 420), 'eaou', -4)]


def build():
    m = sfx.Mix(V.DUR)
    m.add(sfx.room_tone(V.DUR), 0.0, db=-34)
    m.add(sfx.paper_slap(), 0.0, db=-12)                          # the caption lands
    for (a, d, _), (f0, vowels, db) in zip(V.MEOWS, VOICES):
        m.add(sfx.meow(d, f0=f0, vowels=vowels, seed=int(a * 10)), max(0.0, a), db=db, pan=0.25)
    # her footsteps: each foot plant of the walk
    prev, t = None, V.T_WALK
    while t < V.T_LOOK:
        k = math.floor(float(V.WALKER.ph[V.WALKER._i(t)]) * 2 + 0.2)
        if prev is not None and k != prev and V.WALKER.moving(t) > 0.25:
            x = V.WALKER.x(t) * V.GIRL_S
            m.add(sfx.thump(0.12), t, db=-18, pan=float(np.clip((x - 540) / 540, -1, 1)))
        prev = k
        t += 1 / 240
    m.add(sfx.plink(1700), V.SAY[0] - 0.05, db=-20)              # the bubble pops
    m.add(sfx.plink(2600), 7.0, db=-24, pan=0.25)                 # the slow stare-blink
    m.add(sfx.whoosh(0.3), V.CLOSE1[0] - 0.12, db=-16)            # cut to above
    m.add(sfx.impact(0.6), V.CLOSE1[0] + 0.85, db=-16)            # the arrow + caption land
    m.add(sfx.whoosh(0.3), V.CLOSE1[1] - 0.1, db=-18)
    m.add(sfx.gasp(0.5), V.T_SIGH + 0.05, db=-14)                 # her sigh
    m.add(sfx.thump(0.15), V.TAP_HIT, db=-10, pan=0.3)            # foot hits the bowl
    m.add(sfx.crackle(0.5, density=90, seed=3), V.TAP_HIT + 0.02, db=-12, pan=0.3)   # kibble rattles
    m.add(sfx.crackle(0.55, density=70, seed=5), V.CLOSE2[0] + 0.1, db=-14)          # it slides in
    for k in range(3):                                            # one bite: crunch crunch crunch
        m.add(sfx.crackle(0.09, density=200, seed=11 + k), V.EAT[0] + 0.2 + 0.13 * k, db=-10, pan=0.25)
    m.add(sfx.plink(3000), V.CLOSE3[0] + 0.2, db=-16)             # the spot is back
    m.add(sfx.gasp(0.5), V.SIGH2[0] + 0.05, db=-14)               # she gives up
    m.add(sfx.paper_slap(), V.SIGH2[1] + 0.05, db=-14)            # '...FINE.' lands
    m.add(sfx.rustle(0.4, seed=12), V.LIFT[0], db=-14)            # she takes the bag
    m.add(sfx.crackle(1.1, density=260, seed=8), V.POUR[0] + 0.15, db=-9)   # the pour
    m.add(sfx.sand_hiss(1.0, seed=4), V.POUR[0] + 0.2, db=-20)
    m.add(sfx.rustle(0.3, seed=13), V.PUT[0], db=-18)
    for k in range(5):                                            # the feast: crunching
        m.add(sfx.crackle(0.09, density=200, seed=30 + k), V.T_FEAST + 0.15 + 0.22 * k, db=-11, pan=0.25)
    m.add(sfx.purr(1.7), V.T_FEAST + 1.3, db=-8, pan=0.25)
    return m.render()


def main(silent, out):
    x = master(build())
    wav = os.path.join(ROOT, 'sound', 'full_bowl_sfx.wav')
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
