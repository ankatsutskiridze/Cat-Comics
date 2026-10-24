---
name: youtube-upload
description: Upload finished Shorts to YouTube through this PC's Edge via the Claude-in-Chrome extension and SCHEDULE them into the channel's slots around whatever is already scheduled or published — Studio upload form end to end (title, description, tags, audience, related video, schedule), then the pinned first comment once each goes live (plus short casual hearted replies), the ledger, and the move to final/uploaded/. Use whenever Anka says "upload these", "upload 5 videos", "schedule these shorts", "put these on YouTube", "pin the comments", or hands over a list of clips for YouTube.
---

# YouTube upload — scheduled Shorts

**Scope: 9:16 Shorts.** One clip = one upload of `<stem>_9x16.mp4`. Everything
mechanical (metadata parsing, order, slots, ledger, file moves) goes through
**`tools/yt_upload_prep.py`**, so it comes out the same every run; the browser part is
this file. Ledger: `final/YOUTUBE-UPLOADS.md` (created on the first `record`).
Slots/cadence: `SLOT_HOURS` / `PER_DAY` in the tool (Anka's call, see CLAUDE.md).

## 0. Browser + channel (every session)

1. [`docs/browser-setup.md`](../../../docs/browser-setup.md) §1-2: THIS PC's Edge,
   proven local.
2. **Anka has several channels — confirm THIS one before touching anything.** Open
   `https://studio.youtube.com/channel/<CHANNEL_ID>/videos/short` (ID from CLAUDE.md
   "Channel") and check BOTH: the URL still carries that ID after load (Studio redirects
   to the active channel when it can't open it) AND the sidebar / avatar menu shows this
   channel's name. Wrong → avatar → Switch account → this channel → re-check. Same check
   on youtube.com before posting a comment.

## 1. Pinned-comment pass — FIRST, every session

YouTube refuses comments on a scheduled video until it is live.
`python tools/yt_upload_prep.py due` lists ledger rows that are live now with their
comment `pending`. For each one:

1. Open `https://www.youtube.com/shorts/<ID>` → the comments button → the panel.
2. A thread already carrying `#pinned-comment-badge`: ours → just mark it; someone
   else's → leave it and ask Anka (pinning ours replaces it).
3. Identity: `#avatar-btn` → the active account header must be this channel.
4. `#simplebox-placeholder` → type the clip's pinned comment (from its row / `.md`;
   `shift+Return` between lines). Read back `#contenteditable-root` (its innerText DROPS
   emoji: check emoji on a zoomed screenshot) → submit `ytd-commentbox #submit-button button`.
5. Our new thread → its ⋮ "Action menu" → **Pin**, clicked BY REF. **Delete sits right
   under Pin**: never click by coordinates.
   **The first Pin click often doesn't register**: screenshot; if no "Pin this
   comment?" dialog appeared, click the same ref again. Confirm the dialog → "Pinned by
   @<handle>".
6. `python tools/yt_upload_prep.py pinned --url <url>`.

**One tab at a time**: comments don't render in a background tab, and acting in a second
tab can close the first tab's menu.

Posting comments is an external write; if the request was only "upload", Claude Code's
auto mode may refuse the pin pass. Then ask Anka to confirm it.

## 1b. Replies — casual, short, hearted

With a Short's comment panel open, reply the way a real creator does. **Never the
official voice** ("Thank you so much for watching! We're glad…").
- 1-4 words, or emoji only. A question gets a 2-3 word answer.
- Match their energy and emoji; vary loosely, never one pasted reply everywhere.
- **Heart every comment we reply to** (check it turned red on a screenshot).
- Skip spam, hate, anything that needs an argument. Never promise a video; a request
  goes to Anka in the report.
- The paced inbox run is `/youtube-comments`, not this.

## 2. Queue, order, metadata

1. **Clips**: Anka's list → each `_9x16.mp4` in `final/ready-to-upload/`. No list → pick
   yourself (never ask which): the premise absent from the channel longest first, then
   the one waiting longest. State the picks and a one-line reason in the report.
2. **Order = the order Anka wrote them in.** Random only when they didn't list them:
   `python tools/yt_upload_prep.py order <clips…>`.
3. **Metadata**: `python tools/yt_upload_prep.py meta <clips…>` → `title_options`
   (` #usa` appended, ≤100 chars), `description`, `tags`, `tags_yt_chars`, `comment`,
   `problems`. A non-empty `problems` → fix the `.md` first (CLAUDE.md "Upload metadata").
4. **Title**: Anka's pick if named; otherwise the strongest option by CLAUDE.md, and
   never a title the channel used in the last few weeks (ledger + Studio list).
5. No photosensitivity line on a Short.

## 3. Schedule slots

1. In Studio Content → Shorts, read every Short that is **Scheduled** and every one
   **published in the last ~24 h** (open its youtube.com page for "N hours ago"). Manual
   uploads count.
2. `python tools/yt_upload_prep.py slots --count N --existing "YYYY-MM-DD HH:MM" …`
   (Tbilisi times). **A slot is a target, not a gate**: a missed slot is never skipped,
   it goes out as soon as possible. **The one strict rule: ≥ 45 min between any two
   Shorts.** Always run the tool; never pick or skip a time by hand. If the form runs past
   the given time, re-run `slots` right before Schedule.
3. "Publish now" → `--immediate` (now+10 min as a SCHEDULE, never the Publish button).
4. State the plan (clip → time → title) in chat, then upload.

## 4. The upload form — one clip at a time

Open `https://studio.youtube.com/channel/<CHANNEL_ID>/videos/upload?d=ud`. Wait ~5 s, set
and lock a marker title (`docs/browser-setup.md` §2), then:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/activate_edge_tab.ps1 -TitleMatch "CCUPLOAD"
powershell -NoProfile -ExecutionPolicy Bypass -File tools/pick_file_dialog.ps1 `
  -Path "<abs path>\<stem>_9x16.mp4" -InvokeButton "Select files" -WindowTitleMatch "CCUPLOAD" -TimeoutS 40
```

**Details**
1. Title: focus the first `[contenteditable=true]` BY JS (a ref click + Ctrl+A once put
   the description into the title), select all, type the title. End with a trailing
   space so the `#usa` hashtag popup closes instead of autocompleting.
2. Description: the second contenteditable → paste the `.md` description.
3. **Show more** → Tags: focus `#tags-container input`, type the list ending in a comma,
   check the `N/500` counter.
4. Audience: tick **No, it's not made for kids** (`VIDEO_MADE_FOR_KIDS_NOT_MFK`) unless the
   channel default already sets it.
5. Read back before Next:
   `[...document.querySelectorAll('[contenteditable="true"]')].map(b=>b.innerText)`.

**Ad suitability** (appears once the channel is monetised): tick **None of the above** →
**Submit rating**; confirm on a screenshot that Submit went GREY (a first click once
didn't register) → Next.

**Video elements**: Related video → Add → search the title of the Short published just
before this slot → select. A still-scheduled Short is never offered: take the newest
public one and note it in the ledger.

**Checks**: Next.

**Visibility**: expand **Schedule** (never press Save on Unlisted).
1. Time zone → `(GMT+0400)` Tbilisi / Local Time.
2. Date → the slot's day (`studio_date`).
3. Time: typing doesn't stick. Click the field (the first click after the zone menu only
   closes that menu, so click again), `find` the `studio_time` option, scroll to it,
   click. Compare values after `.replace(/\s/g,' ')` (Studio uses a narrow no-break space).
4. Read back the date, zone and time, and check there is no "Select a time in the future".
→ **Schedule**. "We're still checking your content" → Got it. Read the URL BEFORE
clicking Schedule (`ytcp-uploads-dialog ytcp-video-info a`): the closing dialog sometimes
shows no link ("Video processing").

Don't start the next clip until this upload has finished (closing mid-upload loses it).

**Record** (ledger row + moves the 9:16, 16:9 and `.md` to `final/uploaded/`):
```
python tools/yt_upload_prep.py record --clip <9x16 path> --when "YYYY-MM-DD HH:MM" --title "<title as uploaded>" --url <url> --related "<related title>"
```

## 5. Verify + report

- Studio Content → Shorts: every new row is **Scheduled** at its slot time (hover
  tooltip). A "Video published" header on a scheduled clip has happened, so trust the list.
- `final/ready-to-upload/` no longer holds them.
- Report: table clip → time (Tbilisi) → title → URL; pinned comments pending until live.
- Then the `/youtube-comments` run, if Anka wants replies after uploads.

## Gotchas

- **NEVER press Escape inside the upload dialog**: it closes it (the upload survives as a
  draft: Content → Shorts → Edit draft). It has also closed on its own once; same recovery.
- UI language varies by account/run: check button text first, IDs (`#next-button`,
  `#done-button`, `#tags-container input`) work in any language.
- Another PC can publish mid-batch: a new top tile in the related-video picker is the
  tell. Re-run `slots` and move any of ours that are inside 45 min.
- Record every new UI fact from real runs in this file.
