# Measuring a recording → project.json

Every recording is different (Zoom vs Meet vs Teams, floating window vs full screen, dark vs light apps).
Don't guess and don't hard-code: LOOK, then MEASURE with `scripts/frames.py`, then write the numbers.
`V=<video>`, `F="$PY $SKILL/scripts/frames.py"`. All coordinates are source pixels `[x, y, w, h]`, times source seconds.

## 1. Look
`$F sheet $V edit/verify/sheet.jpg --every 45` (add `--start/--end` to zoom into a stretch). From the sheet note:
- when the screen is shared vs camera-only (speaker view)
- which apps/windows appear in the share, and whether the window floats on a wallpaper or fills the share
- where the presenter's face thumbnail sits during the share (Zoom: top-right, ~258x146)
- anything sensitive: URL bars with IDs, emails, names (students, customers), notifications

## 2. Mode: share vs talk (`classify.mode`)
Zoom draws a green border around a shared screen. Find it: `$F grab $V <share second> edit/verify/g.png` and look,
then `$F colscan $V <t> <y0,y1> <x0,x1>` across the left edge to find the border column and its colour
(`$F probe $V <x,y,4,400> <t>` gives the RGB). Confirm with `$F share $V <x,y,4,400> <r,g,b> --tol 60`: it prints
ON/off ranges; they must match what you saw on the sheet.
No green border (Meet, Teams, local recordings)? Pick any region that differs reliably between share and camera
(e.g. a toolbar that only exists during sharing, or the camera tile's background) and use its colour the same way.
→ `"mode": {"probe": [x, y, w, h], "share_rgb": [r, g, b], "tol": 60}`

## 3. Screen crop(s) (`crops.share`)
For each app/window seen during the share, grab a frame and find the content area:
- left/right window edges: `$F colscan $V <t> <y0,y1> <x0,x1>` (look for the `<-- edge` marks)
- top: `$F rowscan $V <t> <x0,x1> <y0,y1>` from the window top down; the LAST strong edge in the first ~110px is the
  bottom of the tab bar + URL bar (browser) or title bar (apps). Crop below it, so URLs/IDs never show.
- bottom: last content row above the share border / taskbar.
- keep the face thumbnail OUT of the crop (if it overlaps the window, end the crop left of it).
Verify: `$F grab $V <t> edit/verify/crop.png --crop x,y,w,h` and look. One entry per app:
`"share": {"notion": [...], "brave": [...]}` (or just `"default"`). The renderer trims each to the card aspect.
Several apps? Add `classify.screen`: a small probe region whose colour differs per app (e.g. a title-bar patch:
light for Notion, dark for a browser), values measured with `$F probe` at a time you know each app is up.

## 4. Face crop (share mode) and camera crop (talk mode)
- `crops.face`: a square inside the presenter thumbnail, centred on the face, above the name label.
  Find the thumbnail with grab + colscan/rowscan; check with `grab --crop`.
- `crops.talk`: in speaker view, a crop of the speaker video centred on the face with the talk-card aspect
  (1060x850 → 1.247), clear of overlay tiles (notetaker bots, self-view). Check with `grab --crop`.

## 5. Who is on screen (`classify.who`)
Pick times where you KNOW who is on screen (from the transcript + sheet). `$F probe $V <face crop> <t1,t2,...>`
for each person in share mode, and `$F probe $V <talk crop> <...>` in talk mode. Rooms differ a lot in colour
(a warm room vs a cool office); record the mean RGB per speaker id:
`"who": {"share": {"probe": [...], "values": {"speaker_0": [r,g,b], "speaker_1": [...]}}, "talk": {...}}`.
If two people look alike in colour, use a region that differs (background, shirt) instead.
Also set `"names"` (speaker id → display name, exact spelling from intake) and `"bubble_speakers"`: the
non-presenter ids whose lines become speech bubbles during the screen share (in camera mode everyone gets captions).

## 6. Frames to skip, freeze or hide
- Black / loading frames at share start, window-switch animations: find them (`$F probe` the crop: very dark or
  mid-transition) and add `"screen_offsets": [{"src": <segment start>, "offset": <s>, "face": true|false}]`: the
  screen picture is taken `offset` seconds later (face + audio stay in sync unless face=true).
- Share ending mid-sentence: `"share_end": <second>` freezes the last good frame.
- Names / IDs inside the content: `"blur": [{"src_from", "src_to", "rect"}]` (source px). If the page scrolls,
  split into several entries or move the box; verify every blurred stretch with grabs.

## 7. Check before moving on
After the first `render_base.py --preview`, look at its "CHECK these" list (mode changes inside a segment) and run a
frame sweep (`ffmpeg ... fps=1/20 ... tile`) to confirm: no URL bar, no thumbnail edge in the card, right name tags.
