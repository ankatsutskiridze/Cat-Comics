# CAT COMICS (working name) — READ THIS FIRST

A NEW YouTube channel, started 2026-10-25. It is a separate channel from
**NEFI & SNOOPY** (`D:\projects\Nefertit Sims`) and **Satisfying 2D Sims**
(`D:\projects\satisfying-2d-sims`), and its content shares NOTHING with them:
no physics simulations, no Nefi / Snoopy / Lucy / Anka rigs, no neon-on-black,
no "one note per collision", no sim captions or counters, no megamix-of-sims
formats. **Only YouTube know-how was carried over**: upload, comments,
analytics, crossposting, metadata rules, what the sibling channels' numbers
taught us, and video-tech gotchas. Never import code, characters or style
from those repos into this one.

## The format

Short comic-style animated Shorts in the spirit of **@equmiart's Instagram
reels**: a relatable everyday moment (a pet and its human at home), told in
~15-25 s by flat hand-drawn cartoon art, a one-line setup caption, and a
punchline close-up. Breakdown of the reference reel, beat by beat:
[`research/reference-equmiart.md`](research/reference-equmiart.md).

- **A REFERENCE IS ADAPTED, NEVER COPIED.** Keep the KIND of premise
  ("pets do X for no reason") and the storytelling grammar (wide shot, setup
  caption, escalation, close-up punchline). Change the specifics: our own
  characters, our own jokes, our own look, our own sound. A viewer must never
  read one of ours as a copy of a creator's video.
- **Never a competitor's name, character, logo or wordmark** on screen, in a
  title, description, tag or comment ("equmi" included).
- Reference URLs are downloaded with `yt-dlp` and read as FRAMES (a page fetch
  of a video URL tells you nothing):
  `yt-dlp --js-runtimes node -f "bv*+ba/b" -o "research/reference-videos/ref_<slug>.%(ext)s" --no-playlist "<url>"`,
  then `ffmpeg -i <file> -vf fps=1 ...` and read the PNGs. Instagram reels
  download without login.

## Open decisions (Anka's — ask, don't assume)

1. Channel name, handle, channel ID (fill in **Channel** below; every skill
   reads it from there).
2. The main characters. **The cat (Anka, 2026-10-26: "exactly this cat")** =
   the Gemini sheet `characters/cat/reference_sheet_gemini.jpg`, made as images
   like the girl; see **The cat** below. **The girl (Anka, 2026-10-26)** = Anka's reference
   sheet `characters/girl/reference_sheet_anka.jpeg`. A code-drawn version
   (`lib/girl.py`, sheet v1) was REJECTED: it did not look like the sheet. She is
   made as IMAGES Anka generates in the same image tool (prompts from us, per
   pose/expression), cut out and animated in code. Still open: the cat's name.
3. How the animation is PRODUCED (the pipeline). Decide on the first video
   and record it here.
4. Sound: **TRIAL (Anka, 2026-10-25): no music, our own synthesised sound
   effects** (`lib/sfx.py`, timed per scene, e.g. `scenes/litter_frenzy_audio.py`;
   files + README in `sound/`). Anka wants popular songs but those cannot go in a
   file we upload. YouTube Audio Library was checked and REJECTED by Anka
   (2026-10-25: the tracks are too weak to be worth using).
5. Upload slots and cadence (the tool defaults to the siblings' 5/day US
   window until changed: `SLOT_HOURS` / `PER_DAY` in `tools/yt_upload_prep.py`).

## The cat (Anka, 2026-10-26)

- Look: [`characters/cat/reference_sheet_gemini.jpg`](characters/cat/reference_sheet_gemini.jpg)
  (Gemini, from `characters/cat/prompt_cat_sheet.md`): soft-black body, thin dark-brown
  outline, cream eyes with slit pupils, tiny pink nose, spiky cheek fur, small fur tufts,
  long tail with a rounded tip. **No coloured marks or drawings anywhere on the cat.**
- Made as IMAGES, like the girl: Anka generates poses in Gemini with the sheet
  attached; `python tools/cut_cat_poses.py <sheet.jpg> <name>...` cuts each pose out to
  `characters/cat/poses/<name>.png` (RGBA). Sources in `characters/cat/poses/src/`.
