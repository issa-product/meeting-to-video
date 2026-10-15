"""Layout audit: checks QUALITY, not just mechanics. Samples the real overlay layout every 0.5s (layout_audit.mjs) and
fails on:
  OVERLAP       two graphics on top of each other (captions, full cards and the screen highlight excepted)
  OVERFLOW      anything off the 1920x1080 frame, or content spilling out of its own card
  EMPTY         a visible card/box with no visible text in it
  TEXT-ON-TEXT  a graphic (not a stage, which replaces the slide on purpose) sitting on visible slide text
  SMALL         visible text under 20px
  IDLE          > 3s with no visible, non-empty graphic and a static screen (screen motion counts in share mode)
Usage: python layout_audit.py <edit_dir> [--step 0.5] [--max-idle 3]   -> exit 1 on any failure, report in verify/
"""
import argparse, json, subprocess, sys
from pathlib import Path
import numpy as np

SKILL = Path(__file__).resolve().parent
ap = argparse.ArgumentParser(); ap.add_argument("edit_dir"); ap.add_argument("--step", type=float, default=0.5); ap.add_argument("--max-idle", type=float, default=3.0)
a = ap.parse_args(); ED = Path(a.edit_dir).resolve(); (ED / "verify").mkdir(exist_ok=True)
raw = ED / "verify/audit_raw.json"
subprocess.run(["node", str(SKILL / "layout_audit.mjs"), str(ED / "mg"), str(raw), str(a.step)], check=True)
A = json.loads(raw.read_text())
D = json.loads((ED / "mg/data.js").read_text()[len("window.DATA = "):-2])
P = json.loads((ED / "project.json").read_text())
cards = {m: P["layout"][m]["card"] for m in ("share", "talk") if m in P["layout"]}
modeAt = lambda t: next((m["mode"] for m in D["modes"] if m["t0"] - 0.01 <= t < m["t1"]), "share")

# base frames at the same moments, streamed one at a time at 960x540 (small UI text is invisible at lower res)
base = ED / "base_preview.mp4"
W, H = 960, 540
proc = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(base), "-vf", f"fps={1 / a.step:g},scale={W}:{H}", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                        stdout=subprocess.PIPE)
sx, sy = W / 1920, H / 1080


def next_frame():
    b = proc.stdout.read(W * H)
    return np.frombuffer(b, np.uint8).reshape(H, W).astype(np.int16) if len(b) == W * H else None


def text_density(img, box):
    """Share of sharp horizontal transitions under a box. Calibrated at 960px: slide text / dense UI 0.02-0.05,
    busy photos ~0.025, flat backgrounds and the brand plate 0.0. > 0.015 = the graphic covers busy slide content."""
    x, y, w, h = [int(v) for v in (box[0] * sx, box[1] * sy, box[2] * sx, box[3] * sy)]
    reg = img[max(0, y):y + h, max(0, x):x + w]
    if reg.size < 20: return 0.0
    return float((np.abs(np.diff(reg, axis=1)) > 35).mean())


def inter(r1, r2):
    x0, y0 = max(r1["x"], r2["x"]), max(r1["y"], r2["y"]); x1, y1 = min(r1["x"] + r1["w"], r2["x"] + r2["w"]), min(r1["y"] + r1["h"], r2["y"] + r2["h"])
    return max(0, x1 - x0) * max(0, y1 - y0)


