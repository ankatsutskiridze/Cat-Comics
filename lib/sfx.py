"""Sound effects synthesised from scratch (numpy/scipy): no samples, no third-party audio,
so every sound we make is ours to use anywhere.

All functions return mono float64 arrays at SR. `Mix` places them on a stereo timeline.
"""
import math

import numpy as np
from scipy import signal

SR = 48000
_rng = np.random.default_rng(1234)


def _n(dur):
    return max(1, int(dur * SR))


def _t(dur):
    return np.arange(_n(dur)) / SR


def noise(dur, rng=None):
    return (rng or _rng).standard_normal(_n(dur))


def band(x, lo, hi, order=4):
    sos = signal.butter(order, [lo, hi], btype='band', fs=SR, output='sos')
    return signal.sosfilt(sos, x)


def low(x, f, order=4):
    return signal.sosfilt(signal.butter(order, f, btype='low', fs=SR, output='sos'), x)


def high(x, f, order=4):
    return signal.sosfilt(signal.butter(order, f, btype='high', fs=SR, output='sos'), x)


def env(dur, attack=0.005, decay=None, hold=0.0):
    """Linear attack, optional hold, exponential decay (decay = time to -60 dB)."""
    t = _t(dur)
    e = np.clip(t / max(attack, 1e-4), 0, 1)
    if decay:
        k = np.clip(t - attack - hold, 0, None)
        e = e * np.exp(-6.9 * k / decay)
    return e


def norm(x, peak=1.0):
    m = np.max(np.abs(x)) + 1e-12
    return x / m * peak


def sweep_tone(f0, f1, dur, shape='sine', curve=1.0):
    t = _t(dur)
    f = f0 + (f1 - f0) * (t / dur) ** curve
    ph = 2 * np.pi * np.cumsum(f) / SR
    if shape == 'sine':
        return np.sin(ph)
    return signal.sawtooth(ph)


# ------------------------------------------------------------------ cat voice

FORMANTS = {'i': (320, 2300, 3000), 'e': (500, 1900, 2600), 'a': (850, 1350, 2700),
            'o': (560, 950, 2500), 'u': (350, 800, 2400)}


def meow(dur=0.6, f0=(520, 780, 460), vowels='iau', bright=1.0, breath=0.06, jitter=0.0,
         growl=0.0, seed=3):
    """Additive harmonic voice with a pitch contour and moving formants ('mee-ow')."""
    rng = np.random.default_rng(seed)
    n = _n(dur)
    t = np.arange(n) / SR
    x = t / dur
    # pitch contour through the given points, plus jitter / vibrato
    pts = np.linspace(0, 1, len(f0))
    f = np.interp(x, pts, f0)
    if jitter:
        j = signal.sosfilt(signal.butter(2, 18, fs=SR, output='sos'), rng.standard_normal(n))
        f = f * (1 + jitter * j / (np.std(j) + 1e-9))
    ph = 2 * np.pi * np.cumsum(f) / SR
    # formant tracks through the vowel sequence
    vp = np.linspace(0, 1, len(vowels))
    F = [np.interp(x, vp, [FORMANTS[v][k] for v in vowels]) for k in range(3)]
    out = np.zeros(n)
    for h in range(1, 28):
        fh = f * h
        amp = sum(np.exp(-((fh - F[k]) / (90 + 40 * k)) ** 2) * (1.0, 0.7 * bright, 0.35 * bright)[k]
                  for k in range(3))
        amp = amp + 0.04 / h
        amp[fh > SR / 2 - 500] = 0
        out += amp * np.sin(h * ph)
    if growl:
        out *= 1 + growl * np.sin(2 * np.pi * 34 * t)
    out += breath * band(rng.standard_normal(n), 1500, 7000) * 0.6
    e = np.clip(x / 0.08, 0, 1) * np.clip((1 - x) / 0.25, 0, 1) ** 0.7
    return norm(out * e)


def scream(dur=3.2, seed=5):
    """A possessed cat yowl: high, wobbly, gritty, with breaths of chaos."""
    rng = np.random.default_rng(seed)
    pts = [600] + list(rng.uniform(760, 1050, 9)) + [700]
    v = meow(dur, f0=pts, vowels='eaoaeaoa', bright=1.4, breath=0.15, jitter=0.03, growl=0.25, seed=seed)
    v = np.tanh(2.2 * v)                                   # grit
    t = _t(dur)
    v *= 0.75 + 0.25 * np.sin(2 * np.pi * 11 * t)          # warble
    return norm(v)


