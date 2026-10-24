---
name: youtube-analytics
description: Channel analytics readout — read YouTube Studio OFF THE SCREEN (no CSV/zip downloads) through this PC's Edge: overview, per-video table (views, stayed-to-watch, APV, AVD, subs), traffic / content type / country / age / gender breakdowns; write reports/<date>_analytics.md and update CLAUDE.md's evidence section where a rule moved. Use whenever Anka says "analyse the channel", "check studio", "how are the videos doing", "pull the analytics". Read-only on YouTube.
---

# YouTube analytics — read off the screen

**No downloads.** Numbers change daily and get re-checked often, so a check is a fast
read off the screen. Nothing is exported and no files are left behind.
**Read-only**: never edit a title, a visibility, a thumbnail or a comment.

## 0. Browser + channel

1. [`docs/browser-setup.md`](../../../docs/browser-setup.md): THIS PC's Edge, proven.
2. Confirm the channel: the URL keeps `<CHANNEL_ID>` (CLAUDE.md "Channel") after load
   AND the sidebar shows its name. An analysis of the wrong channel looks perfectly
   plausible, so this check is the whole guard. Channel-level URLs open by ID without
   switching the account; per-VIDEO pages (retention curves) need the account switched,
   so skip those unless Anka asks (another session may be using the browser).

## 1. What to read

- **Overview**: `studio.youtube.com/channel/<ID>/analytics/tab-overview/period-default`,
  28-day views / watch hours / subs + realtime 48 h.
- **Video table** (Advanced mode, driven BY URL, never by the pickers):
  ```
  https://studio.youtube.com/channel/<ID>/analytics/tab-overview/period-default/explore?entity_type=CHANNEL&entity_id=<ID>&time_period=lifetime&explore_type=TABLE_AND_CHART&metric=EXTERNAL_VIEWS&granularity=DAY&dimension=VIDEO&t_metrics=EXTERNAL_VIEWS&t_metrics=SHORTS_FEED_IMPRESSIONS_VTR&t_metrics=AVERAGE_WATCH_PERCENTAGE&t_metrics=AVERAGE_WATCH_TIME&t_metrics=SUBSCRIBERS_NET_CHANGE&o_column=EXTERNAL_VIEWS&o_direction=ANALYTICS_ORDER_DIRECTION_DESC
  ```
  Wait ~10 s, screenshot to confirm it rendered, then read the rows with JS:
  `[...document.querySelectorAll('yta-explore-table-row')].map(r=>r.innerText)`. Store
  them in `window.__r` and return ~7 rows per call (tool output truncates ~1,000 chars).
  The table shows 50 rows max: sort by `o_column=VIDEO_PUBLISH_DATE` DESC **and** ASC to
  cover every video.
- **Breakdowns**: the same URL with `dimension=TRAFFIC_SOURCE_TYPE` /
  `CREATOR_CONTENT_TYPE` / `COUNTRY` / `VIEWER_AGE` / `VIEWER_GENDER` /
  `DEVICE_PLATFORM_TYPE` / `SHARING_SERVICE`, read from a zoomed screenshot.
- Metric names: `SHORTS_FEED_IMPRESSIONS_VTR` = "Stayed to watch", `EPM` = RPM,
  `VIDEO_THUMBNAIL_IMPRESSIONS_VTR` = CTR, `TOTAL_ESTIMATED_EARNINGS`.

## 2. Studio traps

- `SUBSCRIPTION_SOURCE`, `DEVICE_TYPE` and `SUBSCRIBED_STATUS` are not usable dimensions
  (blank page / endless spinner). Selecting every metric breaks the query.
- **A hung explore page poisons the tab**: every later URL hangs too. Close it and continue
  in a fresh tab. After ~4-6 explore loads, start a fresh tab anyway.
- One navigation per tool call (batched navigations time out and land clicks on the wrong
  page).
- `get_page_text` cannot see Advanced mode (it is a dialog outside `<main>`): use the JS
  row read or screenshots.
- A dimension silently DROPS metrics it does not support: check the table before trusting
  a number.
- JS `.click()` doesn't sort columns; real mouse clicks do.
- Custom date range by URL: `time_period=<startMs>%2C<endMs>` (epoch ms of Pacific
  midnight).

## 3. The report — `reports/<DATE>_analytics.md`

Measure only Shorts ≥ 3 days old (younger ones are still climbing). Sections, kept in this
order so reports diff:
0. Headline: are we on a good path, overview numbers, delta vs the last report.
1. What changed since last time (and a "superseded" banner on the previous report).
2. Top / bottom videos with views, stay %, APV, subs.
3. **Stayed-to-watch vs views** (Spearman ρ with n), stay buckets, premise / character
   splits, length (expect flat; never argue length from one clip).
4. Audience (age, gender, country) and traffic.
5. Long-form, monetisation (once non-zero).
6. Recommendations, numbered, each tied to a number above.
7. What was not read.

Rules: every claim carries its number and n; say "n is small" under 6; raw likes/shares
are not evidence (rates only). Where a finding contradicts CLAUDE.md "What the sibling
channels' numbers taught", **this channel's data wins**: rewrite that section.
