"""Sound for bathroom_ref: our own synthesised effects (lib/sfx.py), no music.

Usage: python scenes/bathroom_ref_audio.py <silent.mp4> <out.mp4>
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'lib'))
sys.path.insert(0, os.path.join(ROOT, 'scenes'))
import sfx  # noqa: E402
import bathroom_ref as V  # noqa: E402
from bathroom_alone_audio import creak  # noqa: E402
from litter_frenzy_audio import master, measure, mux  # noqa: E402


def steps(m, t0, t1, rate, db=-24, pan=0.0):
    t = t0
    while t < t1:
        m.add(sfx.thump(0.1), t, db=db, pan=pan)
        t += 1 / rate


def build():
    m = sfx.Mix(V.DUR)
    m.add(sfx.room_tone(V.DUR), 0, db=-34)
    steps(m, 0.0, 1.0, 6.4, pan=0.2)
    m.add(sfx.meow(0.4, f0=(460, 690, 480), vowels='iau', seed=4), 2.3, db=-8, pan=0.5)
    m.add(creak(0.5), V.T_DOOR0, db=-11)
    steps(m, V.T_DOOR1, 4.3, 6.0, pan=0.3)
    m.add(sfx.whoosh(0.3, 500, 5000), 4.3, db=-13)
    m.add(sfx.thump(0.18), 4.75, db=-12, pan=0.2)
    m.add(sfx.purr(1.5), 4.9, db=-13, pan=0.2)
    m.add(sfx.whoosh(0.3, 500, 5000), 6.4, db=-14)
    m.add(sfx.thump(0.18), 6.85, db=-11)
    steps(m, 8.2, 8.65, 6.0)
    m.add(sfx.rustle(0.3), 10.0, db=-14)
    m.add(sfx.thump(0.2), 10.05, db=-12)
    m.add(sfx.meow(0.3, f0=(520, 580, 480), vowels='eau', seed=11), 10.5, db=-12)
    return m.render()


def main(silent, out):
    import soundfile as sf
    x = master(build())
    wav = os.path.join(ROOT, 'sound', 'bathroom_ref_sfx.wav')
    sf.write(wav, x, sfx.SR, subtype='FLOAT')
    mux(silent, wav, out)
    print(measure(out), out)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
