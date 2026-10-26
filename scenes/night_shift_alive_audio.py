"""Sound for night_shift_alive: night_shift's sound design (same timing and escalating
meows), plus what the living characters now do: the sheets rustle at her twitches, the cat
says its "NOTHING" mrrp with its mouth, and the paw steps land on the walk's footfalls.

Usage: python scenes/night_shift_alive_audio.py <silent.mp4> <out.mp4>
"""
import math
import os
import sys

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'lib'))
sys.path.insert(0, os.path.join(ROOT, 'scenes'))
import sfx  # noqa: E402
import night_shift_alive as V  # noqa: E402
from cat_walk import LEGS  # noqa: E402
from litter_frenzy_audio import master, measure, mux  # noqa: E402

TARGET_LUFS = -14.0


def build():
    m = sfx.Mix(V.DUR)
    m.add(sfx.room_tone(V.DUR), 0.0, db=-36)
    m.add(sfx.crickets(V.DUR), 0.0, db=-36)
    m.add(sfx.paper_slap(), 0.0, db=-10)
    # each clock change ticks; each new spot = the cat just jumped there
    k = 0
    for i, sh in enumerate(V.SHOTS):
        if sh['clock'] and (i == 0 or sh['clock'] != V.SHOTS[i - 1]['clock']):
            m.add(sfx.tick(), sh['t'] + 0.02, db=-8)
            m.add(sfx.tick(2900), sh['t'] + 0.12, db=-12)
        if i and isinstance(sh['cat'], dict):
            m.add(sfx.whoosh(0.22, 600, 5000), sh['t'] - 0.08, db=-18)
            m.add(sfx.thump(), sh['t'] + 0.12, db=-12)
        # meows escalate: higher, longer, louder, more grit as the night goes on
        for j, mt in enumerate(sh['meows']):
            lvl = min(1.0, k / 12)
            f0 = (430 + 180 * lvl, 720 + 260 * lvl, 470 + 120 * lvl)
            dur = 0.38 + 0.12 * lvl
            v = sfx.meow(dur, f0=f0, vowels='iau', bright=1.0 + 0.4 * lvl, jitter=0.01 + 0.02 * lvl,
                         growl=0.15 * lvl, seed=10 + k)
            if lvl > 0.5:
                v = np.tanh(1.5 * v) / np.tanh(1.5)
            pan = -0.35 if (sh['cat']['x'] if isinstance(sh['cat'], dict) else 384) < 300 else 0.25
            m.add(v, sh['t'] + mt, db=-9 + 4 * lvl, pan=pan)
            k += 1
    # her twitches under the blanket
    for j, tj in enumerate(V.GIRL.jolts):
        m.add(sfx.rustle(0.3, seed=30 + j), tj, db=-22)
    # 15.0 she sits up: sheets + an angry hit under the shout bubble
    m.add(sfx.rustle(0.55), 14.92, db=-10)
    m.add(sfx.impact(0.9), 15.12, db=-6)
    m.add(sfx.doom_hit(1.2), 15.15, db=-14)
    # 17.2 NOTHING: a little "mrrp" then silence lets it land
    m.add(sfx.meow(0.3, f0=(520, 560, 480), vowels='eau', seed=40), 17.75, db=-12)
    # 19.2 she lies back; soft paw steps as it walks off
    m.add(sfx.rustle(0.7, seed=9), 19.2, db=-13)
    x0s, x1s, ta, tb = V.WALK_X
    t, dt, prev = ta, 1 / 240, {n: None for n in LEGS}
    while t <= tb:
        ph = (t - ta) * V.WALK_CADENCE
        for n, (_, _, _, off) in LEGS.items():
            c = math.cos(2 * math.pi * (ph + off))
            if prev[n] is not None and prev[n] > 0 >= c and n[1] == 'n':   # near paws land
                x = x0s + (x1s - x0s) * (t - ta) / (tb - ta)
                m.add(sfx.thump(0.1), t, db=-22, pan=float(np.clip((x - 384) / 400, -1, 1)))
            prev[n] = c
        t += dt
    # 21.4 the last meow from the door (the loudest) and her eyes snap open
    m.add(sfx.slide_whistle(1300, 1900, 0.25), 21.48, db=-20)
    return m.render()


def main(silent, out):
    import soundfile as sf
    x = master(build())
    os.makedirs(os.path.join(ROOT, 'sound'), exist_ok=True)
    wav = os.path.join(ROOT, 'sound', 'night_shift_alive_sfx.wav')
    for attempt in range(3):
        sf.write(wav, x, sfx.SR, subtype='FLOAT')
        mux(silent, wav, out)
        lufs, peak = measure(out)
        print('attempt %d: %.2f LUFS, peak %.2f dBFS' % (attempt, lufs, peak))
        if abs(lufs - TARGET_LUFS) <= 0.3 and peak < -1.0:
            break
        x = x * 10 ** ((TARGET_LUFS - lufs) / 20)
    print(out)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
