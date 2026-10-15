"""Cut list -> edl.json, snapped to word boundaries.

cuts.json (written by Claude from the APPROVED plan, phrase times from takes_packed.md):
  {"ranges": [["HOOK", 145.20, 154.68], ["CH1 roadmap", 200.52, 209.74], ...]}
Each [beat, from, to] keeps the words whose start is in [from, to). Inside a range: um/uh are dropped and
pauses longer than --gap are cut (keeps the voice natural, kills dead air). Edges padded 60ms/100ms
(never into a neighbouring word). Usage: python build_edl.py <edit_dir> [--gap 0.32]
"""
import argparse, json
from pathlib import Path

FILL = {"um", "uh", "um,", "uh,", "um...", "uh...", "Um,", "Uh,", "Um", "Uh", "Um...", "Uh..."}
PRE, POST = 0.06, 0.10


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("edit_dir"); ap.add_argument("--gap", type=float, default=0.32)
    a = ap.parse_args(); ED = Path(a.edit_dir)
    P = json.loads((ED / "project.json").read_text())
    tr = next((ED / "transcripts").glob("*.json"))
    W = [w for w in json.loads(tr.read_text())["words"] if w["type"] == "word"]
    cuts = json.loads((ED / "cuts.json").read_text())["ranges"]
    ranges, tot = [], 0.0
    for beat, s0, s1 in cuts:
        groups = [[]]
        for w in [w for w in W if s0 - 0.02 <= w["start"] < s1]:
            if w["text"] in FILL: groups.append([]); continue
            if groups[-1] and w["start"] - groups[-1][-1]["end"] > a.gap: groups.append([])
            groups[-1].append(w)
        for g in groups:
            if not g or (len(g) == 1 and g[0]["text"] in ("So", "So,")): continue
            i0, i1 = W.index(g[0]), W.index(g[-1])
            pe = W[i0 - 1]["end"] if i0 else 0; ns = W[i1 + 1]["start"] if i1 + 1 < len(W) else 1e9
            st = max(g[0]["start"] - PRE, (pe + g[0]["start"]) / 2); en = min(g[-1]["end"] + POST, (g[-1]["end"] + ns) / 2)
            if ranges and st - ranges[-1]["end"] <= 0.02 and st > ranges[-1]["start"]:
                ranges[-1]["end"] = round(en, 3)
            else:
                ranges.append(dict(source="main", start=round(st, 3), end=round(en, 3), beat=beat,
                                   quote=" ".join(w["text"] for w in g)[:90]))
            tot += en - st
    edl = dict(version=1, sources={"main": P["video"]}, ranges=ranges, total_duration_s=round(tot, 2))
    (ED / "edl.json").write_text(json.dumps(edl, indent=1))
    target = P.get("target_minutes")
    print(f"{len(ranges)} ranges, {tot:.1f}s = {int(tot // 60)}:{tot % 60:04.1f}" + (f"  (target {target} min)" if target else ""))


if __name__ == "__main__":
    main()
