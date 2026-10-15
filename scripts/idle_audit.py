"""No idle screen: list every stretch where nothing is animating AND the screen isn't moving.
Covered = any graphic / bubble / card on screen, or (share mode only) real screen motion. Talk mode needs a
graphic at all times except short breaths. Usage: python idle_audit.py <edit_dir> [--max 3]
Exit code 1 if any stretch is longer than --max seconds (fix with graphics, zooms, callouts; then re-run).
"""
import argparse, json, subprocess, sys
from pathlib import Path
import numpy as np

ap = argparse.ArgumentParser(); ap.add_argument("edit_dir"); ap.add_argument("--max", type=float, default=3.0)
a = ap.parse_args(); ED = Path(a.edit_dir)
D = json.loads((ED / "mg/data.js").read_text()[len("window.DATA = "):-2])
T = D["total"]; N = int(T * 2); cov = np.zeros(N, bool)
mark = lambda t0, t1: cov.__setitem__(slice(max(0, int(t0 * 2)), min(N, int(t1 * 2) + 1)), True)
for g in D["graphics"]: mark(g["t0"], g["t1"])
for b in D["bubbles"]: mark(b["t0"], b["t1"])
for c in D["chapters"]: mark(c["start"] - 0.4, c["start"] + c["dur"] + 0.4)
mark(D["title"]["start"] - 0.4, D["title"]["start"] + D["title"]["dur"]); mark(D["end"]["start"] - 0.4, T)
base = ED / "base_preview.mp4"
out = subprocess.run(["ffmpeg", "-v", "error", "-i", str(base), "-vf", "fps=2,scale=320:180", "-f", "rawvideo", "-pix_fmt", "gray", "-"],
                     capture_output=True).stdout
fr = np.frombuffer(out, np.uint8).reshape(-1, 180, 320).astype(int)
mot = np.zeros(N, bool)
for i in range(1, min(len(fr), N)): mot[i] = np.abs(fr[i] - fr[i - 1]).mean() > 1.5
mode = lambda t: next((m["mode"] for m in D["modes"] if m["t0"] <= t < m["t1"]), "share")
idle, s = [], None
for i in range(N + 1):
    ok = i == N or cov[i] or (mot[i] and mode(i / 2) == "share")
    if not ok and s is None: s = i
    if ok and s is not None:
        if (i - s) / 2 > a.max: idle.append((s / 2, i / 2, mode(s / 2)))
        s = None
fmt = lambda t: f"{int(t // 60)}:{t % 60:04.1f}"
print(f"idle stretches > {a.max}s: {len(idle)}")
for t0, t1, m in idle: print(f"  {fmt(t0)}-{fmt(t1)}  {t1 - t0:.1f}s  {m}   (output time; see what is said there and add a graphic)")
sys.exit(1 if idle else 0)
