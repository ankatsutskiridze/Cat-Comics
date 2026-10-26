"""Anka's movement demo (not an upload): everything the code-drawn girl (lib/girl3.py) can
do, in one take in the kitchen of scenes/full_bowl.py, with the cat (lib/cat3.py) watching:

walks in, waves, stretches with a yawn, hands on hips, shrugs, bends down and picks up a toy
mouse, tosses it, walks to the cat, crouches and pets it, stands up, turns round, walks to a
chair and sits down (talks, swings a foot), stands up, sits down on the floor, lies back and
falls asleep.

Usage: python scenes/anka_moves.py stills | video [out.mp4]
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
import full_bowl as K  # noqa: E402  (the kitchen, shadows, text)

W, H, FPS = 1080, 1920, 30
DUR = 25.0
GY, GS = 1800, 0.95                    # her feet line, scale
CAT_X, CAT_Y, CAT_S = 800, 1690, 0.58
CHAIR_X = 300
ease = K.ease
S = girl3.STATES

# ------------------------------------------------------------------ her path and poses
WALK = girl3.Walker(-150 / GS, [(0.0, 330 / GS), (10.0, 615 / GS), (14.6, CHAIR_X / GS)],
                    speed=300.0, stride=150.0)
TURN = (14.3, 14.6)                     # she turns round (faces left) before walking to the chair
PICK = 8.15                             # her hand reaches the toy
TOSS = 9.2                              # she lets go of it

SIT_X = CHAIR_X


def _st(name, **kw):
    d = dict(S[name])
    d.update(kw)
    return d


KEYS = [
    (0.0, S['arms_down']), (2.3, S['arms_down']),
    (2.6, S['wave']), (3.5, S['wave']),
    (3.8, S['stretch']), (4.7, S['stretch']),
    (5.0, S['hands_hips']), (5.8, S['hands_hips']),
    (6.1, S['shrug']), (6.8, S['shrug']),
    (7.1, S['arms_down']),
    (7.7, 'pick'), (8.25, 'pick'),
    (8.75, _st('arms_down', arm_n=dict(sh=10, el=60, hand='grip'))),
    (9.0, _st('arms_down', arm_n=dict(sh=-30, el=30, hand='grip'))),                     # wind up
    (9.25, _st('arms_down', arm_n=dict(sh=110, el=-10, hand='open'), lean=6)),           # toss
    (9.7, S['arms_down']), (10.9, S['arms_down']),
    (11.4, 'pet'), (13.0, 'pet'),
    (13.6, S['arms_down']), (16.2, S['arms_down']),
    (16.8, S['sit_chair']), (19.0, S['sit_chair']),
    (19.6, S['arms_down']), (19.9, S['arms_down']),
    (20.4, S['crouch']),
    (21.0, S['sit_floor']), (21.8, S['sit_floor']),
    (22.6, S['lie_back']), (25.0, S['lie_back']),
]


def girl_x(t):
    return WALK.x(t) * GS


def facing(t):
    """+1 = facing right (as drawn), -1 = left; a quick squash through the turn."""
    a, b = TURN
    if t < a:
        return 1.0
    if t >= b:
        return -1.0
    return math.cos(math.pi * (t - a) / (b - a))


def to_src(X, Y, gx, f):
    return 165 + (X - gx) / (GS * f), 1180 - (GY - Y) / GS


def state_at(t):
    for (ta, sa), (tb, sb) in zip(KEYS, KEYS[1:]):
        if ta <= t < tb:
            return sa, sb, ease((t - ta) / (tb - ta)), ta, tb
    return KEYS[-1][1], KEYS[-1][1], 0.0, KEYS[-1][0], KEYS[-1][0]


def pet_state(t, gx, f):
    """Crouched, the near hand on the cat's head, stroking."""
    st = dict(S['squat_pet'])
    pose, _ = girl3.body(st)
    sk = girl3._Skin(pose)
    sh = tuple(sk('shirt', np.array([girl3.SHOULDER['n']]), None)[0])
    stroke = 22 * math.sin((t - 11.4) * 2 * math.pi * 1.3)
    tx, ty = to_src(CAT_X - 40 + stroke, CAT_Y - 410, gx, f)
    arm = girl3.arm_ik('n', (tx, ty), bend=-1, shoulder=sh)
    arm.update(hand='open', wr=-30)
    st['arm_n'] = arm
    st.pop('arm_f', None)
    return st


def pick_state(t, gx, f):
    """Squats and reaches the toy on the floor with her near hand."""
    st = dict(S['crouch'], hip=(-10, 330), lean=58, nod=0.9, head=-14)
    pose, _ = girl3.body(st)
    sk = girl3._Skin(pose)
    sh = tuple(sk('shirt', np.array([girl3.SHOULDER['n']]), None)[0])
    tx, ty = to_src(TOY_FLOOR[0], TOY_FLOOR[1] - 55, gx, f)
    arm = girl3.arm_ik('n', (tx, ty), bend=-1, shoulder=sh)
    arm.update(hand='grip' if t >= PICK else 'open')
    st['arm_n'] = arm
    st.pop('arm_f', None)                       # the far hand stays behind her back
    return st


