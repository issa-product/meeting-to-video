"""Prove the full-frame cards are really in the RENDERED overlay (snapshots can't prove this).
Measures overlay alpha inside every title/chapter/end card window; also flags a too-short overlay.
Usage: python alpha_check.py <edit_dir> [overlay.webm]
"""
import json, subprocess, sys
from pathlib import Path

ED = Path(sys.argv[1]); ov = ED / (sys.argv[2] if len(sys.argv) > 2 else "overlay.webm")
D = json.loads((ED / "mg/data.js").read_text()[len("window.DATA = "):-2])
dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(ov)], capture_output=True, text=True).stdout)
pts = [("title", D["title"]["start"] + 1.0)] + [(f"chapter {c['n']}", c["start"] + 0.8) for c in D["chapters"]] + [("end", D["end"]["start"] + 2.0)]
bad = []
for name, t in pts:
    b = subprocess.run(["ffmpeg", "-v", "error", "-c:v", "libvpx-vp9", "-i", str(ov), "-vf", f"select=eq(n\\,{round(t * 30)}),format=rgba,alphaextract",
                        "-frames:v", "1", "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True).stdout
    a = sum(b) / max(1, len(b)); ok = a > 250
    print(f"{name:12s} t={t:7.2f}  alpha={a:5.1f}  {'OK' if ok else 'MISSING'}")
    if not ok: bad.append(name)
print(f"overlay {dur:.2f}s vs composition {D['total']:.2f}s" + ("  <-- SHORT: render the tail (render_overlay.sh --tail)" if dur < D["total"] - 0.1 else ""))
sys.exit(1 if bad or dur < D["total"] - 0.1 else 0)
