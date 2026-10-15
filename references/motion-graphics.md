# Motion graphics: never idle, never loud

Read `taste.md` first. Goal: someone who wasn't in the meeting watches to the end because the screen always
tells them something, calmly. Every graphic carries information from the talk; nothing is decoration.

## Start from the screen inventory
`inventory.py` splits the share into screens; each is **text** or **visual** (Claude confirms by looking):

| Screen kind | Treatment |
|---|---|
| text (title, bullets, simple table, agenda) | a `stage` scene replaces it for its whole stretch: same message, built on the words |
| visual (chart, screenshot, UI demo, board, diagram) | shown in full; side column cards, a label chip only if that corner is calm, outline highlights |
| camera only (talk mode) | something in the panel at all times: list, big, quote, track, bar, score |

## Zones (one item per zone at a time; cues_lib resolves handoffs and queues, and reports conflicts)
| Zone | What | Where |
|---|---|---|
| `stage` | `type: "stage"` scenes | exactly over the screen / speaker card |
| `col` | side cards (`pos: "col"`) + the other person's bubbles | right column under the face (share mode only) |
| `panel` | side cards (`pos: "panel"`) | right of the speaker card (talk mode only) |
| `label` | `lane` chip | top-left of the screen card (hidden while a stage is up) |
| `highlight` | `rowhi` outlines | on a visual screen (hidden while a stage is up) |
| `full` | title / chapter / end cards | whole frame, in the inserted gaps |

## Components (data for C.add; every time comes from C.at(src, word))
Stage layouts (`type: "stage"`, `layout`):
- `headline`: `kicker?, lines[{t, text, style?: "sub"}]`. Cold opens, takeaways, a strong line.
- `bullets`: `title, items[{t, text, icon?}]`. The replacement for a bullet slide.
- `stat`: `t, value, label`. A number said out loud ("40%", "4 days → ½ day").
- `compare`: `title?, old{t, label, rows[]}, new{t, label, rows[]}`. Before/after, old/new.
- `steps`: `title?, steps[{t, text}]`. A process, phases, a release path.
- `quote`: `t, text, who`. A line worth keeping.
- `matrix`: `title?, x_label, y_label, dots[{t, label, x, y}]`. Priorities, trade-offs.
Side cards (`pos: "col"` in share mode, `pos: "panel"` in talk mode):
- `list`: `title?, rows[{t, text, icon?}]` · `proj`: `title, rows[...]` · `big`: `a{t, text}, b{t, text}`
- `quote`: `text, who` · `bar`: `title, items[{t, label, pct}]` · `track`: `title, steps[{t, text}]` · `score`: `title, players[{name, val, t}]`
Screen annotations (visual screens only): `lane`: `icon, text` · `rowhi`: `ys[], h` (screen px)
Bubbles: automatic for `bubble_speakers` during the share; paraphrase long lines with `C.short`.
Icons: layers receipt zap users x check trend pin swap sparkles flag clock play tag msg.

## Timing
- Anchor every graphic to the word that carries it; rows / lines / dots reveal on THEIR words.
- A card enters with its first line (cues_lib moves t0 so a card is never empty); hold ≥ 1.5s.
- Chapter cards cover cuts: they slide in 0.34s before their gap and out after it.

## Zooms (off by default)
Only for a small UI detail on a visual screen. `C.zoom(name, pre_t0, pre_t1, z, fx, fy)` → run `zoom_check.py`,
look at `verify/zoom_<name>.png`, and only then set `verified=True` (unverified zooms are not rendered).
Never zoom a text slide (it becomes a stage).