def girl_state(t):
    gx = girl_x(t)
    f = facing(t)
    sa, sb, k, ta, tb = state_at(t)
    if sa == 'pick':
        sa = pick_state(t, gx, f)
    if sb == 'pick':
        sb = pick_state(t, gx, f)
    if sa == 'pet':
        sa = pet_state(t, gx, f)
    if sb == 'pet':
        sb = pet_state(t, gx, f)
    st = girl3.blend(sa, sb, k)
    # walking overrides the legs while she moves
    mv = WALK.moving(t)
    walk = None
    if mv > 0.02 and not st.get('hip'):
        walk = (float(WALK.ph[WALK._i(t)]), float(WALK.st[WALK._i(t)]))
    pose, arms = girl3.body(st, walk)
    # hair swing on the walk; a stretch yawn; expression
    ph = 2 * math.pi * float(WALK.ph[WALK._i(t)])
    hl = -2.5 * mv + 2.5 * math.sin(ph * 2 - 0.9) * mv
    for b in ('lockL', 'lockR', 'lockF'):
        q = dict(pose.get(b, {}))
        q['rot'] = q.get('rot', 0.0) + hl
        pose[b] = q
    expr, talk, blink, look = 'smile', 0.0, 0.0, (0.0, 0.0)
    for bt in (1.4, 5.3, 10.2, 13.8, 18.2, 21.3):
        if bt <= t < bt + 0.16:
            blink = math.sin((t - bt) / 0.16 * math.pi)
    if 2.6 <= t < 3.6:
        expr = 'happy'
    elif 3.8 <= t < 4.8:
        expr = 'sleep'                              # the yawn
        talk = 0.0
    elif 5.0 <= t < 5.9:
        expr = 'annoyed'
    elif 6.1 <= t < 6.9:
        expr = 'neutral'
    elif 7.4 <= t < 8.8:
        look = (0.6, 0.9)
    elif 9.0 <= t < 10.0:
        expr = 'happy'
    elif 11.4 <= t < 13.0:
        expr = 'happy'
        look = (0.6, 0.8)
    elif 17.2 <= t < 19.0:
        talk = abs(math.sin((t - 17.2) * math.pi * 4.2)) if t < 18.6 else 0.0
    elif t >= 22.6:
        expr = 'sleep'
    if expr == 'sleep' and 3.8 <= t < 4.8:
        talk = 0.8 * math.sin(min(1, (t - 3.9) / 0.8) * math.pi)    # mouth open in the yawn
        expr = 'smile'
        blink = 1.0
    # the foot swings while she sits on the chair
    if 17.0 <= t < 19.0:
        st2 = dict(st)
        sw = 20 * math.sin((t - 17.0) * 5)
        st2['n'] = (st['n'][0] + sw, st['n'][1] - abs(sw) * 0.4, 0)
        pose, arms = girl3.body(st2)
    return gx, f, pose, arms, expr, blink, look, talk


# ------------------------------------------------------------------ the toy mouse

def toy(ctx, x, y, rot=0.0, k=1.0):
    ctx.save()
    ctx.translate(x, y)
    ctx.rotate(rot)
    ctx.scale(k, k)
    ctx.move_to(-24, 2)
    ctx.curve_to(-50, 6, -54, -18, -70, -10)
    ctx.set_source_rgb(*K.INK)
    ctx.set_line_width(4)
    ctx.stroke()
    ctx.save()
    ctx.scale(1.0, 0.62)
    ctx.arc(0, 0, 28, 0, 2 * math.pi)
    ctx.restore()
    ctx.set_source_rgb(0.62, 0.62, 0.66)
    ctx.fill_preserve()
    ctx.set_source_rgb(*K.INK)
    ctx.set_line_width(4)
    ctx.stroke()
    ctx.arc(14, -14, 9, 0, 2 * math.pi)
    ctx.set_source_rgb(0.95, 0.65, 0.68)
    ctx.fill_preserve()
    ctx.set_source_rgb(*K.INK)
    ctx.stroke()
    ctx.arc(22, -2, 2.6, 0, 2 * math.pi)
    ctx.fill()
    ctx.restore()


TOY_FLOOR = (520.0, 1792.0)


def toy_prop(ctx, Wr, ha):
    ctx.save()
    ctx.translate(Wr[0], Wr[1])
    ctx.rotate(-math.radians(ha))
    toy(ctx, 0, 46, 1.4, 1.0 / GS)
    ctx.restore()


# ------------------------------------------------------------------ the cat

