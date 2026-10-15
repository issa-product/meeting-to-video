# Gotchas (each one cost a re-render; the scripts already handle them, keep it that way)

1. **Render ≠ snapshot.** The HyperFrames renderer steps frames in its own order; a fresh-page snapshot can look
   perfect while the render is blank. Visibility must be a tween with BOTH ends declared
   (`fromTo(autoAlpha 0→1)` / `to(autoAlpha 0)`). Never autoAlpha only in a fromTo's FROM vars; never `tl.set` for
   card visibility. Prove it with `render_overlay.sh --test 30` + `alpha_check.py`.
2. **Static `data-duration` wins.** The renderer reads the root element's attribute, not a JS-set value. cues_lib
   stamps the real length into mg/index.html; if an overlay comes out short, `render_overlay.sh <edit> --tail <len>`.
3. **`fromTo` after t=0 needs `immediateRender:false`**, or its FROM state shows from frame 0.
4. **GSAP owns `transform`.** A CSS `translate(-50%,-50%)` gets overwritten: centre with xPercent/yPercent.
5. **AAC segment concat drifts** (encoder priming, ~2 ms per cut → 0.26 s over 6 min). Audio master comes from
   sample-exact trims (`build_audio.py`); compose re-times both videos by frame index.
6. **Cold opens reuse source audio**: the same source word exists twice in the cut. Anchor with `after=`.
7. **Anything crossing a card gap** reappears after the card: cues_lib clamps; cards are the top layer.
8. **Share starts on black / window-switch swipes**: use `screen_offsets` (screen from a later moment).
9. **Zoom crop x/y must be expressions of time**, not of the scaled frame size (crop doesn't re-evaluate iw/ih).
10. **Words in captions:** remove um/uh, fix mishearings with `C.fixes`, merge split names, glossary from intake.
11. **Long `<video>` inside HyperFrames hangs renders**: the base video is never inside the overlay composition.
12. **ffmpeg builds without drawtext/libass are common**: captions live in the overlay, not in ffmpeg.
13. **Low memory (8 GB)**: one render worker; don't run two renders at once; ~2 min per output minute.
14. **Never re-transcribe** a source that hasn't changed (transcribe.py caches).
15. **Don't crop to dodge an overlay** (v1 cropped Zoom's face tile out and cut slide content): paint over it.
16. **Don't trim to fit the card** (v1 silently cut the edges again): the card takes the content's shape; the
    renderer letterboxes.
17. **Odd pixel sizes crash zooms** (scale with eval=frame needs even sizes): layout_options and render_base force
    even; render_base refuses an odd card.
18. **Zoom targets set by eye cut text**: zooms render only after `zoom_check.py` + a look at the full-zoom still.
19. **Unpositioned top-level elements** render in the corner: every element in the overlay layer is absolute.
20. **Cards visible before their text is spoken** look broken: cues_lib moves a card's start to its first line.
21. **Shared size classes leak** between stage and side cards: stage styles are scoped under `.stage`, side under `.side`.
22. **"A box is on screen" isn't "the screen is alive"**: layout_audit counts only visible boxes with visible text.
