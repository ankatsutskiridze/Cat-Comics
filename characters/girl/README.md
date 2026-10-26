# The girl

- **MASTER reference: `girl_master_red.png`** (Anka's sheet with the hair recoloured to a
  clear red by `tools/recolor_hair.py`; Anka 2026-10-26: her hair is RED). Attach it to every
  image prompt with "exactly this character, same face". Every new image is compared to it.

- Design source: `reference_sheet_anka.jpeg` (Anka, 2026-10-26): long straight red-brown hair
  to the waist, side-swept fringe, ears showing; big dark eyes; sage-green crew-neck tee;
  dusty-pink cuffed shorts; white crew socks; chunky white sneakers; soft painted anime style.
- **Pipeline (Anka, 2026-10-26): images, not a code rig.** Anka generates each needed pose /
  expression in the same image tool, with the reference sheet attached, from prompts we
  write; the files land in `characters/girl/scenes/`; scenes cut them out and animate them
  (face swaps, small moves, camera). The code rig `lib/girl.py` + `girl_sheet_v1.png` was
  rejected (did not look like the sheet); kept only as a record.