def cat_state(t, gx):
    mood, roll, yaw, look, nod = 'deadpan', 1.5 * math.sin(t * 1.1), 0.0, (0.0, 0.0), 0.0
    blink = 0.0
    for b in (2.0, 6.5, 15.5, 20.0):
        if b <= t < b + 0.18:
            blink = math.sin((t - b) / 0.18 * math.pi)
    # watches her
    dx = (gx - CAT_X) / 400
    yaw = max(-0.8, min(0.8, dx))
    look = (max(-1, min(1, dx)), -0.3)
    if 2.6 <= t < 3.6:
        mood = 'confused'
    if 9.25 <= t < 10.5:                       # follows the toy flying off
        mood = 'surprised'
        k = ease((t - 9.25) / 0.5)
        yaw, look = 0.8 * k, (1.0 * k, -0.6 + 0.4 * k)
    if 11.4 <= t < 13.2:                       # being petted
        mood = 'content'
        roll += 6 * math.sin((t - 11.4) * 2 * math.pi * 1.3)
    if t >= 22.6:
        mood = 'sleepy'
    return dict(mood=mood, blink=blink, look=look, head_roll=roll, head_yaw=yaw, head_nod=nod,
                breathe=math.sin(t * 2 * math.pi / 2.4))


# ------------------------------------------------------------------ the chair

def chair(ctx):
    seat_y = GY - (1180 - (640 + 185 + 45)) * GS
    x0, x1 = CHAIR_X - 120, CHAIR_X + 110
    for lx in (x0 + 14, x1 - 34):
        K._box(ctx, lx, seat_y + 20, lx + 22, GY - 4, (0.62, 0.40, 0.24), 6, 6)
    K._box(ctx, x1 - 30, seat_y - 360, x1 - 8, seat_y + 10, (0.62, 0.40, 0.24), 6, 6)    # backrest post
    K._box(ctx, x1 - 40, seat_y - 360, x1 + 2, seat_y - 250, (0.72, 0.48, 0.30), 6, 10)
    K._box(ctx, x0, seat_y - 6, x1, seat_y + 26, (0.76, 0.52, 0.32), 6, 10)


# ------------------------------------------------------------------ frames

def frame(t):
    s = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    ctx = cairo.Context(s)
    z, zc = 1.12, (560.0, 1660.0)
    ctx.save()
    ctx.translate(*zc)
    ctx.scale(z, z)
    ctx.translate(-zc[0], -zc[1])
    K.kitchen(ctx, t)
    chair(ctx)
    K.shadow(ctx, CAT_X, CAT_Y + 4, 120, 16, 0.18)
    gx, f, pose, arms, expr, blink, look, talk = girl_state(t)
    cat3.draw_cat_front(ctx, CAT_X, CAT_Y, CAT_S, **cat_state(t, gx))
    if t < PICK:
        toy(ctx, *TOY_FLOOR)
    if PICK <= t < TOSS and arms and 'n' in arms:
        arms['n']['prop'] = toy_prop
    K.shadow(ctx, gx + 8 * f, GY + 2, 150, 20, 0.16)
    ctx.save()
    ctx.translate(gx, GY)
    ctx.scale(f if abs(f) > 0.05 else 0.05, 1)
    ctx.translate(-gx, -GY)
    girl3.draw_girl(ctx, gx, GY, GS, pose, expr, blink, look, talk, arms=arms)
    ctx.restore()
    if TOSS <= t < TOSS + 0.9:                  # the toy flies off to the right
        u = (t - TOSS) / 0.9
        toy(ctx, 470 + 900 * u, 1250 - 700 * u + 900 * u * u, u * 9)
    ctx.restore()
    s.flush()
    return s


def stills():
    from PIL import Image
    ts = [1.0, 3.0, 4.2, 5.4, 6.4, 8.0, 9.25, 12.0, 14.45, 15.5, 17.8, 20.5, 21.4, 23.5]
    tw, th = 216, 384
    cols = 7
    sheet = Image.new('RGB', (cols * (tw + 6) + 6, 2 * (th + 6) + 6), 'white')
    for i, t in enumerate(ts):
        sf = frame(t)
        a = np.ndarray((H, sf.get_stride() // 4, 4), np.uint8, sf.get_data())[:, :W]
        im = Image.fromarray(np.dstack([a[..., 2], a[..., 1], a[..., 0]]), 'RGB')
        sheet.paste(im.resize((tw, th), Image.LANCZOS), (6 + (i % cols) * (tw + 6), 6 + (i // cols) * (th + 6)))
    p = os.path.join(ROOT, 'output', 'anka_moves_stills.png')
    sheet.save(p)
    print(p)


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
        for data in pool.imap(_bytes, range(n), chunksize=4):
            pr.stdin.write(data)
    pr.stdin.close()
    pr.wait()
    print(path)


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'video':
        video(sys.argv[2] if len(sys.argv) > 2 else os.path.join(ROOT, 'output', 'anka_moves.mp4'))
    else:
        stills()
