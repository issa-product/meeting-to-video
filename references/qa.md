# QA (before every preview you send, and fully before final)

Automatic (all must pass):
- [ ] `idle_audit.py <edit>` exits 0 (no > 3s idle, screen share included)
- [ ] `alpha_check.py <edit>`: every title/chapter/end card OK and overlay length == composition length
- [ ] `build_audio.py` total == motion_plan total (frame-exact); `ffprobe` nb_frames of base == total × 30
- [ ] cues.py printed no MISS and no "PARAPHRASE these" lines left
- [ ] loudness (after mix): integrated ≈ -14 LUFS, true peak ≤ -1 dBTP; music under speech, no SFX louder than voice

Visual (look, don't assume):
- [ ] frame sweep every ~20s of the composite (`ffmpeg -vf fps=1/20,scale=480:-1,tile=4x4`)
- [ ] one snapshot per graphic type at its fully-revealed moment, composited over the base
- [ ] every card gap: card fully covers the frame, no ghost of the previous graphic
- [ ] no URL bars, IDs, emails or names the user didn't clear; blur boxes still on target when the page scrolls
- [ ] name tag matches who is on screen; face circle never shows the notetaker / empty tile
- [ ] captions: right speaker colour, glossary spellings, no caption under a full card

Sync:
- [ ] spot-check 5 graphics: the payload lands on its word (±2 frames), never before
- [ ] first 2s and last 2s look intentional; the end card holds ≥ 3s

Critic pass (for anything company-wide): spawn a sub-agent with the preview frames + PLAN.md to watch it cold
"as a coworker": ranked problems with timestamps, top 5 fixes. Fix, max 3 passes, then report what's left.