# ------------------------------------------------------------------ effects

def paper_slap():
    a = band(noise(0.16), 400, 5000) * env(0.16, 0.001, 0.12)
    b = np.sin(2 * np.pi * 95 * _t(0.16)) * env(0.16, 0.001, 0.10)
    return norm(0.7 * norm(a) + 0.5 * b)


def plink(f=2300):
    t = _t(0.12)
    return norm(np.sin(2 * np.pi * (f - 500 * t / 0.12) * t) * env(0.12, 0.001, 0.1))


def whoosh(dur=0.35, lo=400, hi=4000):
    x = band(noise(dur), lo, hi)
    t = _t(dur) / dur
    return norm(x * np.sin(np.pi * t) ** 2)


def slide_whistle(f0=520, f1=1250, dur=1.4):
    t = _t(dur)
    vib = 1 + 0.012 * np.sin(2 * np.pi * 6 * t)
    f = (f0 + (f1 - f0) * (t / dur) ** 1.4) * vib
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) + 0.12 * np.sin(4 * np.pi * np.cumsum(f) / SR)
    x += 0.05 * band(noise(dur), 1000, 4000)
    e = np.clip(t / 0.08, 0, 1) * np.clip((dur - t) / 0.2, 0, 1)
    return norm(x * e)


def doom_hit(dur=1.6):
    t = _t(dur)
    f = 62 * np.exp(-t * 0.6) + 34
    sub = np.sin(2 * np.pi * np.cumsum(f) / SR) * env(dur, 0.002, 1.4)
    click = band(noise(0.05), 80, 2500) * env(0.05, 0.0005, 0.04)
    x = sub
    x[:len(click)] += 0.6 * click
    eerie = np.sin(2 * np.pi * 1661 * t) * np.clip(t / 0.5, 0, 1) * np.exp(-t * 1.2) * \
        (0.6 + 0.4 * np.sin(2 * np.pi * 7 * t))
    return norm(x + 0.12 * eerie)


def drone(dur=1.4):
    """Ominous low swell that leans into a hit."""
    t = _t(dur)
    x = np.sin(2 * np.pi * 55 * t) + 0.5 * np.sin(2 * np.pi * 82.5 * t) + 0.3 * signal.sawtooth(2 * np.pi * 110 * t)
    x = low(x, 600) * (1 + 0.15 * np.sin(2 * np.pi * 5 * t))
    return norm(x * (t / dur) ** 2)


def poof(dur=0.3):
    x = low(noise(dur), 1800) + 0.4 * band(noise(dur), 2000, 6000)
    return norm(x * env(dur, 0.004, 0.25))


def gasp(dur=0.35):
    t = _t(dur) / dur
    x = band(noise(dur), 900, 5000) * (t ** 1.5) * np.clip((1 - t) / 0.15, 0, 1)
    return norm(x)


def crackle(dur, density=55, seed=7):
    """Electric crackle: clusters of tiny filtered noise bursts over a low buzz."""
    rng = np.random.default_rng(seed)
    n = _n(dur)
    out = np.zeros(n)
    for _ in range(int(density * dur)):
        L = int(rng.uniform(0.003, 0.03) * SR)
        s = rng.integers(0, max(1, n - L))
        b = band(rng.standard_normal(L + 64), 1800, 9000)[64:] * np.exp(-np.linspace(0, 6, L))
        out[s:s + L] += b * rng.uniform(0.2, 1.0)
    t = np.arange(n) / SR
    buzz = signal.sawtooth(2 * np.pi * 58 * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 3.3 * t)) * 0.18
    buzz = low(buzz, 900)
    return norm(norm(out) + buzz)


def riser(dur=1.0):
    t = _t(dur)
    tone = sweep_tone(180, 900, dur, curve=2.0)
    hiss = band(noise(dur), 500, 9000) * (t / dur) ** 2
    return norm((0.5 * tone + 0.6 * norm(hiss)) * (t / dur) ** 1.6)


