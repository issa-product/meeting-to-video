"""Style frames (sent WITH the plan, before any full render): ~4 stills of the real look, built from the real
recording + the chosen layout + the real overlay components. Nothing is rendered over time; it takes a minute.

edit/style.json:
{"frames": [
  {"src_t": 300, "mode": "share", "who": "speaker_0", "caption": "We pay it ourselves today",
   "chip": {"n": 1, "title": "The roadmap"},
   "graphics": [{"type": "stage", "layout": "bullets", "title": "Why it's a big project",
                 "items": [{"text": "We don't collect tax", "icon": "x"}, {"text": "Tax needs an address", "icon": "pin"}]}]},
  {"src_t": 850, "mode": "share", "graphics": [{"type": "list", "pos": "col", "title": "Proration", "rows": [{"text": "Pay the difference"}]}]},
  {"src_t": 1150, "mode": "talk", "who": "speaker_0", "graphics": [{"type": "big", "pos": "panel", "a": {"text": "Is it done?"}, "b": {"text": "In RC now"}}]},
  {"chapter": {"n": 2, "title": "What comes first", "kicker": "Impact x urgency"}}
]}
Graphics use the normal schema (references/motion-graphics.md) minus times. Usage: python style_frames.py <edit_dir>
-> verify/style_1..N.png + verify/style_sheet.jpg
"""
import copy, io, json, re, shutil, subprocess, sys
from pathlib import Path
from PIL import Image, ImageDraw

SKILL = Path(__file__).resolve().parent.parent
ED = Path(sys.argv[1]).resolve(); P = json.loads((ED / "project.json").read_text())
S = json.loads((ED / "style.json").read_text())["frames"]
PY = sys.executable
subprocess.run([PY, str(SKILL / "scripts/layout_assets.py"), str(ED)], check=True, capture_output=True)
L = ED / "layout"; tags = json.loads((L / "layout.json").read_text())["tags"]
SEG = 3.0
D = dict(total=len(S) * SEG + 1, title=dict(start=9999, dur=1), end=dict(start=9999, dur=1), chapters=[], chips=[], captions=[], bubbles=[],
         graphics=[], modes=[], nch=P.get("chapters_total", 6), names=P["names"], brand=P["brand"], layout=P["layout"])


def stamp_times(g, t):
    g = copy.deepcopy(g); g["t0"], g["t1"] = t + 0.1, t + SEG - 0.05
    def walk(o):
        if isinstance(o, dict):
            for k, v in list(o.items()):
                if isinstance(v, (dict, list)): walk(v)
            if "text" in o or "label" in o or "val" in o: o.setdefault("t", t + 0.15)
        elif isinstance(o, list):
            for v in o: walk(v)
    walk(g); g.setdefault("t", t + 0.15)
    return g


for k, f in enumerate(S):
    t = k * SEG; md = f.get("mode", "share")
    D["modes"].append(dict(mode=md, t0=t, t1=t + SEG))
    if "chapter" in f:
        c = f["chapter"]; D["chapters"].append(dict(n=max(2, c["n"]), title=c["title"], kicker=c.get("kicker", ""), start=t + 0.6, dur=2.2))
        continue
    for g in f.get("graphics", []): D["graphics"].append(stamp_times(g, t))
    if f.get("caption"):
        D["captions"].append(dict(t0=t + 0.1, t1=t + SEG - 0.05, mode=md, who=f.get("who", list(P["names"])[0]),
                                  w=[dict(x=w, t=t + 0.12, k=False) for w in f["caption"].split()]))
    if f.get("chip"): D["chips"].append(dict(n=f["chip"]["n"], title=f["chip"]["title"], t0=t - 0.3, t1=t + SEG + 0.4))
mg = ED / "verify/style_mg"
if mg.exists(): shutil.rmtree(mg)
shutil.copytree(SKILL / "templates/overlay", mg)
(mg / "data.js").write_text("window.DATA = " + json.dumps(D) + ";\n")
html = mg / "index.html"; html.write_text(re.sub(r'(id="root"[^>]*?data-duration=")[\d.]+(")', rf"\g<1>{D['total']}\g<2>", html.read_text()))
times = ",".join(f"{k * SEG + 2.0:.2f}" for k in range(len(S)))
snap = ED / "verify/style_snap"
if snap.exists(): shutil.rmtree(snap)
subprocess.run(["npx", "--yes", "hyperframes@0.7.60", "snapshot", "--at", times, "--no-end", "-o", str(snap)], cwd=mg, check=True, capture_output=True)
shots = sorted(snap.glob("frame-*.png"))


def src_frame(t):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", P["video"], "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True).stdout
    im = Image.open(io.BytesIO(raw)).convert("RGB"); d = ImageDraw.Draw(im)
    for pb in P.get("paint", []):
        if pb.get("src_from", 0) <= t < pb.get("src_to", 1e9):
            x, y, w, h = pb["rect"]; d.rectangle([x, y, x + w, y + h], fill="#" + pb["color"].lstrip("#"))
    return im


outs = []
for k, f in enumerate(S):
    md = f.get("mode", "share")
    base = Image.open(L / f"bg_{md}.png").convert("RGBA")
    if "src_t" in f:
        im = src_frame(f["src_t"]); cx, cy, cw, ch = P["layout"][md]["card"]
        x, y, w, h = (list(P["crops"]["share"].values())[0] if md == "share" else P["crops"]["talk"])
        s = min(cw / w, ch / h); fit = im.crop((x, y, x + w, y + h)).resize((int(w * s), int(h * s)), Image.LANCZOS)
        card = Image.new("RGB", (cw, ch), "#" + P.get("letterbox", "#FFFFFF").lstrip("#")); card.paste(fit, ((cw - fit.width) // 2, (ch - fit.height) // 2))
        base.paste(card, (cx, cy), Image.open(L / f"mask_{md}.png"))
        who = f.get("who", list(P["names"])[0])
        if md == "share" and "face" in P["layout"]["share"]:
            fx, fy, fd = P["layout"]["share"]["face"]; Fx, Fy, Fw, Fh = P["crops"]["face"]
            ring = Image.open(L / "facering.png"); base.alpha_composite(ring, (fx - 8, fy - 8))
            base.paste(im.crop((Fx, Fy, Fx + Fw, Fy + Fh)).resize((fd, fd), Image.LANCZOS), (fx, fy), Image.open(L / "facemask.png"))
        tg = Image.open(L / f"tag_{who}.png"); base.alpha_composite(tg, tuple(tags[f"{md}_{who}"]))
    ov = Image.open(shots[k]).convert("RGBA").resize((1920, 1080))
    base.alpha_composite(ov); out = ED / f"verify/style_{k + 1}.png"; base.convert("RGB").save(out); outs.append(out)
sheet = Image.new("RGB", (2 * 964, ((len(outs) + 1) // 2) * 546), (25, 25, 25))
for k, o in enumerate(outs): sheet.paste(Image.open(o).resize((960, 540)), ((k % 2) * 964, (k // 2) * 546))
sheet.save(ED / "verify/style_sheet.jpg", quality=85)
print(f"wrote {len(outs)} style frames -> verify/style_*.png, verify/style_sheet.jpg (send these with the plan)")