- The old code rig `lib/cat.py` (graffiti cat, sheet v4) is NOT this cat; it stays
  only because `scenes/litter_frenzy.py` uses it.

## Channel

- Name: _TBD_ · Handle: _TBD_ · Channel ID: _TBD_
- On Anka's Google account next to NEFI & SNOOPY / Satisfying 2D Sims / Pink
  Simulations — **confirm the channel before every upload, reply or
  analytics read** (Studio opens on whichever channel was used last).

## People and language

- The person in chat is **Anka** (they/them unless told otherwise). Luka also
  works on the channels. **Chat in Georgian** — every message, status lines
  too. Titles, descriptions, tags, docs and code stay in English.
- Anka reviews at fine detail and wants to be corrected: if a suggestion is
  wrong, say so plainly with the evidence, then do what they decide.

## Workflow

1. Idea / reference → a short beat list (setup, escalation, punchline).
2. **Look first, as STILLS**: key frames for approval before any full render.
   Small fixes: show a still or a fast preview first, then the full render
   with an honest ETA.
3. Full clip → `final/needs-review/` as `<stem>_9x16.mp4` + `<stem>.md`.
   `output/` is disposable scratch: a clip waiting for Anka's verdict never
   lives there only.
4. **Approval must be explicit.** A short or ambiguous message is not a green
   light; ask in one line. Approved → `final/ready-to-upload/`, uploaded →
   `final/uploaded/` (the `youtube-upload` skill moves it). A clip always
   moves with ALL its files.
5. Multi-video requests: no plan walkthrough, build them all, stage them to
   `needs-review/`, one final message with a link to every mp4.
- **Change only what was asked.** One named defect = one minimal change; a
  nearby improvement is a one-line suggestion, never folded in.
- **Never remove a visible feature as part of a fix without asking.**
- When Anka describes a moment they saw, find that exact frame before
  touching anything.

## Sound

- The reference runs a pop song under the whole clip. **We never put a
  copyrighted song into a file we upload** (Content ID claims, blocked or
  demonetised videos, and it can cost YPP). Use tracks we hold a licence for
  (royalty-free with the licence saved next to the file) or CC0 / public
  domain recordings; every sound file gets its source + licence in a
  `README.md` beside it.
- Master to **-14 LUFS integrated, measured in STEREO on the muxed mp4**; keep
  the decoded peak under -1 dBFS (AAC overshoots: measure the mp4, not the wav).
- No silent head: something audible from frame 0.

## Upload metadata — every Short, unasked, in chat AND in `<stem>.md`

`<stem>.md` sections (the names are load-bearing — `tools/yt_upload_prep.py
meta` parses them): `# <title>`, what happens, `## Titles`, `## Pinned comment`,
`## Description`, `## Tags`.

- **Titles: 3-4 options of DIFFERENT types** (reaction · relatable statement ·
  question · POV / "when your cat…" · number), each with **1-3 emoji** that
  the clip earns, ending in ` #usa` (the siblings' US-audience convention;
  re-test here once there is data). ≤ 100 chars. One formula across a whole
  channel reads as templated.
- **Pinned comment**: one line that invites a reply ("does yours do this
  too? 👇"). Never promise a video.
- **Description** (English, no hashtags): 1-2 sentences of what happens, then
  the channel's brand line (decide it with the channel name).
- **Tags filled to ~490-499 of YouTube's 500.** YouTube counts commas and +2
  quotes per multi-word tag:
  `sum(len(t)+2*(' ' in t) for t in tags)+len(tags)-1` (`meta` prints it as
  `tags_yt_chars`). Order: brand → this clip's topic → genre (cat cartoon,
  funny cat, cat animation, cat comic, relatable…) → format (2d animation,
  shorts animation…). Never a competitor's name.
- Every number in a title or description is true of the clip.
- **Don't reuse a title within a few weeks**: two uploads with the same title
  cannibalise each other.
- Shorts never carry a photosensitivity line; a long-form upload with
  flashing content does.

## What the sibling channels' numbers taught (evidence; re-check here)

From NEFI & SNOOPY (n=41 Shorts, 2026-10-19) and Satisfying 2D Sims (n=133
mature Shorts, 2026-09-09). Treat these as starting priors. **Once this
channel has its own data, its own numbers win** and this section gets
rewritten.

