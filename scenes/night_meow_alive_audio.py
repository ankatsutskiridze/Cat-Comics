"""Sound for night_meow_alive: night_meow's sound design (same timing, same voices), plus
what the living characters now do on screen: the sheets rustle at each of her twitches,
and the walking cat's paw steps land on its footfalls.

Usage: python scenes/night_meow_alive_audio.py <silent.mp4> <out.mp4>
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
import night_meow_alive as V  # noqa: E402
from cat_walk import LEGS  # noqa: E402
from litter_frenzy_audio import TARGET_LUFS, master, measure, mux  # noqa: E402
from night_meow_audio import VOICES  # noqa: E402


def build():
    m = sfx.Mix(V.DUR)
    m.add(sfx.room_tone(V.DUR), 0.0, db=-36)                        # never a silent frame
    m.add(sfx.crickets(V.DUR), 0.0, db=-36, pan=0.5)
    m.add(sfx.paper_slap(), 0.0, db=-10)
    for at in (3.2, 5.6, 8.0, 12.6, 16.4):
        m.add(sfx.tick(), at, db=-14)
    for k, ((a, b), (f0, vowels, pan)) in enumerate(zip(V.MEOWS, VOICES)):
        last = k == len(V.MEOWS) - 1
        m.add(sfx.meow(b - a, f0=f0, vowels=vowels, bright=1.2 if last else 1.0, seed=20 + k),
              a, db=-4 if last else -8 + 0.5 * k, pan=pan)
    # her twitches under the blanket
    for k, tj in enumerate(V.GIRL.jolts):
        if tj < 16.4:
            m.add(sfx.rustle(0.3, seed=30 + k), tj, db=-22)
    m.add(sfx.rustle(0.5), 7.95, db=-12)                            # she springs up
    m.add(sfx.whoosh(0.3), 8.0, db=-12)
    m.add(sfx.impact(0.9), 8.15, db=-10)
    m.add(sfx.plink(1900), 11.5, db=-18)                            # the slow blink
    m.add(sfx.rustle(0.6, seed=7), 12.55, db=-13)                   # lies back down
    # paw steps: every foot plant of the walk (a leg's swing ending)
    w = V.WALK
    t = w.t0
    dt = 1 / 240
    prev = {n: None for n in LEGS}
    while t <= w.t1:
        ph = (t - w.t0) * w.cadence
        for n, (_, _, _, off) in LEGS.items():
            c = math.cos(2 * math.pi * (ph + off))
            if prev[n] is not None and prev[n] > 0 >= c:          # swing -> stance
                x = w.x(t)
                m.add(sfx.thump(), t, db=-22 if n[1] == 'f' else -19,
                      pan=float(np.clip((x - 540) / 600, -1, 1)))
            prev[n] = c
        t += dt
    m.add(sfx.gasp(), 16.42, db=-12)
    m.add(sfx.plink(2600), 16.45, db=-16)
    return m.render()


def main(silent, out):
    x = master(build())
    wav = os.path.join(ROOT, 'sound', 'night_meow_alive_sfx.wav')
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
