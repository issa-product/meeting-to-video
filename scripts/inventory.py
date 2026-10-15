"""Screen inventory (before the plan): split every screen-share stretch into distinct SCREENS (a slide, a page, an
app view) and give each a kind hint. Claude confirms each kind by looking, and the plan shows the choice per section:
  text   (title, bullets, simple table)          -> replaced by a STAGE scene (full motion scene in the card)
  visual (chart, screenshot, diagram, board, UI) -> shown in full; graphics only in the side column / label chip
Usage: python inventory.py <edit_dir> [--min 3]   (needs project.json crops + classify.mode)
Writes inventory.json (edit "kind" where the hint is wrong) and verify/inventory.jpg (numbered thumbnails).
"""
import argparse, json, subprocess
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

ap = argparse.ArgumentParser(); ap.add_argument("edit_dir"); ap.add_argument("--min", type=float, default=3.0)
a = ap.parse_args(); ED = Path(a.edit_dir); P = json.loads((ED / "project.json").read_text())
V = P["video"]; M = P["classify"]["mode"]
x, y, w, h = list(P["crops"]["share"].values())[0]
TW, TH = 320, int(320 * h / w) // 2 * 2
mx, my, mw, mh = M["probe"]
crop_f = subprocess.run(["ffmpeg", "-v", "error", "-i", V, "-vf", f"fps=1,crop={w}:{h}:{x}:{y},scale={TW}:{TH}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                        capture_output=True, check=True).stdout
mode_f = subprocess.run(["ffmpeg", "-v", "error", "-i", V, "-vf", f"fps=1,crop={mw}:{mh}:{mx}:{my}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                        capture_output=True, check=True).stdout
F = np.frombuffer(crop_f, np.uint8).reshape(-1, TH, TW, 3).astype(np.int16)
Mo = np.frombuffer(mode_f, np.uint8).reshape(-1, mh, mw, 3).astype(np.int16)
n = min(len(F), len(Mo))
share = [bool((np.abs(Mo[i] - M["share_rgb"]).max(2) < M.get("tol", 40)).mean() > 0.3) for i in range(n)]


def kind_hint(img):
    """text: a flat background dominates and colour is sparse; visual: lots of non-background, colourful or photographic."""
    g = img.mean(2); bg = np.median(g)
    flat = (np.abs(g - bg) < 12).mean()
    chroma = (img.max(2) - img.min(2)).mean()
    return ("text" if flat > 0.72 and chroma < 22 else "visual"), round(float(flat), 2), round(float(chroma), 1)


screens, cur = [], None
for i in range(n):
    if not share[i]:
        if cur: screens.append(cur); cur = None
        continue
    if cur is not None and np.abs(F[i] - F[cur["ref"]]).mean() > 9:   # a different slide/page/view
        screens.append(cur); cur = None
    if cur is None: cur = dict(src_from=i, src_to=i + 1, ref=i)
    else: cur["src_to"] = i + 1
if cur: screens.append(cur)
screens = [s for s in screens if s["src_to"] - s["src_from"] >= a.min]
out, tiles = [], []
for k, s in enumerate(screens):
    mid = (s["src_from"] + s["src_to"]) // 2
    hint, flat, chroma = kind_hint(F[mid])
    out.append(dict(id=k + 1, src_from=s["src_from"], src_to=s["src_to"], kind_hint=hint, kind=hint, flat=flat, chroma=chroma, note=""))
    im = Image.fromarray(F[mid].astype(np.uint8)); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, 200, 22], fill=(0, 0, 0)); d.text((5, 5), f"#{k + 1} {s['src_from'] // 60}:{s['src_from'] % 60:02d} {hint}", fill=(255, 220, 0))
    tiles.append(im)
(ED / "inventory.json").write_text(json.dumps(out, indent=1))
if tiles:
    cols = 5; rows = (len(tiles) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (TW + 4), rows * (TH + 4)), (25, 25, 25))
    for k, im in enumerate(tiles): sheet.paste(im, ((k % cols) * (TW + 4), (k // cols) * (TH + 4)))
    (ED / "verify").mkdir(exist_ok=True); sheet.save(ED / "verify/inventory.jpg", quality=82)
print(f"{len(out)} screens: {sum(o['kind'] == 'text' for o in out)} text (-> stage), {sum(o['kind'] == 'visual' for o in out)} visual (-> full + column)")
for o in out: print(f"  #{o['id']:<3} {o['src_from'] // 60}:{o['src_from'] % 60:02d}-{o['src_to'] // 60}:{o['src_to'] % 60:02d}  {o['kind']}")
print("LOOK at verify/inventory.jpg and fix any wrong 'kind' in inventory.json before writing the plan.")
