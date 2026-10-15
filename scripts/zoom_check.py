"""Zoom check: renders each zoom at FULL zoom from the source (same paint + crop + letterbox as the renderer) and
checks the card edges for cut text. A zoom only renders once it passed here AND you looked at the still and set
verified=True in cues.py. Zooms are off by default; use them for a small UI detail on a visual screen, never on
text slides (those become stage scenes).
Usage: python zoom_check.py <edit_dir>   -> verify/zoom_<name>.png + PASS/FAIL per zoom (exit 1 on any FAIL)
"""
import io, json, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

ED = Path(sys.argv[1]); P = json.loads((ED / "project.json").read_text())
plan = json.loads((ED / "motion_plan.json").read_text()); segs = json.loads((ED / "timeline.json").read_text())["segs"]
cx, cy, cw, ch = P["layout"]["share"]["card"]; bad = 0
for z in plan["zooms"]:
    tm = (z["t0"] + z["t1"]) / 2
    s = next((s for s in segs if s["out_start"] <= tm < s["out_start"] + s["dur"]), None)
    if s is None: print(f"{z['name']}: midpoint outside the cut"); bad += 1; continue
    src = s["src_start"] + (tm - s["out_start"])
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{src:.2f}", "-i", P["video"], "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True).stdout
    im = Image.open(io.BytesIO(raw)).convert("RGB"); d = ImageDraw.Draw(im)
    for pb in P.get("paint", []):
        if pb.get("src_from", 0) <= src < pb.get("src_to", 1e9):
            x, y, w, h = pb["rect"]; d.rectangle([x, y, x + w, y + h], fill="#" + pb["color"].lstrip("#"))
    x, y, w, h = list(P["crops"]["share"].values())[0]   # zooms belong on the main screen crop
    scr = im.crop((x, y, x + w, y + h)); k = min(cw / w, ch / h)
    card = Image.new("RGB", (cw, ch), "#" + P.get("letterbox", "#FFFFFF").lstrip("#"))
    fit = scr.resize((int(w * k) // 2 * 2, int(h * k) // 2 * 2), Image.LANCZOS); card.paste(fit, ((cw - fit.width) // 2, (ch - fit.height) // 2))
    Z = card.resize((int(cw * z["z"]), int(ch * z["z"])), Image.LANCZOS)
    ox, oy = int(cw * (z["z"] - 1) * z["fx"]), int(ch * (z["z"] - 1) * z["fy"])
    view = Z.crop((ox, oy, ox + cw, oy + ch)); view.save(ED / f"verify/zoom_{z['name']}.png")
    g = np.asarray(view.convert("L")).astype(int)
    band = 8; edges = {"left": g[:, :band], "right": g[:, -band:], "top": g[:band, :], "bottom": g[-band:, :]}
    cut = []
    for side, b in edges.items():
        bgv = np.median(b); ink = (np.abs(b - bgv) > 60).mean()
        if ink > 0.03: cut.append(f"{side} {ink:.0%}")
    ok = not cut; bad += 0 if ok else 1
    print(f"{z['name']}: {'PASS' if ok else 'FAIL: text likely cut at ' + ', '.join(cut)}  -> verify/zoom_{z['name']}.png "
          f"(look at it; set verified=True in cues.py only if nothing important is cut)")
sys.exit(1 if bad else 0)
