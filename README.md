# meeting-to-video (Claude Code skill)

Turns a meeting / demo / screen-share recording into a short, fun, branded video: tight cut, word-synced
captions, chapter cards, zooms, callouts, story cards, speech bubbles, sound effects and music. Claude asks
what you want, measures your recording, shows you a plan, and only builds after you approve.

## Install (one minute)
1. Clone it into your Claude Code skills folder:
   ```
   git clone https://github.com/issa-product/meeting-to-video ~/.claude/skills/meeting-to-video
   ```
   (or with GitHub CLI: `gh repo clone issa-product/meeting-to-video ~/.claude/skills/meeting-to-video`)
2. Open Claude Code anywhere and say: **"Turn my meeting recording into a video"**.
   Claude runs the setup check and installs what's missing (ffmpeg, Python packages, Node), asking first.
3. Have an ElevenLabs API key ready (elevenlabs.io → Settings → API keys). It's used for transcription,
   sound effects and music. Your audio is sent to ElevenLabs; nothing else leaves your machine.

Update later: `git -C ~/.claude/skills/meeting-to-video pull`

Works on macOS and Linux (Windows via WSL2). Zoom recordings are the best-tested; Meet/Teams work because
Claude measures each recording instead of assuming a layout.

## What Claude will ask you
Where the video is · how long the result should be (3 / 5 / 7 min) · who's speaking (and spellings) · who
it's for · what viewers should remember · brand colours (or it proposes) · what to deliver.

## What you approve along the way
The plan (sections kept/cut, hook, chapters, graphic ideas) → the layout (3 options) → previews (send notes by
timestamp) → the sound-effects cue sheet and music → the final.

## Time
Rendering is roughly 2 minutes per minute of finished video on an 8 GB laptop.

## Layout of this folder
`SKILL.md` (Claude's instructions) · `setup/` (doctor + install guide) · `scripts/` (pipeline) ·
`templates/` (project config, cues example, overlay component library) · `references/` (measuring, motion
graphics, sound, QA, gotchas, plan template).
