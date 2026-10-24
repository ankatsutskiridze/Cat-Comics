# Browser setup — shared by youtube-upload, youtube-comments, youtube-analytics, crosspost

All YouTube/TikTok/Facebook work runs through THIS PC's Edge, driven by the
Claude-in-Chrome extension. Never ask which browser.

## 1. Pick THIS PC's Edge, and PROVE it

The same account has browsers on other PCs connected, and **the extension's `isLocal`
flag and display names are NOT proof**. Another PC's browser once reported `isLocal:true`,
got picked, and opened Studio on the wrong channel.

a. `Get-Process msedge` is empty → `Start-Process msedge`, wait ~8 s. Do this BEFORE
   listing browsers, so the other PC is never the only option.
b. THIS PC's proven deviceId lives in **`.claude/browser.local`** (gitignored; lines
   `deviceId=<id>`, `computer=<$env:COMPUTERNAME>`, `proven=<date>`).
   - The file exists AND `computer` equals `$env:COMPUTERNAME` → `list_connected_browsers`
     → `select_browser` with that deviceId, whatever its name. Still run step c.
   - The file is missing or `computer` differs → try each listed browser with step c; the
     one that proves LOCAL is this PC's. Write it to `.claude/browser.local`.
   - Never use a deviceId that has not passed step c this session.
c. **Proof:** serve a random-named file from the scratchpad with
   `python -m http.server <port> --bind 127.0.0.1` (background), `navigate` the tab to
   `http://127.0.0.1:<port>/<file>`; `get_page_text` shows the marker = LOCAL (localhost
   only resolves on the browser's own machine). Quick alternative: `navigate` to any https
   page, `javascript_tool` → `document.title='CCLOCAL-<random>'`, then
   `powershell -NoProfile -ExecutionPolicy Bypass -File tools/verify_local_browser.ps1 -Marker CCLOCAL-<random>`.
   That script gives a FALSE `NOT_LOCAL` when the tab is not the active tab of its window,
   so the localhost proof is the one that decides.
d. If the extension switches instances mid-session, re-select the SAME proven deviceId.

## 2. Tabs

- `tabs_context_mcp createIfEmpty:true` → work in that tab group.
- **`tabs_create_mcp` does NOT activate the new tab.** Before any OS file picker, run
  `powershell -NoProfile -ExecutionPolicy Bypass -File tools/activate_edge_tab.ps1 -TitleMatch "<page title>"`
  and check that it prints `ACTIVE:`. Sites reset `document.title` on route changes: set a
  marker title, and lock it with ONE MutationObserver per page load (guard with
  `if(!window.__lock){window.__lock=1; …}`). A second observer with a different title
  ping-pongs forever and freezes Edge.
- Keep the working tab ACTIVE: in a background tab, screenshots time out and comment
  panels never render.

## 3. Files into a page — `tools/pick_file_dialog.ps1`

The extension's `file_upload` caps at 10 MB (it is fine for a cover PNG). Videos go
through the real Windows picker:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools/pick_file_dialog.ps1 `
  -Path "<abs path>\<stem>_9x16.mp4" -InvokeButton "Select files" -WindowTitleMatch "<marker>" -TimeoutS 40
```

- Success ends with `DIALOG_CLOSED`. The path goes in with WM_SETTEXT, so it does not
  depend on the keyboard layout (a Georgian layout turns typed keys into Georgian letters).
- `NO_BUTTON` on the right tab = Edge did not expose the page to UIA. Start the script
  WITHOUT `-InvokeButton` in the background (it polls for the dialog), then click the page
  button with the extension's `computer left_click` on a fresh `find` ref. That click is a
  trusted gesture and opens the real picker.
- The first click after a `navigate` often misses (stale ref): re-`find`, click again.
- `FOREGROUND_FAILED` with the dialog open: a real mouse click on the dialog's title bar,
  then re-run with the same `-Path`.
- A failed run can leave its Open dialog alive, and the next run then appends to it.
  Close any leftover `#32770` dialog (PostMessage WM_CLOSE) before retrying.

## 4. Clicking

- Prefer `find` + click by `ref`. Screenshot coordinates are SCALED from CSS pixels; never
  reuse a coordinate from an earlier screenshot. If you need one, compute it fresh from
  `getBoundingClientRect()` × (frame width / `innerWidth`) in the same turn.
- Verify a click landed (`document.activeElement`, or a screenshot) before typing.
- **Ctrl+A in a rich editor can select the whole page**: focus the box by JS, or use
  End → Shift+Home.
- Never trigger JS alerts or confirm dialogs: they block the extension.
- Site permissions are per extension install: a fresh install needs studio.youtube.com /
  youtube.com / tiktok.com / facebook.com allowed by hand.
