"""Sound for warm_spot: our own synthesised effects (lib/sfx.py), no music, timed to
scenes/warm_spot.py, mastered to -14 LUFS and muxed onto the silent render.

Usage: python scenes/warm_spot_audio.py <silent.mp4> <out.mp4>
"""
import os
import sys

import numpy as np
import soundfile as sf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'lib'))
sys.path.insert(0, os.path.join(ROOT, 'scenes'))
import sfx  # noqa: E402
import warm_spot as V  # noqa: E402
from litter_frenzy_audio import TARGET_LUFS, master, measure, mux  # noqa: E402

# one voice per meow (V.MEOWS): pitch contour, vowels, level; the last one is the scream
VOICES = [((540, 820, 500), 'iau', -9), ((520, 860, 480), 'iaou', -8), ((580, 920, 520), 'iau', -7),
          ((470, 600, 430), 'eau', -6),
          ((560, 840, 500), 'iau', -9), ((540, 880, 480), 'iau', -8), ((600, 950, 520), 'iaou', -7),
          ((620, 1050, 560), 'iaaou', -3)]


def pan_of(x):
    return float(np.clip((x - 540) / 540, -1, 1)) * 0.6


def build():
    m = sfx.Mix(V.DUR)
    m.add(sfx.room_tone(V.DUR), 0.0, db=-34)
    m.add(sfx.crickets(V.DUR), 0.0, db=-36)                      # night outside the window
    m.add(sfx.paper_slap(), 0.0, db=-12)                          # the caption lands
    for (a, d, _, _), (f0, vowels, db) in zip(V.MEOWS, VOICES):
        x = V.cat_state(a)[0]
        bright = 1.3 if db == -3 else 1.0
        m.add(sfx.meow(d, f0=f0, vowels=vowels, bright=bright, seed=int(a * 10)), max(0.0, a), db=db,
              pan=pan_of(x))
    for a, d, p0, p1, _ in V.JUMPS:                              # each jump: push-off whoosh, soft landing
        m.add(sfx.whoosh(d * 0.9), a, db=-22, pan=pan_of(p0[0]))
        m.add(sfx.thump(0.16), a + d, db=-13, pan=pan_of(p1[0]))
        m.add(sfx.rustle(0.3, seed=int(a)), a + d, db=-22, pan=pan_of(p1[0]))
    m.add(sfx.gasp(0.3), V.JUMPS[0][0] + V.JUMPS[0][1] + 0.05, db=-14)   # "oof": it lands on her
    for a, _ in V.CLOCK[1:]:                                      # the clock rolls on
        m.add(sfx.tick(), a, db=-18, pan=-0.5)
        m.add(sfx.tick(2600), a + 0.09, db=-21, pan=-0.5)
    m.add(sfx.plink(2600), 4.6, db=-24)                           # slow stare-blinks
    m.add(sfx.plink(2600), 14.8, db=-24)
    m.add(sfx.rustle(0.45, seed=21), V.T_SIT - 0.02, db=-12)      # she jolts up out of the blanket
    m.add(sfx.whoosh(0.3), V.T_SIT, db=-18)
    m.add(sfx.plink(1700), V.SAY[0] - 0.05, db=-20)               # the bubble pops
    m.add(sfx.impact(0.6), V.SAY[0] + 0.05, db=-22)
    m.add(sfx.chime(1568), V.T_SIT + 0.45, db=-26)                # the warm dent glows
    m.add(sfx.purr(V.DUR - V.T_CURL - 0.2), V.T_CURL + 0.2, db=-8)
    m.add(sfx.plink(1500), V.SAY2[0] - 0.05, db=-20)
    return m.render()


def main(silent, out):
    x = master(build())
    wav = os.path.join(ROOT, 'sound', 'warm_spot_sfx.wav')
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