SKIP_OVERLAP = {"caption", "full", "highlight"}
BOXES = {"stage", "col", "panel", "label", "chip"}
issues = {k: [] for k in ("OVERLAP", "OVERFLOW", "EMPTY", "TEXT-ON-TEXT", "SMALL", "IDLE")}
covered, mot, prev = [], [], None
for k, s in enumerate(A["samples"]):
    img = next_frame()
    mot.append(bool(img is not None and prev is not None and np.abs(img - prev).mean() > 1.5)); prev = img if img is not None else prev
    t = s["t"]; els = [e for e in s["els"] if e["op"] > 0.6]
    full = any(e["kind"] == "full" for e in els)
    meaningful = [e for e in els if e["kind"] in BOXES | {"highlight"} and (e["nText"] > 0 or e["kind"] == "highlight")]
    covered.append(full or bool(meaningful))
    if full: continue
    for i, e in enumerate(els):
        if e["kind"] in BOXES and e["nText"] == 0: issues["EMPTY"].append((t, e["kind"], "visible box with no text"))
        if e["x"] < -2 or e["y"] < -2 or e["x"] + e["w"] > 1922 or e["y"] + e["h"] > 1082: issues["OVERFLOW"].append((t, e["kind"], f"off frame at {e['x']:.0f},{e['y']:.0f} {e['w']:.0f}x{e['h']:.0f}"))
        if e["overflow"]: issues["OVERFLOW"].append((t, e["kind"], f"content spills out of its box ({e['text'][:30]})"))
        if e["nText"] and e["minFont"] < 20: issues["SMALL"].append((t, e["kind"], f"{e['minFont']:.0f}px text ({e['text'][:30]})"))
        for f2 in els[i + 1:]:
            if e["kind"] in SKIP_OVERLAP or f2["kind"] in SKIP_OVERLAP: continue
            ov = inter(e, f2)
            if ov > 0.03 * min(e["w"] * e["h"], f2["w"] * f2["h"]): issues["OVERLAP"].append((t, f"{e['kind']}+{f2['kind']}", f"{e['text'][:24]} / {f2['text'][:24]}"))
        # graphic on visible slide text: anything but a stage (which replaces the slide) inside the screen card
        md = modeAt(t); c = cards.get(md)
        if c and e["kind"] in ("label", "col", "panel") and img is not None:
            cr = dict(x=c[0], y=c[1], w=c[2], h=c[3])
            if inter(e, cr) > 0.2 * e["w"] * e["h"] and not any(x["kind"] == "stage" for x in els):
                if text_density(img, (e["x"], e["y"], e["w"], e["h"])) > 0.015:
                    issues["TEXT-ON-TEXT"].append((t, e["kind"], f"sits on busy slide content ({e['text'][:30]})"))
# idle: no meaningful graphic and a static screen (share mode only counts real screen motion)
run = None
for k, s in enumerate(A["samples"]):
    ok = covered[k] or (k < len(mot) and mot[k] and modeAt(s["t"]) == "share")
    if not ok and run is None: run = s["t"]
    if ok and run is not None:
        if s["t"] - run > a.max_idle: issues["IDLE"].append((run, "screen", f"{s['t'] - run:.1f}s with nothing meaningful moving (until {int(s['t'] // 60)}:{s['t'] % 60:04.1f})"))
        run = None


def collapse(lst):
    """Merge repeats of the same problem on consecutive samples into one time range."""
    out = []
    for t, who, msg in sorted(lst, key=lambda x: (x[1], x[2], x[0])):
        if out and out[-1][1] == who and out[-1][2] == msg and t - out[-1][3] <= a.step * 1.5: out[-1][3] = t
        else: out.append([t, who, msg, t])
    return sorted(out)


fmt = lambda t: f"{int(t // 60)}:{t % 60:04.1f}"
lines, bad = [], 0
for k, lst in issues.items():
    c = collapse(lst); bad += len(c)
    lines.append(f"{k}: {len(c)}")
    lines += [f"   {fmt(t0)}-{fmt(t1)}  {who}: {msg}" for t0, who, msg, t1 in c[:25]]
if A["errors"]: lines.append("PAGE ERRORS: " + " | ".join(A["errors"][:5])); bad += 1
rep = "\n".join(lines); (ED / "verify/layout_audit.txt").write_text(rep); print(rep)
print("PASS" if not bad else f"FAIL ({bad} problems; output times; full report verify/layout_audit.txt)")
sys.exit(1 if bad else 0)