- **Stayed-to-watch is the #1 reach predictor** (ρ +0.74 / r +0.59). Views
  jump at a cliff (~65-70% stay); every breakout sat above it.
- **The opening decides.** 0-3 s is the swipe; **seconds 4-10 separate
  winners from losers** (15-21 pts lost vs 25-49). Something must MOVE in the
  first 2 s, and the premise must be clear by second 3-5.
- **Length is flat** from 20-60 s: never tune length, tune the opening and
  the escalation. Cut dead time, never a beat (setup → escalation → payoff).
- An exit right at the punchline is healthy (payoff-leavers), not a defect.
- **Home life with the human was NEFI's top premise** (5 of 5 above 580K,
  median 748K vs 85K for the rest). That is this channel's whole genre, which
  is the reason to make it. NEFI's audience: 71% aged 25-44, 62% female.
- **Raw likes and shares are not evidence** (views cause them). Only rates are.
- **Cadence:** 5 Shorts/day did not dilute meaningfully on the old channel. A
  3/day test LOST (+20% per clip, but -30-46% per upload day). Mild dilution
  is cheap; missing uploads are not.
- **Franchise the winners within days, with ONE change a viewer could name.**
  Cosmetic-only re-uploads are what YouTube's inauthentic-content policy
  targets, and that policy gates YPP.
- **Long-form is where the money is** (old channel: long-form = 90% of revenue
  on 26% of views). A compilation runs **8:00-10:00** (mid-roll ads need 8:00),
  the **highest-stay clip goes first** (~35% of viewers leave in the first
  ~55 s), and it cuts straight from clip to clip (each black title card cost
  ~1.2 audience points). Do this only once there are enough Shorts, and only
  with tracks licensed for long-form.
- **Comment replies:** a reply-to-a-comment video had the best subscriber
  rate on the old channel.

## Skills (this repo)

- `/youtube-upload`: schedule Shorts in Studio, pinned comment, ledger, move
  to `uploaded/`. Mechanics in `tools/yt_upload_prep.py`.
- `/youtube-comments`: answer comments only when Anka says so (or after an
  upload session), ~15 videos per run, one reply every 40-60 s.
- `/youtube-analytics`: read Studio OFF THE SCREEN (no CSV downloads), write
  `reports/<date>_analytics.md`.
- `/crosspost`: TikTok + Facebook uploads.
- Browser setup shared by all four: [`docs/browser-setup.md`](docs/browser-setup.md).

## Video-tech gotchas (verified on this PC)

- Encode: libx264, crf 18, yuv420p, `-movflags +faststart`; mux
  `-c:v copy -c:a aac -b:a 384k -shortest`. **When RE-muxing new audio onto a
  muxed clip, drop `-shortest`**: it can discard the last frames. Check
  `nb_read_packets` afterwards.
- yuv420p needs EVEN width/height. Shorts are 1080x1920 (or 2160x3840).
- Two renders writing the same output path corrupt the mp4 silently (ffmpeg
  exits 0, "Invalid NAL unit size" on decode).
- **4K renders run ONE AT A TIME on this PC** (it is shared with other
  sessions' renders; a second concurrent 4K encode died from lack of RAM).
- Stopping a background bash script with TaskStop leaves its loop alive: find
  its PID by its OWN script name (`Get-CimInstance Win32_Process`) and
  `taskkill /PID <pid> /T /F`. Never pattern-kill `python`/`multiprocessing`:
  other sessions' renders run here too.
- The first run on a cold font cache rasterises text slightly differently; to
  bit-compare two renders, compare the second run of each.
- `ffmpeg overlay` with a delayed input drops frames at the junction: build
  the delayed video as a file first, and encode overlay output with
  `-fps_mode cfr`.
- pyloudnorm needs float64 `(samples, channels)` and returns -inf on silence.

## Git

**Never run `git commit` unprompted. No `Co-Authored-By` / AI-attribution
trailer in a commit message, ever.** Leave the work in the tree and report
what is ready.

## Knowledge lives in the repo

Machine-local memory does not travel; durable rules go in this file, `docs/`
or `.claude/skills/`. Keep them terse: rules and numbers.
