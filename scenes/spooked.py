"""Spooked: 3 AM, all quiet. The cat hops onto the sleeping girl and settles... then its head
snaps up: it stares at the empty wall above the bed. The camera follows its gaze: nothing
there. Back on the cat: pupils huge, fur up, and it launches off her belly and bolts. She
sits up, looks where it ran, then slowly at that wall: "...what did you SEE?!" Nothing.
The cat strolls back, curls up at her feet and falls asleep. She doesn't. "Great. Now I
can't sleep."

Both characters are drawn in code every frame (lib/girl3.py lying / sitting up in bed,
lib/cat3.py); the bedroom, bed and blanket are scenes/warm_spot.py's. Premise: the genre's
"cats panic at night for no reason" moment (research/reference-equmiart.md); our characters,
our trigger (the stare at nothing), the gaze pans, the bolt and the ending where the fear
passes to her.

Usage:
  python scenes/spooked.py stills            -> output/spooked_stills.png
  python scenes/spooked.py still <t>         -> output/_sp_<t>.png
  python scenes/spooked.py video [out.mp4]   -> silent 1080x1920 30 fps render
"""
import math
import os
import subprocess
import sys

import cairo
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'lib'))
sys.path.insert(0, os.path.join(ROOT, 'scenes'))
import cat3  # noqa: E402
import girl3  # noqa: E402
from full_bowl import bubble, caption, ease, ease_out, pulse, shadow, shout  # noqa: E402
from warm_spot import BED_TOP, GIRL_S, GIRL_X, GIRL_Y, _arc, bed_back, blanket, pillow, room, zzz  # noqa: E402

W, H, FPS = 1080, 1920, 30
DUR = 18.0

# ------------------------------------------------------------------ timeline (s)
HOP = (0.35, 0.8)                      # floor -> her belly
SNAP = 2.45                            # its head snaps up to the wall
PUSH = (2.7, 3.5)                      # push-in on the cat
WIDEN = (3.4, 4.6)                     # its eyes widen while it stares
PAN1 = (4.85, 5.35, 6.35, 6.75)        # pan to the wall, hold on nothing, pan back
SPOOK = 6.8                            # pupils huge, fur up
T_WIDE = 7.55                          # cut to wide: the launch
LAUNCH = (7.75, 8.2)                   # off her belly onto the floor
BOLT = (8.3, 8.65)                     # off screen right
SIT = (8.55, 8.9)                      # she sits up
T_LOOK_WALL = 9.9                      # she turns to the wall
FACE = (10.3, 12.35)                   # push-in on her face
SAY = (10.75, 12.25)                   # "...what did you SEE?!"
PAN2 = (12.35, 12.85, 13.55, 13.95)    # pan to the wall again: still nothing
BACK = (14.1, 14.6)                    # the cat hops back in, onto her feet
T_CURL = 15.0                          # curls up, eyes shut
T_GLANCE = (15.2, 16.0)                # she glances at it, then back at the wall
T_END_CAP = 16.2

# the cat's spots: (x, y, scale) = screen point under its paws
P_FLOOR = (845.0, 1800.0, 0.50)
P_BELLY = (585.0, 1290.0, 0.44)
P_RUN = (985.0, 1830.0, 0.50)
P_OFF = (1380.0, 1760.0, 0.50)
P_FEET = (845.0, 1312.0, 0.44)
JUMPS = [(HOP[0], HOP[1], P_FLOOR, P_BELLY, 240), (LAUNCH[0], LAUNCH[1], P_BELLY, P_RUN, 170),
         (BOLT[0], BOLT[1], P_RUN, P_OFF, 120), (BACK[0], BACK[1], P_OFF, P_FEET, 330)]
PREP = 0.3
LAND = 0.3

SPOT = (330.0, 330.0)                  # the empty wall it stares at (high above the picture)


# ------------------------------------------------------------------ the cat

