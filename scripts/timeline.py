"""Output-timeline map (before inserted cards): every kept word with its output time, every segment with its
layout mode. Segment lengths are the RENDERED frame counts (30fps), so graphics sync to real frames.
Run after the first render_base.py pass.   Usage: python timeline.py <edit_dir> [--sub preview]
"""
import argparse, json, subprocess
from pathlib import Path


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("edit_dir"); ap.add_argument("--sub", default="preview")
    a = ap.parse_args(); ED = Path(a.edit_dir)
    P = json.loads((ED / "project.json").read_text())
    R = json.loads((ED / "edl.json").read_text())["ranges"]
    W = [w for w in json.loads(next((ED / "transcripts").glob("*.json")).read_text())["words"] if w["type"] == "word"]
    log = {x["i"]: x for x in json.loads((ED / f"clips/log_{a.sub}.json").read_text())}
    durs = []
    for i in range(len(R)):
        n = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=nb_frames", "-of", "csv=p=0",
                            str(ED / f"clips/{a.sub}/seg_{i:03d}.mp4")], capture_output=True, text=True).stdout.strip()
        durs.append(int(n) / 30)
    (ED / f"clips/durs_{a.sub}.json").write_text(json.dumps(durs))
    segs, words, off = [], [], 0.0
    for i, r in enumerate(R):
        segs.append(dict(i=i, src_start=r["start"], src_end=r["end"], out_start=round(off, 4), dur=durs[i], beat=r["beat"],
                         mode=log[i]["mode"], who=log[i]["who"]))
        for w in W:
            if r["start"] <= w["start"] < r["end"]:
                words.append(dict(text=w["text"], spk=w.get("speaker_id"), src=w["start"], seg=i,
                                  start=round(w["start"] - r["start"] + off, 3), end=round(min(w["end"], r["end"]) - r["start"] + off, 3)))
        off += durs[i]
    (ED / "timeline.json").write_text(json.dumps(dict(segs=segs, words=words, total=off)))
    print(f"{len(segs)} segments, {len(words)} words, {off:.2f}s before cards")


if __name__ == "__main__":
    main()
