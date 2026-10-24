---
name: youtube-comments
description: Answer viewer COMMENTS in YouTube Studio through the browser — read the unanswered inbox, write one individual reply per comment at a human pace, verify each one posted, report the count. Use ONLY when Anka says to ("answer the comments", "reply to the new comments", "გაეცი პასუხები"), or at the end of an upload session when Anka wants replies after uploads.
---

# Answering viewer comments

**Never on my own initiative.** No daily automation, no "I noticed new comments so I
replied". It runs when Anka says so, and stops when they say stop.

**Scope: ~15 videos' worth of comments per run**, then report and stop. Text replies (and
hearts) only: no pins (that is `/youtube-upload` §1), no moderation, no deleting.

## 0. Browser + channel

1. [`docs/browser-setup.md`](../../../docs/browser-setup.md): THIS PC's Edge, proven.
2. **Confirm the channel** (CLAUDE.md "Channel") in the sidebar / avatar before typing.
3. Unanswered inbox:
   ```
   https://studio.youtube.com/channel/<CHANNEL_ID>/comments/inbox?filter=%5B%7B%22name%22%3A%22RESPONDED%22%2C%22value%22%3A%7B%22responded%22%3Afalse%7D%7D%5D
   ```
   The list is virtualised and lazy-loads, so the total is never known. Never quote one.

## 1. Pace — the whole point

**One reply every 40-60 s, never a burst.** The account must not read as a bot. After
several fast posts Studio starts answering with an error toast (in Georgian UI:
`სამწუხაროდ, წარმოიქმნა შეცდომა`).
- Error toast → wait ~30 s, retype, resubmit (the text is gone and the reply did NOT post).
- Never "catch up" after a slow patch.

## 2. Writing the replies

- **Every reply is written for that one comment.** No template, no reused sentence.
- **Answer what they said**: vary length and tone, reply in their language.
- Short and casual, the maker's voice: never marketing, never "thanks for watching,
  subscribe". At most one emoji, only where it lands.
- An idea comment gets an honest reaction, never a promise of a video or a date.
- Skip hostile or spam rows. Anything needing a decision (collab, business, complaints)
  goes to Anka.
- Heart the comments we reply to.

## 3. Posting mechanics

- The video a comment was left on is in the RIGHT column of the same row (in
  `get_page_text` its title prints after the comment).
- Scroll the row into the top third first (the reply box opens below the row).
- Reply button on the row → the box opens focused → type → **screenshot before submit**
  (confirm the text sits under the RIGHT comment) → submit.
- **A successful post re-renders the list**: a box typed into while that lands is cleared
  silently. **The toast is not proof**: check the row's counter went `0` → `1 reply`.
- Refs go stale between renders; re-`find`, or click from a fresh screenshot.

## 4. Report

How many replies were posted, across how many videos, which ones errored and were retried,
and a short list of notable comments still unanswered (video requests especially).
