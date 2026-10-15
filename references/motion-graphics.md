# Motion graphics: make it fun, never idle

Goal: someone who wasn't in the meeting watches to the end because something meaningful is always moving.
Every graphic carries information from the talk (a number, a list, a contrast, a decision, a joke): never decoration.

## The idle rule
No stretch > 3s without motion or a graphic. `idle_audit.py` enforces it. Screen shares count as idle when the
screen is static (a Notion board, a slide). Fill them:

| Situation on screen | Use |
|---|---|
| Static doc/board while items are named | `zoom` into the area + `rowhi` on each item as it's said + `proj` card per item in the column |
| A UI being demoed | `zoom` on the part being explained + `lane` chip naming it ("New: task breakdown") |
| A number is said ("10X", "5%", "213 PDFs") | `burst` (big number), `bar` (shares), count-up in `list` |
| Before vs after / old vs new | `compare` |
| A process / steps / phases / release path | `flow` (with pain-point bubbles) or `track` |
| Priorities / trade-offs | `matrix` (2x2) |
| A great line, a user quote | `quote` |
| A decision / status | `stamp` ("On hold", "Pilot: 5 courses") |
| A question from the other person | bubble (automatic in share mode) or `big` panel ("Sam asks") in talk mode |
| A story or joke | `kinetic` lines that land word by word (strike-through for the punchline) |
| Camera-only stretches | something in the `panel` at all times: `list`, `big`, `quote`, `track`, `score` |
| Cold open / closer | `kinetic` (pos "free" over the card or "panel"), `score` for a bet/vote |

Variety: don't reuse the same component twice in a row; alternate card / panel / column positions.

## Timing (the part that makes it feel produced)
- Anchor every graphic to the word that carries it (`C.at(src, word)`); rows/dots/lines reveal on THEIR words.
- Never ahead of speech: entrances can start ~0.1-0.3s before the word, payloads (numbers, verbs) land on it.
- Hold a card until the next one in the same slot, or until the idea is finished; ≥ 1.5s readable.
- One new thing at a time per area (cues_lib clamps overlaps per slot automatically).
- Cards cover cuts: a chapter card slides in 0.34s before its gap and out after it.

## Positions
`card` = centred on the screen/speaker card with a dark scrim (use when the screen content is not the point right now)
· `col` = the strip right of the screen card, under the face (share mode, narrow) · `panel` = right of the speaker card
(talk mode) · `free` = big kinetic text over the card · `lane` = chip at the card's top-left (names what's on screen).

## Component schema (data for C.add)
All: `type, t0, t1` (+ `pos`). Optional `ey` eyebrow (off by default: taste).
- `list`: `title, rows[{t,icon,text}]` · `proj`: `icon,title,rows[{t,text}]` (first row shows with the card)
- `rowhi`: `ys[]` (screen px, zoom fully in), `h` · `matrix`: `title, x_label, y_label, dots[{t,label,x,y,tone}], hot_t`
- `quote`: `t, text, who` · `flow`: `title, steps[{t,text}], bubbles[{t,text}]` · `compare`: `title, old{t,label,rows}, new{...}`
- `bar`: `title, items[{t,label,pct}]` · `track`: `title, steps[{t,text}]` · `big`: `a{t,text}, b{t,text}`
- `score`: `title, players[{name,val,t}]` · `stamp`: `t, text, tone` · `burst`: `t, text` · `lane`: `icon, text`
- `kinetic`: `lines[{t,text,style:big|mid|pill,strike_t?,icon?}]`
Icons: layers receipt zap tag users x check trend pin swap sparkles flag scissors clock play msg.
Zoom: `C.zoom(name, pre_t0, pre_t1, z, fx, fy)`: fx,fy = point on the screen card (0-1) that stays fixed; z 1.3-1.9.
Row highlight y with a zoom in: `y = card_y + card_h * (fy + (row_fy - fy) * z)`.

## Taste defaults (override only if the user asks)
- No decorative micro details: no eyebrow labels, HUD text, legends, "LIVE" badges. The headline is the focal point.
- Motion must mean something: entrances reveal information; no idle wobble, no ambient particles.
- No em dashes in on-screen text. Short lines; captions ≤ 34 characters per chunk.
- Bubbles paraphrase long spoken questions (the audio keeps the exact words).
- Brand: one primary, one accent, one pop colour; Nunito-style rounded type unless the brand says otherwise.
