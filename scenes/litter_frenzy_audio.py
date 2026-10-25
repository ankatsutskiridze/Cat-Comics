"""Sound for litter_frenzy: our own synthesised effects (lib/sfx.py), no music, timed to the
picture in scenes/litter_frenzy.py, mastered to -14 LUFS and muxed onto the silent render.

Usage: python scenes/litter_frenzy_audio.py <silent.mp4> <out.mp4>
"""
import os
import subprocess
import sys
import tempfile

import numpy as np
import pyloudnorm as pyln
import soundfile as sf

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'lib'))
sys.path.insert(0, os.path.join(ROOT, 'scenes'))
import sfx  # noqa: E402
import litter_frenzy as V  # noqa: E402

TARGET_LUFS = -14.0
CEIL_DB = -1.5


def build():
    m = sfx.Mix(V.DUR)
    m.add(sfx.room_tone(V.DUR), 0.0, db=-38)                       # never a silent frame
    # 0-1.8 face: caption slaps on, a questioning "mrrp?", the blink
    m.add(sfx.paper_slap(), 0.0, db=-8)
    m.add(sfx.meow(0.38, f0=(430, 520, 640), vowels='eau', seed=2), 0.35, db=-9)
    m.add(sfx.plink(2400), 1.15, db=-14)
    # 1.8 cut to the box; the slow stretch
    m.add(sfx.whoosh(0.3), 1.72, db=-16)
    m.add(sfx.slide_whistle(480, 1150, 1.6), 2.1, db=-17)
    # 4.9 eyes go blank (a swell leans into the hit), 5.0 tail poofs, 5.7 gasp
    m.add(sfx.drone(1.3), 3.6, db=-12)
    m.add(sfx.doom_hit(), 4.88, db=-4)
    m.add(sfx.poof(), 5.0, db=-9)
    m.add(sfx.gasp(), 5.55, db=-14)
    # 6.6-10 possessed: electric crackle and buzz
    m.add(sfx.crackle(0.6, density=25, seed=4), 6.0, db=-20)
    m.add(sfx.crackle(3.4), 6.6, db=-12)
    m.add(sfx.meow(0.9, f0=(300, 340, 280), vowels='uou', growl=0.6, bright=0.6, seed=8), 7.6, db=-15)
    # 10-11 crouch: wind-up
    m.add(sfx.riser(1.0), 10.0, db=-10)
    # 11-14.5 frenzy: a scratch per paw stroke (2 paws x 4 scoops a second), sand, the yowl
    k = 0
    t = V.DIG0 + 0.0625
    while t < V.DIG1 - 0.05:
        m.add(sfx.scratch(seed=k), t, db=-7 + np.random.default_rng(k).uniform(-2, 1),
              pan=-0.45 if k % 2 else 0.45)
        k += 1
        t += 0.125
    m.add(sfx.sand_hiss(V.DIG1 - V.DIG0 - 0.15), V.DIG0 + 0.15, db=-16)
    m.add(sfx.scream(3.3), V.DIG0 + 0.1, db=-11)
    # 14.5 white flash
    m.add(sfx.impact(), 14.48, db=-3)
    # aftermath: sparkle chimes, a purr, the slow blink, a pleased "mrrp"
    m.add(sfx.chime(2093), 15.0, db=-18, pan=-0.4)
    m.add(sfx.chime(3136), 15.35, db=-20, pan=0.4)
    m.add(sfx.purr(1.9), 15.3, db=-14)
    m.add(sfx.plink(2000), 16.3, db=-16)
    m.add(sfx.meow(0.45, f0=(520, 600, 470), vowels='eao', seed=11), 16.75, db=-10)
    return m.render()


def master(x):
    """Soft-limit under the ceiling, then set integrated loudness to the target."""
    meter = pyln.Meter(sfx.SR)
    for _ in range(4):
        lufs = meter.integrated_loudness(x)
        x = x * 10 ** ((TARGET_LUFS - lufs) / 20)
        ceil = 10 ** (CEIL_DB / 20)
        x = np.tanh(x / ceil) * ceil
    return x


def measure(mp4):
    with tempfile.TemporaryDirectory() as d:
        wav = os.path.join(d, 'a.wav')
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', mp4, '-vn', '-ac', '2', '-ar', '48000',
                        '-c:a', 'pcm_f32le', wav], check=True)
        a, sr = sf.read(wav, dtype='float64')
    lufs = pyln.Meter(sr).integrated_loudness(a)
    peak = 20 * np.log10(np.max(np.abs(a)) + 1e-12)
    return lufs, peak


def mux(silent, wav, out):
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', silent, '-i', wav, '-map', '0:v', '-map', '1:a',
                    '-c:v', 'copy', '-c:a', 'aac', '-b:a', '384k', '-movflags', '+faststart', out], check=True)


def main(silent, out):
    x = master(build())
    sound_dir = os.path.join(ROOT, 'sound')
    os.makedirs(sound_dir, exist_ok=True)
    wav = os.path.join(sound_dir, 'litter_frenzy_sfx.wav')
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
