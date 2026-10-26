# Cat poses (cut-outs)

Source: Gemini images Anka generated on 2026-10-26 with `../reference_sheet_gemini.jpg`
attached (`src/poses_a_src.jpg`, `src/poses_b_src.jpg`, 896x1200 each). Cut with
`python tools/cut_cat_poses.py <src> <names...>` (RGBA, trimmed, 8 px pad).

| file | pose | size px |
|---|---|---|
| `sit_meow.png` | sitting, looking up, mouth wide open, eyes closed | 379x556 |
| `sit_look_up.png` | sitting, looking up, mouth closed, eyes open (NOT a mouth-only twin of `sit_meow`: eyes and head differ) | 384x554 |
| `lean_meow.png` | standing, back arched, leaning down, meowing | 432x538 |
| `walk_side.png` | walking, side view, tail up | 430x487 |
| `held_bored.png` | held up under the front legs by two hands (forearms fade out), bored eyes | 373x971 |
| `look_back_meow.png` | sitting, head turned up to the side, meowing (not a look over the shoulder) | 332x659 |
| `face_deadpan.png` | face close-up, deadpan; the right cheek spikes are cut by the source's edge | 394x542 |
