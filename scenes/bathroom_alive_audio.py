"""Sound for bathroom_alive: our own synthesised effects (lib/sfx.py), no music.

Usage: python scenes/bathroom_alive_audio.py <silent.mp4> <out.mp4>
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'lib'))
sys.path.insert(0, os.path.join(ROOT, 'scenes'))
import sfx  # noqa: E402
import bathroom_alive as V  # noqa: E402
from bathroom_alone_audio import creak  # noqa: E402
from litter_frenzy_audio import master, measure, mux  # noqa: E402


def build():
    m = sfx.Mix(V.DUR)
    m.add(sfx.room_tone(V.DUR), 0, db=-34)
    m.add(sfx.paper_slap(), 0.0, db=-10)
    t = 0.05
    while t < 2.0:                                     # soft paw steps down the hallway
        m.add(sfx.thump(0.1), t, db=-24, pan=-0.8 + 1.4 * t / 2.0)
        t += 1 / 6.4
    m.add(sfx.meow(0.42, f0=(460, 700, 480), vowels='iau', seed=4), 2.25, db=-7, pan=0.5)
    for k, tt in enumerate((2.75, 2.88, 3.01)):
        m.add(sfx.scratch(seed=k), tt, db=-10, pan=0.5)
    m.add(sfx.meow(0.38, f0=(520, 760, 500), vowels='iau', seed=6), 2.95, db=-8, pan=0.5)
    m.add(creak(0.6), V.T_DOOR0, db=-11)
    m.add(sfx.gasp(0.35), V.T_DOOR1 + 0.25, db=-12)
    m.add(sfx.plink(2600), V.T_DOOR1 + 0.3, db=-16)
    t = V.T_DOOR1 + 0.2
    while t < 5.6:
        m.add(sfx.thump(0.1), t, db=-24)
        t += 1 / 6.0
    m.add(sfx.whoosh(0.35, 500, 5000), 7.0, db=-12)
    m.add(sfx.thump(0.2), 7.55, db=-11)
    m.add(sfx.purr(3.4), 7.9, db=-12)
    m.add(sfx.gasp(0.6), 8.7, db=-14)                  # her long sigh into her hands
    m.add(sfx.whoosh(0.3), V.T_BACK - 0.1, db=-14)
    m.add(sfx.thump(0.25), V.T_BACK, db=-9)
    m.add(sfx.meow(0.55, f0=(480, 820, 520), vowels='iau', seed=33), V.T_BACK + 0.35, db=-5, pan=0.5)
    return m.render()


def main(silent, out):
    import soundfile as sf
    x = master(build())
    wav = os.path.join(ROOT, 'sound', 'bathroom_alive_sfx.wav')
    sf.write(wav, x, sfx.SR, subtype='FLOAT')
    mux(silent, wav, out)
    print(measure(out), out)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
