---
name: crosspost
description: Upload a finished Short to TikTok and Facebook through this PC's Edge via the Claude-in-Chrome extension — drive the real Windows file picker, write the caption, upload a cover PNG, post or schedule, record in the ledger. Use whenever Anka says "upload this to tiktok/facebook", "post the next one", "crosspost", or hands over a clip path for the socials.
---

# Crosspost — TikTok + Facebook

YouTube leads; the socials follow with clips already on YouTube. Ledger:
**`final/CROSSPOST.md`** (date, platform, title, source file, URL, views later). Read it
first: a clip goes up ONCE per platform. Cadence and which accounts/Pages: Anka's call,
recorded here once decided. Never mass-upload a backlog.

## 0. Browser

[`docs/browser-setup.md`](../../../docs/browser-setup.md) end to end: proven local Edge,
the active-tab rule, the file picker, clicking by ref.
- **TikTok's login redirect kicks the tab out of the extension's group.** Navigate to
  `/tiktokstudio` FIRST, then `/tiktokstudio/upload`.
- If `activate_edge_tab.ps1` fails to foreground, use the ONE active tab for both
  platforms, `navigate`-ing it between them.

## 1. Pick the clip

Anka's path, or the oldest clip in `final/uploaded/` not yet in the ledger. Always the
`_9x16.mp4`.

## 2. TikTok Studio (`tiktok.com/tiktokstudio/upload`)

1. Picker: `-InvokeButton "Select video" -WindowTitleMatch "TikTok Studio"` (or the
   background-script + extension-click recipe). Wait for "Uploaded".
2. Dismiss "New editing features" (Got it).
3. Description: `find` the box, click its REF, then `End` → `shift+Home` → `Delete`, then
   type. **Never Ctrl+A here** (a missed click selects the whole page and the caption
   silently stays the filename). Type each hashtag WITH a trailing space and `Escape`
   after it (otherwise the suggestion list grabs the next click). Read back
   `document.querySelector('.public-DraftEditor-content').innerText`.
4. Cover: `find` the file input inside "Upload cover" → `file_upload` a PNG of the
   PUNCHLINE frame → Save.
5. Settings: Everyone · comments allowed · **AI-generated label: set it truthfully for how
   the video was made**.
6. Post → the Posts list shows "Only me" while TikTok transcodes; it flips by itself.
   Still "Only me" after 15 min → open the row's privacy dropdown.

**Schedule instead**: "When to post" → Schedule → Allow. The time field is read-only:
open the dropdown and click `span.tiktok-timepicker-option-text.tiktok-timepicker-left`
(hour) / `-right` (minute) via DOM `scrollIntoView` + `.click()` on the span AND its
parent. **Read the result off a SCREENSHOT**: the DOM input returns the old value.

## 3. Facebook Reel (`facebook.com/reels/create`)

**Verify the identity first**: the composer must post as the channel's Page, not the
personal profile. Wrong identity → STOP and switch.
1. Picker: `-InvokeButton "Add video or drag and drop" -WindowTitleMatch "Create reel"`. If
   the ref click fails twice, a coordinate click on the box centre works.
2. Next → Next → Reel settings → description.
3. Cover: click "Edit" on the thumbnail **EXACTLY ONCE**, then wait (up to ~25 s,
   spinner only). A second click stacks a second dialog and the composer can't be
   recovered (reload and redo). Poll with `find` for its file input → `file_upload` → Save.
4. "Your reel is safe to publish!" → Post.

**Schedule instead**: `Scheduling options` (often ignores the first click) → `find` the
time field, `triple_click` its REF, type `8:30 AM`, click the single `[role="option"]` at
coordinates computed fresh → Schedule for later. The "saved as a draft" toast afterwards
is misleading: verify in `facebook.com/professional_dashboard/content_calendar/` (Month
view).

## 4. Caption

The YouTube title (it is the proven hook; its emoji count) + one sentence of what happens +
3-5 relevant hashtags. Same text on both platforms. Never a competitor's name or tag.

## 5. After posting

Append the ledger row, close the tabs you created, never delete posts (Anka's call).