def cat_place(t):
    """(x, y, scale, crouch, stretch, lean, airborne) from the jump list."""
    pos = P_FLOOR
    for (t0, t1, a, b, hgt) in JUMPS:
        if t >= t1:
            pos = b
    crouch, stretch, lean, air = 0.0, 0.0, 0.0, False
    x, y, s = pos
    for i, (t0, t1, a, b, hgt) in enumerate(JUMPS):
        d = 1 if b[0] > a[0] else -1
        prep = 0.12 if i == 2 else PREP                # the bolt: no wind-up, it is already running
        if t0 - prep <= t < t0 and i != 3:
            k = ease((t - (t0 - prep)) / prep)
            crouch = 0.45 * k
            lean = 6 * d * k
        elif t0 <= t < t1:
            u = (t - t0) / (t1 - t0)
            x, y, s = _arc(a, b, ease(u) * 0.3 + u * 0.7, hgt)
            air = True
            stretch = math.sin(u * math.pi) * 0.9 + (0.4 if u < 0.15 else 0)
            lean = 14 * d * math.cos(u * math.pi)
            crouch = 0.25 * max(0.0, (u - 0.8) / 0.2)
        elif t1 <= t < t1 + LAND:
            k = (t - t1) / LAND
            crouch = 0.5 * math.exp(-k * 3.5) * math.cos(k * 4)
    return x, y, s, crouch, stretch, lean, air


def cat_state(t):
    mood, yaw, nod = 'deadpan', 0.0, 0.0
    roll = 1.5 * math.sin(t * 1.1)
    look = [0.0, 0.0]
    ear_l = ear_r = 0.0
    blink = 0.0
    for b, d in ((1.35, 0.7), (14.75, 0.2)):          # 1.35 = a slow, content blink
        if b <= t < b + d:
            blink = math.sin((t - b) / d * math.pi) ** 0.7
    x, y, s, crouch, stretch, lean, air = cat_place(t)
    # on the rug: looks up at the bed
    if t < HOP[0]:
        yaw, look = -0.4, [-0.6, -0.7]
    # settled on her belly: calm, a little head bob, one ear flick
    elif t < SNAP:
        yaw, look = 0.1, [0.1, 0.2]
        mood = 'sleepy' if t > 1.1 else 'deadpan'
        if 1.95 < t < 2.3:
            ear_r = 16 * math.sin((t - 1.95) / 0.35 * 2 * math.pi) * (1 - (t - 1.95) / 0.35)
    # the snap: head up and to the left, staring at the wall; the eyes widen as it stares
    elif t < SPOOK:
        k = ease_out((t - SNAP) / 0.12)
        yaw = -0.75 * k
        nod = -0.55 * k
        roll += -6 * k
        look = [-1.0 * k, -1.0 * k]
        w = (t - WIDEN[0]) / (WIDEN[1] - WIDEN[0])
        mood = 'deadpan' if t < SNAP + 0.06 else ('surprised' if w < 1 else 'surprised')
        if t < WIDEN[0]:
            mood = 'confused' if t > SNAP + 0.5 else 'deadpan'
        ear_l, ear_r = -6 * k, 6 * k                   # ears forward
        crouch += 0.12 * ease(w)                       # it sinks low, very slowly
        lean += 3 * ease(w)
    # spooked: pupils huge, fur up, ears back, low
    elif t < LAUNCH[0] - PREP:
        mood = 'spooked'
        yaw, nod, look = -0.75, -0.5, [-1.0, -1.0]
        u = t - SPOOK
        crouch += 0.3 * ease_out(u / 0.15)
        roll += -6 + 2.5 * math.sin(u * 70) * math.exp(-u * 3)     # a shiver
    # the launch and the bolt: ears back
    elif t < BOLT[1]:
        mood = 'spooked'
        yaw, look = 0.6, [1.0, 0.0]
    # it comes back as if nothing happened
    elif t < T_CURL:
        mood = 'deadpan'
        yaw, look = -0.5, [-0.6, 0.0]
    # curls up at her feet: eyes shut, purring
    else:
        k = ease((t - T_CURL) / 0.5)
        mood = 'content' if t > T_CURL + 0.3 else 'sleepy'
        crouch += 0.32 * k
        yaw = 0.1 * k
        roll += 7 * k + 2 * math.sin((t - T_CURL) * 2.2)
        nod = 0.2 * k
    if air:
        ear_l, ear_r = 18, -18                         # ears back in the air
    breathe = math.sin(t * 2 * math.pi / (1.2 if SPOOK <= t < BOLT[1] else 2.4))
    return (x, y, s, stretch), dict(mood=mood, blink=blink, look=tuple(look), head_roll=roll, head_yaw=yaw,
                                    head_nod=nod, lean=lean, breathe=breathe, crouch=crouch,
                                    ear_l=ear_l, ear_r=ear_r)


