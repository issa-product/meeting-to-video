---
name: meeting-to-video
description: Turn a recorded meeting, demo, slide presentation or screen-share walkthrough (Zoom, Google Meet, Teams, any .mp4) into a short, engaging, branded company video with word-synced motion graphics, stage scenes for text slides, captions, chapter cards and sound design. Use when the user wants to edit, cut down, recut, make more engaging, add motion graphics to, or turn into a highlight/explainer video a meeting recording, product walkthrough, demo, deck presentation, all-hands segment or screen recording. Guides setup, asks for the video and goals, inventories the screens, shows a plan WITH style frames for approval, then builds and quality-checks the video.
---

# Meeting → video

Turn a long recording into a short video people actually watch: nothing important lost, the screen never idle,
the look calm and readable. Every time: **ask → measure → inventory → plan + style frames (user approves) → cut →
build → audit → user review → sound (user approves) → final → learn.**

`SKILL=~/.claude/skills/meeting-to-video`, `PY=~/.config/meeting-to-video/venv/bin/python`, scripts in `$SKILL/scripts`.
Outputs go in `<video folder>/edit/`. Log every session in `edit/project.md`; read it first when resuming.
**Read `references/taste.md` at the start of every project. It wins over any default.**

## Phase 0: setup (first run on a machine)
`bash $SKILL/setup/doctor.sh`. Install whatever is MISSING yourself (setup/SETUP.md), asking before each install;
the user only pastes an ElevenLabs key. Say up front: rendering ≈ 2 min per minute of final video on 8 GB.

## Phase 1: intake (ask; AskUserQuestion when available, a few at a time)
1. **Where is the recording?** (path; check with ffprobe)
2. **Target length**: under 3 / about 5 / about 7 min / "keep everything important"
3. **Audience and tone** · 4. **Who speaks** (exact spellings, who presents) + **glossary** of product terms
5. **What should viewers remember?** (2-3 focus ideas) · 6. **Brand** (colours, logo, or propose) ·
7. **Deliverables** (16:9 final, 9:16 teaser, Slack post + chapters) · 8. **Privacy**: audio goes to ElevenLabs, OK?
9. **Cut style**: gentle (default: keeps "um"s and short pauses, natural speech) or tight (`--aggressive`)?

## Phase 2: ingest + measure
1. `$PY $SKILL/scripts/transcribe.py <video> <edit> --speakers N`, `$PY $SKILL/scripts/pack.py <edit>`, read takes_packed.md.
2. `frames.py sheet` and LOOK. 3. Measure THIS recording into `edit/project.json` (from templates/project.example.json)
following `references/measuring.md`: share/talk signature, full screen crops, **paint** boxes over overlays that
sit on the content (Zoom's face tile: paint it, never crop the slide), face + camera crops, who-signatures,
offsets for black frames, blur boxes. Never guess a number you haven't measured.

## Phase 3: screen inventory
`$PY $SKILL/scripts/inventory.py <edit>` → look at `verify/inventory.jpg`, correct every `kind` in inventory.json:
**text** (title / bullets / simple table → replaced by a stage scene) or **visual** (chart / screenshot / UI / board
→ shown in full, graphics only beside it). This choice goes into the plan per section.

## Phase 4: PLAN + LOOK → **user approves before anything is built**
Read `references/story.md`. Write `edit/PLAN.md` (`references/plan-template.md`): sections (keep/trim/cut + why),
the screen kind and treatment per section, 3 hook candidates + pick, closer, chapters, the graphic per section,
length vs target. Then show the LOOK with it:
- `layout_options.py <edit> <share_s> --talk <cam_s>` → 3 layouts (card = the screen's own shape, even sizes)
- write `edit/style.json` (~4 representative moments: a stage scene, a visual screen with a side card, a camera
  stretch with a panel, a chapter card) → `style_frames.py <edit>` → `verify/style_sheet.jpg`
Send plan + layouts + style frames together. Iterate until the user says go. Never show the style first in a render.

## Phase 5: cut
`edit/cuts.json` from the approved sections → `build_edl.py <edit>` (gentle) or `--aggressive` if asked.
Check length vs target; trim repeats and small talk first, never information the user said matters.

## Phase 6: base video
Chosen layout into project.json → `layout_assets.py <edit>` → `render_base.py <edit> --preview` → `timeline.py <edit>`.
Read the "CHECK these" segments; sweep frames for leaks (URL bars, names, the face tile showing through).

## Phase 7: motion graphics + audit
Read `references/motion-graphics.md`. Copy `templates/overlay/` → `<edit>/mg/` and `templates/cues.example.py` →
`<edit>/cues.py`; write cues for THIS video (stage scenes for text screens, side cards for visual screens and
camera stretches, every item on its word). `$PY <edit>/cues.py` must print no MISS / CONFLICT / PROBLEMS.
Zooms only if they add something: `zoom_check.py <edit>`, look, then `verified=True`; re-render those segments.
`build_audio.py <edit>`. Then the gates, in order, fixing and repeating until each passes:
1. `layout_audit.py <edit>`: no OVERLAP / OVERFLOW / EMPTY / TEXT-ON-TEXT (busy content under a graphic) /
   SMALL text / IDLE > 3s. This is the quality gate; nothing ships with a failure.
2. `render_overlay.sh <edit> --test 30` (a REAL short render) → `render_overlay.sh <edit>` → `alpha_check.py <edit>`.
3. `PRESET=veryfast CRF=22 compose.sh <edit> <edit>/base_preview.mp4 <edit>/preview.mp4`, sweep frames, send it.
Ask for notes by timestamp and whether the focus ideas land. Re-run only what changed; never re-transcribe.

## Phase 8: sound → **user approves the cue sheet and picks the music**
`references/sound.md`: `audio/sfx_plan.json` (cues tied to visible events, sparse) → `sound.py sheet` → OK →
`sound.py gen` → two music options → user picks → `sound.py mix <edit> --music <file>` → report loudness.

## Phase 9: final, deliver, learn
`render_base.py <edit>` (final 1080p) → `compose.sh <edit> <edit>/base_final.mp4 <edit>/final.mp4 <edit>/audio/master.wav`
→ `references/qa.md` → deliver final.mp4, chapter timestamps, Slack post, teaser if asked.
**Learning loop (always):** fold what this project taught back into the skill, not just the project log:
taste feedback → `references/taste.md` (Taste log, dated); new traps → `references/gotchas.md`; script/template
fixes → the scripts. Show the user the diff, then `git -C $SKILL add -A && git -C $SKILL commit -m "learn: <what>"`
and `git -C $SKILL push` (ask before pushing).

## Non-negotiables
- Never build before the plan + style frames are approved. Never mix before the cue sheet is approved.
- Never guess a timestamp, crop or colour: measure it. Every anchor resolves.
- Never crop slide content to hide an overlay (paint it); never trim content to fit a card (the card takes the
  content's shape; the renderer letterboxes); all sizes even; zooms only after zoom_check.
- Text lands ON the spoken word, never before. One item per zone. No card visible without text.
- Taste (`references/taste.md`): light cards, SF Pro 500-700, calm motion, no veils, no bursts over busy slides,
  text slides become stage scenes.
- Privacy: no URL bars, IDs or uncleared names on screen; only audio leaves the machine (ElevenLabs).
- Known traps: `references/gotchas.md` (read before Phase 6).
