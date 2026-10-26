"""Sound for alive_rig: our own synthesised effects (lib/sfx.py), no music: her footsteps
on each foot plant of the walk, the cat's surprised plink, two meows, the jump's whoosh and
the landing thump; mastered to -14 LUFS and muxed onto the silent render.

Usage: python scenes/alive_rig_audio.py <silent.mp4> <out.mp4>
"""
import math
import os
import sys

import soundfile as sf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'lib'))
sys.path.insert(0, os.path.join(ROOT, 'scenes'))
import sfx  # noqa: E402
import alive_rig as V  # noqa: E402
from litter_frenzy_audio import TARGET_LUFS, master, measure, mux  # noqa: E402


def build():
    m = sfx.Mix(V.DUR)
    m.add(sfx.room_tone(V.DUR), 0.0, db=-34)
    m.add(sfx.meow(0.3, f0=(480, 560, 500), vowels='eau', seed=3), 0.1, db=-16, pan=0.3)   # a little mrrp: no silent head
    # footsteps: a foot lands each time the walk phase passes a half cycle
    g = V.GIRL
    t, prev = V.T_IN, None
    while t < V.T_STOP + 0.3:
        k = math.floor(g.walk_phase(t) * 2 + 0.25)
        if prev is not None and k != prev and g.walk(t) > 0.3:
            m.add(sfx.thump(0.12), t, db=-17, pan=max(-1.0, min(1.0, (g.x(t) - 540) / 540)))
        prev = k
        t += 1 / 240
    m.add(sfx.plink(2600), 1.62, db=-15, pan=0.3)                    # surprised
    for b in V.GIRL.blinks:
        m.add(sfx.plink(2300), b, db=-26, pan=-0.4)
    for (a, d), seed, f0 in zip(V.CAT.meows, (7, 9), ((520, 820, 520), (560, 900, 540))):
        m.add(sfx.meow(d, f0=f0, vowels='iau', seed=seed), a, db=-7, pan=0.3 if a < V.J0 else 0.6)
    m.add(sfx.whoosh(0.4, 500, 5000), V.J0 - 0.05, db=-12, pan=0.4)
    m.add(sfx.thump(0.2), V.J1, db=-8, pan=0.6)
    return m.render()


def main(silent, out):
    x = master(build())
    wav = os.path.join(ROOT, 'sound', 'alive_rig_sfx.wav')
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