def draw_cat(ctx, t):
    (x, y, s, stretch), st = cat_state(t)
    if x > W + 200:
        return
    on_bed = y < 1500
    shadow(ctx, x, y + 2, 92 * s / 0.44, 13, 0.18)
    ctx.save()
    ctx.translate(x, y)
    ctx.scale(1 - 0.10 * stretch, 1 + 0.16 * stretch)
    cat3.draw_cat_front(ctx, 0, 0, s, **st)
    ctx.restore()


def cat_weight(t):
    """Where the cat presses the blanket (x, 0..1), or None."""
    x, y, s, *_ = cat_place(t)
    if y > 1500 or y < 1260 or x < 330 or x > 1040:
        return None
    return (x, 1.0)


def cat_head(t):
    """The cat's head on screen (approx.), for the push-in."""
    (x, y, s, _), _st = cat_state(t)
    return x, y - (665 - 190) * s


# ------------------------------------------------------------------ the girl

def sit_amount(t):
    if t < SIT[0]:
        return 0.0
    u = (t - SIT[0]) / (SIT[1] - SIT[0])
    if u < 1:
        return ease_out(u) * 1.06
    return 1.0 + 0.06 * math.exp(-(t - SIT[1]) * 8) * math.cos((t - SIT[1]) * 20)


def girl_state(t):
    sit = sit_amount(t)
    R = -90 + 88 * sit                                 # body angle from upright
    expr, blink, look, talk = 'sleep', 0.0, (0.0, 0.0), 0.0
    head, turn = 0.0, 0.0
    # the cat lands on her belly: a small jolt in her sleep
    head -= 3 * pulse(t, HOP[1], HOP[1] + 0.3)
    # the launch off her belly: OOF, eyes snap open
    if t >= LAUNCH[0]:
        oof = pulse(t, LAUNCH[0], LAUNCH[0] + 0.35)
        head -= 6 * oof
        expr = 'surprised'
        look = (0.9, 0.6)
    if t >= SIT[0]:
        look = (1.0, 0.3)                              # where it ran
        head += 4 * ease((t - SIT[0]) / 0.3)
    # slowly, she turns to the wall behind her and up
    if t >= T_LOOK_WALL:
        k = ease((t - T_LOOK_WALL) / 0.6)
        look = (1.0 - 2.0 * k, 0.3 - 1.1 * k)
        turn = -0.8 * k
        head += -10 * k
    # a glance at the sleeping cat, then straight back to the wall
    if T_GLANCE[0] <= t < T_GLANCE[1] + 0.4:
        k = ease((t - T_GLANCE[0]) / 0.3) * (1 - ease((t - T_GLANCE[1]) / 0.4))
        look = (-1.0 + 2.0 * k, -0.8 + 1.3 * k)
        turn = -0.8 * (1 - k)
        expr = 'bored' if k > 0.6 else 'surprised'
    if SAY[0] <= t < SAY[1]:
        talk = abs(math.sin((t - SAY[0]) * math.pi * 3.8)) * 0.8
    # she never blinks while she watches the wall; a little shiver at the end
    if t > T_END_CAP:
        head += 1.2 * math.sin(t * 40) * math.exp(-(t - T_END_CAP) * 2)
    breathe = math.sin(t * 2 * math.pi / (3.6 if t < LAUNCH[0] else 1.6))
    pose = {'root': dict(rot=-90), 'gravity': min(1.0, sit),
            'chest': dict(rot=88 * sit, sx=1 + 0.012 * breathe * (1 - sit)),
            'head': dict(rot=head), 'turn': turn, 'nod': 0.0}
    if t > SIT[0]:
        d = t - SIT[0]
        hl = 7 * math.exp(-d * 2.6) * math.sin(d * 7)
        pose['lockL'] = dict(rot=hl)
        pose['lockR'] = dict(rot=hl * 0.8)
        pose['lockF'] = dict(rot=hl * 0.9)
    # arms along her sides lying; sitting: she clutches the blanket to her chest
    rest = {s: dict(sh=girl3.ARMS_DOWN[s]['sh'] - R, el=girl3.ARMS_DOWN[s]['el']) for s in ('n', 'f')}
    arms = rest
    if t >= SIT[0]:
        k = ease((t - SIT[0]) / 0.4)
        lap = {'n': dict(sh=20, el=55), 'f': dict(sh=12, el=50)}
        clutch = {'n': dict(sh=-10, el=120, hand='grip'), 'f': dict(sh=-4, el=115, hand='grip')}
        c = ease((t - T_LOOK_WALL - 0.3) / 0.5)
        arms = {}
        for s_ in ('n', 'f'):
            a, b = lap[s_], clutch[s_]
            arms[s_] = dict(sh=a['sh'] + (b['sh'] - a['sh']) * c, el=a['el'] + (b['el'] - a['el']) * c,
                            hand=b['hand'] if c > 0.5 else 'relaxed')
            if k < 1:
                arms[s_]['sh'] = rest[s_]['sh'] + (arms[s_]['sh'] - rest[s_]['sh']) * k
                arms[s_]['el'] = rest[s_]['el'] + (arms[s_]['el'] - rest[s_]['el']) * k
    return pose, expr, blink, look, talk, arms


