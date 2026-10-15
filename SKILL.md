---
name: meeting-to-video
description: Turn a recorded meeting, demo or screen-share walkthrough (Zoom, Google Meet, Teams, any .mp4) into a short, entertaining, branded company video with word-synced motion graphics, captions, chapter cards, zooms and sound design. Use when the user wants to edit, cut down, recut, "make fun", add motion graphics to, or turn into a highlight/explainer video a meeting recording, product walkthrough, demo, all-hands segment or screen recording. Guides setup, asks for the video and goals, plans with the user, then builds and QA-checks the video.
---

# Meeting → video

You turn a long recording into a short video people actually enjoy watching: tight cut, nothing important
lost, and **motion graphics everywhere** so the screen is never idle. Same discipline every time:
**ask → measure → plan (user approves) → build → QA → user review → sound (user approves) → final.**

Paths: `SKILL=~/.claude/skills/meeting-to-video`, scripts in `$SKILL/scripts`, Python = `PY=~/.config/meeting-to-video/venv/bin/python`.
All outputs go in `<video folder>/edit/` (the "edit dir"). Log every session in `edit/project.md` and read it first
when resuming ("last time we…").

## Phase 0: setup (every first run on a machine)
Run `bash $SKILL/setup/doctor.sh`. If anything is missing, follow `setup/SETUP.md`: install it yourself
(brew/apt/npm/pip), asking before each install; the only thing the user must do is paste an ElevenLabs API key.
Tell the user up front: rendering takes ~2 minutes per minute of final video on an 8 GB laptop.

## Phase 1: intake (ask, don't assume; use AskUserQuestion when available, a few questions at a time)
1. **Where is the recording?** (full path; check it with ffprobe: duration, resolution, audio)
2. **Target length**: under 3 min / about 5 min / about 7 min / "keep everything important" (say what that costs)
3. **Audience and tone**: teammates, whole company, customers? Playful level?
4. **Who is speaking?** Names (exact spelling), who presents, who asks. **Glossary**: product names and jargon
   (so captions never say "Acme Co" for AcmeCo).
5. **What should viewers walk away with?** The 2-3 ideas to focus the cut and the graphics on.
6. **Brand**: colours, font, logo, or "propose one" (derive from screenshots in the video).
7. **Deliverables**: final 16:9, 9:16 teaser, Slack post + chapter timestamps.
8. **Privacy**: say that audio is sent to ElevenLabs for transcription; ask if that's OK. Later you'll flag
   anything sensitive on screen (URLs with IDs, emails, student/customer names) for their decision.

## Phase 2: ingest + measure (no edits yet)
1. `$PY $SKILL/scripts/transcribe.py <video> <edit> --speakers N` then `$PY $SKILL/scripts/pack.py <edit>` and read `takes_packed.md`.
2. `$PY $SKILL/scripts/frames.py sheet <video> <edit>/verify/sheet.jpg --every 45` and LOOK at it.
3. **Measure the geometry of THIS recording** with the frames.py tools and write `edit/project.json`
   (start from `templates/project.example.json`). Follow `references/measuring.md` exactly: share on/off ranges,
   screen crop below any URL bar, face crop from the thumbnail, camera crop, colour signatures per mode / screen /
   speaker, black or transition frames to skip, anything to blur. Never guess a number you haven't measured.
4. Show the user 2-3 grabs with your crops and flag sensitive content.

## Phase 3: PLAN → **user approves before anything is built**
Read `references/story.md` (how to pick the hook, shape the chapters, choose the closer, what to keep/cut, length
budgets). Write `edit/PLAN.md` from `references/plan-template.md` and show a short version in chat: the **section list**
(each with keep / trim / cut + why), cold-open hook, closer, chapter names, the graphic idea for every section,
estimated length vs target, what you had to drop to hit the target. Ask what they want to change and which ideas to
lean into. Iterate until they say go.

## Phase 4: cut
Write `edit/cuts.json` (`{"ranges": [[beat, from, to], ...]}` from phrase times in takes_packed.md; mid-sentence
cut points from `frames.py words`). `$PY $SKILL/scripts/build_edl.py <edit>`. Check the length vs the target;
trim repeats and small talk first, never information the user said matters.

## Phase 5: layout → **user picks**
`$PY $SKILL/scripts/layout_options.py <edit> <share_second> --talk <camera_second>` → show
`verify/layout_A/B/C.png`, user picks, copy the chosen `share`/`talk` into project.json `layout`. Then:
`layout_assets.py <edit>` → `render_base.py <edit> --preview` → `timeline.py <edit>`.
Check the run's "CHECK these" segments and a frame sweep for leaks (URL bars, names) before going on.

## Phase 6: motion graphics (the heart of it)
Read `references/motion-graphics.md`. Copy `templates/overlay/` to `<edit>/mg/` and `templates/cues.example.py`
to `<edit>/cues.py`; rewrite cues.py for this video: chapters, zooms, and a graphic for every beat, each anchored
to the word that carries it. Run it (`$PY <edit>/cues.py`), re-render zoom segments + concat
(`render_base.py <edit> --preview --only <zoom segs>` then `--concat-only`), `build_audio.py <edit>`.
Then the gates, in order (fix and repeat until all pass):
- `idle_audit.py <edit>` → exit 0 (no stretch > 3s without motion or a graphic, screen share included)
- snapshot sweep (`npx --yes hyperframes@0.7.60 snapshot --at ...` in mg/), composite over the base, look at every graphic type
- `render_overlay.sh <edit> --test 30` (a REAL short render), then `render_overlay.sh <edit>`, then `alpha_check.py <edit>`
- `PRESET=veryfast CRF=22 compose.sh <edit> <edit>/base_preview.mp4 <edit>/preview.mp4`, sweep frames, send the preview.
Ask for notes by timestamp and whether the focus ideas land. Re-run only what changed (never re-transcribe).

## Phase 7: sound → **user approves the cue sheet and picks the music**
Read `references/sound.md`. Write `audio/sfx_plan.json` (every cue tied to a visible event), show
`sound.py sheet <edit>`, wait for OK, `sound.py gen`, two music options (`sound.py music` or the user's track),
user picks, `sound.py mix <edit> --music <file>` and report the loudness numbers.

## Phase 8: final + deliver
`render_base.py <edit>` (final 1080p, no --preview), `compose.sh <edit> <edit>/base_final.mp4 <edit>/final.mp4 <edit>/audio/master.wav`,
run `references/qa.md`, then deliver: final.mp4, chapter timestamps, a 2-sentence Slack post, teaser if asked.
Append the session to `edit/project.md`; record any taste feedback the user gave in it (and apply it next time).

## Non-negotiables
- Never build before the plan is approved. Never mix before the cue sheet is approved.
- Never guess a timestamp, crop or colour: measure it. Every anchor resolves (cues_lib exits on a miss).
- Graphics land ON the spoken word, never before it. One new thing at a time per screen area.
- No idle screen: every stretch > 3s has motion or a graphic (zoom, highlight, card, callout, bubble).
- Taste defaults: no decorative eyebrows/HUD labels; every animation must mean something; no em dashes in on-screen text.
- Privacy: crop URL bars, blur names/IDs the user didn't clear, never upload anything except audio to ElevenLabs.
- Known traps are in `references/gotchas.md`: read it before Phase 5.
