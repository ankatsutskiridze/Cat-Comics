# Living characters: mesh rigs built from the drawings

The drawings ARE the characters. Each one gets a triangle mesh bound to bones
(`lib/rig.py`, Live2D-style). Poses bend the mesh and the drawing is resampled through it,
so the character moves without seams. Faces change by swapping textures on the same mesh
(blink, talk, moods), so the warp carries them along with the head.

| actor | file | drawing | does |
|---|---|---|---|
| `CatSit` | `lib/cat_rig.py` | Gemini sheet sitting body + its 8 expression heads | breathe, blink, tilt / nod / turn head, ear flicks, crouch, meow, jump (x/y/rot/crouch tracks), moods |
| `CatWalk` | `lib/cat_walk.py` | `characters/cat/poses/walk_side.png` | 4-leg walk gait (planted feet), body bob, head nod, tail sway; mirrors to walk right |
| `CatBust` | `lib/cat_bust.py` | `characters/cat/poses/face_deadpan.png` | close-up: breathe, tilt, ear flick, slow blink, talk (`words`) |
| `GirlStand` | `lib/girl_stand.py` | master sheet big figure, `characters/rig/girl_src.png` | stroll (hands behind back), stand, breathe, weight shift, lean, tilt / nod / turn head, blink, talk, hair on spring physics |
| `BedGirl` | `lib/girl_bed.py` | `bed_sleep` / `bed_awake` / `bed_annoyed` | lying in bed: breathe, head roll, twitches (`jolt`), faces sleep / awake / annoyed, blinks |
| `ShoutGirl` | `lib/girl_bed.py` | `sit_shout` | sits up with a spring, jaw on the words (`talk`), head shake, arm tremble, hair sway, lunge |

## Directing

Every actor is driven by tracks (`Track.key(t, value[, ease])`, `Steps.set(t, value)`) and
event lists, then drawn per frame:

```python
cat = CatSit(x=690, y=1600, height=400, mood='deadpan')
cat.yaw.key(0.8, 0).key(1.2, -0.7)        # turn its head toward her
cat.mood.set(1.6, 'surprised')
cat.meow(3.6, 0.55)
girl = GirlStand(x=-260, y=1790, height=1300)
girl.x.key(0.2, -260).key(2.7, 330)       # she walks in...
girl.walk.key(0.2, 1).key(2.35, 1).key(2.75, 0)
girl.tilt.key(2.9, 0).key(3.3, 7)         # ...and looks down at the cat
cat.draw(frame, t); girl.draw(frame, t)   # frame = PIL RGBA
```

Worked scenes: `scenes/alive_rig.py` (room), `scenes/night_meow_alive.py`,
`scenes/night_shift_alive.py` (bedroom).

## Adding a drawing as a new rig

1. Cut it with `tools/cut_rig_source.py` (keeps eye whites, socks and sneakers).
2. Put a grid on it, read pivots off it, and write bones (`name: (parent, pivot)`).
3. Weight maps = smooth regions per bone. Parts that swing over each other (near / far
   legs, hair locks over the shirt) go in separate `layers`; a layer can carry its own weight
   maps so two touching legs never drag each other's edges.
4. Face variants are copies of the drawing with the lids / mouth painted in, added with
   `add_texture`; a layer-specific copy is `'<name>@<layer>'`.

Limits: a rig bends ONE drawing. Big turns (front to side), sitting down / standing up and
lying to sitting need another drawing (a new rig) and a cut or a fast move between them.