def head_screen(t):
    """Her face on screen (approx.)."""
    sit = min(1.0, sit_amount(t))
    hx = GIRL_X - (1180 - 195) * GIRL_S
    hy = GIRL_Y - 30
    if sit > 0:
        px, py = GIRL_X - (1180 - 520) * GIRL_S, GIRL_Y - 25
        L = (520 - 195) * GIRL_S
        a = math.radians(88 * sit)
        hx, hy = px - L * math.cos(a), py - L * math.sin(a)
    return hx, hy


# ------------------------------------------------------------------ camera

def _lerp3(a, b, k):
    return tuple(a[i] + (b[i] - a[i]) * k for i in range(3))


def _clamp(z, cx, cy):
    hw, hh = W / (2 * z), H / (2 * z)
    return z, min(max(cx, hw), W - hw), min(max(cy, hh), H - hh)


def camera(t):
    """(zoom, centre x, centre y)."""
    wide = (1.0, W / 2, H / 2)
    hx, hy = cat_head(min(t, SPOOK))
    on_cat = (2.3, hx - 40, hy + 40)
    on_spot = (2.7, SPOT[0], SPOT[1])
    if t < PUSH[0] or T_WIDE <= t < FACE[0] or t >= PAN2[3]:
        cam = wide
    elif t < PAN1[0]:
        cam = _lerp3(wide, on_cat, ease((t - PUSH[0]) / (PUSH[1] - PUSH[0])))
        cam = (cam[0] + 0.25 * ease((t - PUSH[1]) / 1.3), cam[1], cam[2])     # a slow creep in
    elif t < PAN1[3]:
        a, b, c, d = PAN1
        k = ease((t - a) / (b - a)) * (1 - ease((t - c) / (d - c)))
        cam = _lerp3((2.55, on_cat[1], on_cat[2]), on_spot, k)
    elif t < T_WIDE:
        cam = (2.55 + 0.35 * ease_out((t - SPOOK) / 0.12), on_cat[1], on_cat[2] - 20)   # snap closer
        cam = (cam[0], cam[1] + 7 * math.sin(t * 80) * math.exp(-(t - SPOOK) * 3), cam[2])
    else:
        fx, fy = head_screen(t)
        on_face = (2.1, fx + 40, fy + 60)
        if t < PAN2[0]:
            cam = _lerp3(wide, on_face, ease((t - FACE[0]) / 0.6))
        else:
            a, b, c, d = PAN2
            k1 = ease((t - a) / (b - a))
            k2 = ease((t - c) / (d - c))
            cam = _lerp3(_lerp3(on_face, on_spot, k1), wide, k2)
    # the launch jolts the wide shot
    j = pulse(t, LAUNCH[0], LAUNCH[0] + 0.3)
    if j:
        cam = (cam[0] + 0.03 * j, cam[1] + 5 * math.sin(t * 90) * j, cam[2])
    return _clamp(*cam)


# ------------------------------------------------------------------ frames

def scene(ctx, t):
    room(ctx, t)
    bed_back(ctx)
    pillow(ctx)
    pose, expr, blink, look, talk, arms = girl_state(t)
    girl3.draw_girl(ctx, GIRL_X, GIRL_Y, GIRL_S, pose, expr, blink, look, talk, arms=arms)
    blanket(ctx, t, min(1.0, sit_amount(t)), cat_weight(t))
    draw_cat(ctx, t)


