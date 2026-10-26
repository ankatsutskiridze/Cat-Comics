"""Sound for night_meow: our own synthesised effects (lib/sfx.py), no music, timed to the
picture in scenes/night_meow.py, mastered to -14 LUFS and muxed onto the silent render.

Usage: python scenes/night_meow_audio.py <silent.mp4> <out.mp4>
"""
import os
import sys

import numpy as np
import soundfile as sf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'lib'))
sys.path.insert(0, os.path.join(ROOT, 'scenes'))
import sfx  # noqa: E402
import night_meow as V  # noqa: E402
from litter_frenzy_audio import TARGET_LUFS, master, measure, mux  # noqa: E402

# one voice per meow: (pitch contour, vowels, pan = where the cat is on screen)
VOICES = [((520, 760, 470), 'iau', 0.05), ((480, 700, 430), 'eau', 0.05), ((560, 820, 500), 'iao', 0.05),
          ((600, 880, 520), 'iau', 0.25), ((540, 900, 480), 'eaou', 0.25), ((620, 940, 540), 'iau', 0.55),
          ((640, 980, 560), 'iaou', 0.55), ((700, 1080, 600), 'iaaou', -0.7)]


def build():
    m = sfx.Mix(V.DUR)
    m.add(sfx.room_tone(V.DUR), 0.0, db=-36)                        # never a silent frame
    m.add(sfx.crickets(V.DUR), 0.0, db=-36, pan=0.5)                # night through the window
    m.add(sfx.paper_slap(), 0.0, db=-10)                            # the clock strip lands
    for at in (3.2, 5.6, 8.0, 12.6, 16.4):                          # every new clock time
        m.add(sfx.tick(), at, db=-14)
    for k, ((a, b), (f0, vowels, pan)) in enumerate(zip(V.MEOWS, VOICES)):
        last = k == len(V.MEOWS) - 1
        m.add(sfx.meow(b - a, f0=f0, vowels=vowels, bright=1.2 if last else 1.0, seed=20 + k),
              a, db=-4 if last else -8 + 0.5 * k, pan=pan)
    # 8.0 she sits up and yells (the bubble): sheets, a whoosh and a hit for the bubble
    m.add(sfx.rustle(0.5), 7.95, db=-12)
    m.add(sfx.whoosh(0.3), 8.05, db=-12)
    m.add(sfx.impact(0.9), 8.15, db=-10)
    # 10.8 the stare: nothing but the room, one small plink to land the beat
    m.add(sfx.plink(1900), 11.5, db=-18)
    # 12.6 she lies back down, the cat walks off left: soft paw steps panning away
    m.add(sfx.rustle(0.6, seed=7), 12.55, db=-13)
    t = 12.75
    while t < 15.0:
        x = 760 - 1050 * V.ease((t - 12.6) / 2.6 * 1.15)
        m.add(sfx.thump(), t, db=-20, pan=float(np.clip((x - 540) / 600, -1, 1)))
        t += np.pi / 7.5
    # 16.4 her eyes snap open
    m.add(sfx.gasp(), 16.42, db=-12)
    m.add(sfx.plink(2600), 16.45, db=-16)
    return m.render()


def main(silent, out):
    x = master(build())
    wav = os.path.join(ROOT, 'sound', 'night_meow_sfx.wav')
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
