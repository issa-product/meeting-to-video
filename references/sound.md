# Sound design (the fun multiplier; the user approves the cue sheet before anything is mixed)

1. **Cue plan** `edit/audio/sfx_plan.json`: every cue tied to a VISIBLE event at its output time (card lands,
   stamp hits, burst pops, zoom starts, chapter card slides). Read times from `mg/data.js` (graphics t / chapter
   start). Density: ~8 well-chosen cues per minute at most; most transitions get nothing. Long-form gains: payoffs
   -5/-6 dB, transitions -6/-8, texture -9/-11 (relative to clips normalised by ElevenLabs).
   Prompts: "short soft whoosh, airy", "bright pop, cartoon, short", "rubber stamp thud", "gentle riser 0.8s",
   "single wood click". 0.4-1.2s each.
2. **Show** `sound.py sheet <edit>` and WAIT for approval. Then `sound.py gen <edit>` (cached; attack measured,
   so each sound starts early and its transient lands on the frame).
3. **Music**: two contrasting beds (e.g. "upbeat light corporate, plucky, 110 bpm, no vocals" vs "lo-fi warm,
   soft drums, no vocals"), via `sound.py music <edit> audio/music_a.mp3 "<prompt>"`, or the user's own
   royalty-free track. The user listens and picks. You cannot hear: never claim it sounds good, report numbers.
4. **Mix** `sound.py mix <edit> --music <file> --duck 13`: music ducked ~12-15 dB under speech (sidechain), faded
   out before the end card, SFX placed by attack, limiter, two-pass loudnorm to -14 LUFS / -1 dBTP →
   `audio/master.wav`. Report integrated loudness, true peak, LRA.
5. Compose the final with `audio/master.wav` as the 4th argument of compose.sh.
