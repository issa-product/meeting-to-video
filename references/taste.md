# Taste (read this at the start of EVERY project; it overrides any default in the template)

These are the house rules. They came from real feedback. When the user gives new taste feedback, add it to the
**Taste log** at the bottom (with the date and what triggered it) and fold it back into the repo (SKILL.md, Phase 9).

## Type
- SF Pro (system font on macOS; bundled Inter elsewhere). Weights 500-700 only. No 800/900 "chunky" type.
- Headlines 56-112px, body 24-44px, nothing visible under 20px (layout_audit fails on SMALL).
- Short lines. No em dashes in on-screen text. Sentence case.

## Surfaces
- Light cards (white / near-white) with a soft shadow. No dark scrims, no veils over the screen.
- The screen recording is shown in full and untouched, or replaced entirely by a stage scene. Never "a box over
  half the slide".
- One accent colour for emphasis (highlights, chips). Brand primary for the frame and chapter cards.

## Motion
- Calm: fades + small rises (8-18px), power2/power3 out, 0.35-0.5s. No overshoot, no bounce, no "pop", no spin.
- Every animation reveals information (a line, a row, a number). Nothing moves just to move: no wobble, no
  particles, no confetti, no idle loops.
- One new thing at a time per zone. Text lands on the word that says it, never before it.

## What goes where
- Text-only slides (title, bullets, simple table) → a **stage** scene that replaces the slide and tells the same
  thing better (big text, built line by line on the words).
- Visual screens (chart, screenshot, UI, board, diagram) → shown in full; graphics only in the side column / panel
  and a small label chip if the corner is calm. Highlights are outlines, not fills.
- Big numbers live on a stage (`stat`), never as a burst over a busy slide.
- No decorative micro details: no eyebrows, HUD labels, legends, "LIVE" badges, tickers.

## Cut
- Gentle by default: keep "um"s and pauses under 0.7s so speech never jumps. Tighter only when the user asks.

## Taste log
- 2026-10-15: v1 felt loud and jumpy. Chunky 900 Nunito, dark scrims, bouncy pops, number bursts over busy slides,
  aggressive um/pause removal. Replaced with the rules above (SF Pro 500-700, light cards, calm easing, stage scenes
  for text slides, gentle cut).
