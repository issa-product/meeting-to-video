"""Phrase-level reading view of the transcript: one line per phrase, [start-end] S<n> text.
Phrases break on silence >= 0.5s or a speaker change. Cut decisions are made from this file.
Usage: python pack.py <edit_dir>   -> <edit_dir>/takes_packed.md
"""
import json, sys
from pathlib import Path

ED = Path(sys.argv[1])
out = ["# Packed transcript", "", "Phrases break on silence >= 0.5s or speaker change. Times are source seconds.", ""]
for tp in sorted((ED / "transcripts").glob("*.json")):
    words = [w for w in json.loads(tp.read_text())["words"] if w["type"] in ("word", "audio_event")]
    out.append(f"## {tp.stem}")
    cur = []
    def flush():
        if cur:
            spk = (cur[0].get("speaker_id") or "?").replace("speaker_", "S")
            txt = " ".join(w["text"] if w["type"] == "word" else f"({w['text']})" for w in cur)
            out.append(f"  [{cur[0]['start']:07.2f}-{cur[-1]['end']:07.2f}] {spk} {txt}")
    for w in words:
        if cur and (w["start"] - cur[-1]["end"] >= 0.5 or w.get("speaker_id") != cur[-1].get("speaker_id")):
            flush(); cur = []
        cur.append(w)
    flush()
(ED / "takes_packed.md").write_text("\n".join(out) + "\n")
print(f"wrote {ED / 'takes_packed.md'} ({len(out)} lines)")