def frame(t):
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(s)
    z, cx, cy = camera(t)
    ctx.save()
    ctx.translate(W / 2, H / 2)
    ctx.scale(z, z)
    ctx.translate(-cx, -cy)
    scene(ctx, t)
    hx, hy = head_screen(t)
    if t < LAUNCH[0]:
        zzz(ctx, hx + 40, hy - 110, t, 1.0)
    if t > T_CURL + 0.5:
        zzz(ctx, P_FEET[0] + 50, P_FEET[1] - 280, t, 0.85, min(1, (t - T_CURL - 0.5) / 0.4))
    ctx.restore()
    # the words
    if SPOOK <= t < T_WIDE:
        shout(ctx, '!!', 760, 560, 190, (t - SPOOK) / 0.75, rot=0.12)
    if LAUNCH[0] <= t < LAUNCH[0] + 0.9:
        hx, hy = head_screen(t)
        shout(ctx, 'OOF!', hx + 60, hy - 170, 96, (t - LAUNCH[0]) / 0.9, rot=-0.12)
    if SAY[0] <= t < SAY[1] + 0.1:
        bubble(ctx, [('...what did', 78), ('you SEE?!', 104)], W / 2, 520, (W / 2 + 120, 860),
               (t - SAY[0]) / (SAY[1] - SAY[0]), shake=2 * math.sin(t * 50))
    if t < SNAP + 0.2:
        caption(ctx, '3 AM. All quiet.', W / 2, 220, 80, pop=min(1, t / 0.3))
    if t >= T_END_CAP:
        caption(ctx, "Great. Now I can't sleep.", W / 2, 220, 68, pop=min(1, (t - T_END_CAP) / 0.3), tilt=2)
    s.flush()
    return s


# ------------------------------------------------------------------ outputs

STILL_TIMES = [0.2, 0.6, 1.6, 2.6, 3.3, 4.4, 5.6, 6.9, 7.85, 8.45, 9.5, 10.6, 11.5, 13.0, 14.4, 16.8]


def stills():
    from PIL import Image, ImageDraw
    tw, th = 270, 480
    cols = 8
    rows = (len(STILL_TIMES) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * (tw + 8) + 8, rows * (th + 8) + 8), 'white')
    d = ImageDraw.Draw(sheet)
    for i, t in enumerate(STILL_TIMES):
        s = frame(t)
        a = np.ndarray((H, s.get_stride() // 4, 4), np.uint8, s.get_data())[:, :W]
        im = Image.fromarray(np.dstack([a[..., 2], a[..., 1], a[..., 0]]), 'RGB')
        x, y = 8 + (i % cols) * (tw + 8), 8 + (i // cols) * (th + 8)
        sheet.paste(im.resize((tw, th), Image.LANCZOS), (x, y))
        d.text((x + 6, y + th - 18), '%.1fs' % t, fill=(255, 0, 0))
    p = os.path.join(ROOT, 'output', 'spooked_stills.png')
    sheet.save(p)
    print(p)


def still(t, path):
    s = frame(t)
    s.write_to_png(path)
    print(path)


def _bytes(i):
    return bytes(frame(i / FPS).get_data())


def video(path, workers=4):
    from multiprocessing import Pool
    n = int(DUR * FPS)
    cmd = ['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'bgra', '-s', '%dx%d' % (W, H),
           '-r', str(FPS), '-i', '-', '-c:v', 'libx264', '-crf', '18', '-pix_fmt', 'yuv420p',
           '-movflags', '+faststart', path]
    pr = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool(workers) as pool:
        for i, data in enumerate(pool.imap(_bytes, range(n), chunksize=4)):
            pr.stdin.write(data)
            if i % 90 == 0:
                print('frame %d/%d' % (i, n), flush=True)
    pr.stdin.close()
    pr.wait()
    print(path)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'video':
        video(sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, 'output', 'spooked_silent.mp4'))
    elif len(sys.argv) > 2 and sys.argv[1] == 'still':
        still(float(sys.argv[2]), os.path.join(ROOT, 'output', '_sp_%s.png' % sys.argv[2]))
    else:
        stills()