def scratch(seed=0):
    rng = np.random.default_rng(seed)
    d = rng.uniform(0.05, 0.08)
    x = band(rng.standard_normal(_n(d)), 1400, 7000)
    t = _t(d) / d
    grit = (rng.random(_n(d)) < 0.02) * rng.uniform(1, 3, _n(d))
    return norm((x + band(grit, 2000, 9000)) * np.exp(-4 * t) * np.clip(t / 0.05, 0, 1))


def sand_hiss(dur, seed=9):
    rng = np.random.default_rng(seed)
    n = _n(dur)
    grains = (rng.random(n) < 0.004) * rng.uniform(0.2, 1, n)
    g = band(np.convolve(grains, np.hanning(60), 'same') * rng.standard_normal(n), 2500, 11000)
    bed = band(rng.standard_normal(n), 3000, 9000) * 0.25
    return norm(g + bed)


def impact(dur=1.2):
    t = _t(dur)
    boom = np.sin(2 * np.pi * (48 + 30 * np.exp(-t * 8)) * t) * env(dur, 0.001, 1.0)
    crash = band(noise(dur), 300, 8000) * env(dur, 0.001, 0.45)
    return norm(boom + 0.5 * norm(crash))


def chime(f=2093):
    t = _t(0.9)
    x = sum(a * np.sin(2 * np.pi * f * r * t) * np.exp(-t * d)
            for a, r, d in [(1, 1, 4), (0.5, 2.76, 7), (0.3, 5.4, 10), (0.2, 1.5, 6)])
    return norm(x * np.clip(t / 0.002, 0, 1))


def purr(dur=1.6):
    t = _t(dur)
    x = low(noise(dur), 260) * (0.55 + 0.45 * np.sign(np.sin(2 * np.pi * 24 * t))) ** 2
    x += 0.4 * np.sin(2 * np.pi * 48 * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 24 * t))
    return norm(x * np.clip(t / 0.25, 0, 1) * np.clip((dur - t) / 0.4, 0, 1))


def tick(f=3200):
    """A clock tick: a tiny bright click with a short body."""
    t = _t(0.06)
    x = band(noise(0.06), 2000, 7000) * np.exp(-t * 160) + 0.5 * np.sin(2 * np.pi * f * t) * np.exp(-t * 90)
    return norm(x)


def thump(dur=0.18):
    """Soft paws landing on something."""
    t = _t(dur)
    x = np.sin(2 * np.pi * (90 + 60 * np.exp(-t * 40)) * t) * np.exp(-t * 28) + 0.3 * low(noise(dur), 900) * np.exp(-t * 40)
    return norm(x)


def rustle(dur=0.5, seed=4):
    """Bed sheets moving."""
    rng = np.random.default_rng(seed)
    x = band(rng.standard_normal(_n(dur)), 600, 5000)
    t = _t(dur) / dur
    am = np.convolve(np.abs(rng.standard_normal(_n(dur))), np.hanning(2400), 'same')
    return norm(x * am * np.sin(np.pi * t))


def crickets(dur, seed=2):
    """Distant night crickets: chirp trains of a ~4.4 kHz tone."""
    rng = np.random.default_rng(seed)
    n = _n(dur)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for f, rate, ph in [(4400, 0.9, 0.0), (4750, 0.7, 0.4)]:
        gate = (np.sin(2 * np.pi * rate * t + ph * 6) > 0.6).astype(float)
        pulse = (np.sin(2 * np.pi * 30 * t) > 0).astype(float)
        out += np.sin(2 * np.pi * f * t) * gate * pulse
    return norm(low(out, 6000))


def room_tone(dur):
    return norm(low(band(noise(dur), 60, 3000), 1200)) * 0.5


# ------------------------------------------------------------------ timeline

class Mix:
    def __init__(self, dur):
        self.buf = np.zeros((_n(dur) + SR, 2))
        self.dur = dur

    def add(self, x, at, db=0.0, pan=0.0):
        """pan -1 left .. +1 right (constant power)."""
        g = 10 ** (db / 20)
        a = (pan + 1) * math.pi / 4
        s = int(at * SR)
        e = min(len(self.buf), s + len(x))
        if e <= s:
            return
        self.buf[s:e, 0] += x[:e - s] * g * math.cos(a)
        self.buf[s:e, 1] += x[:e - s] * g * math.sin(a)

    def render(self):
        return self.buf[:_n(self.dur)].copy()
