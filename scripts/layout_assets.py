"""Brand plates, rounded-card masks, face circle + ring and name tags, from project.json.
Usage: python layout_assets.py <edit_dir>   -> <edit_dir>/layout/*.png + layout.json (tag positions)
"""
import json, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

SKILL = Path(__file__).resolve().parent.parent
ED = Path(sys.argv[1]); P = json.loads((ED / "project.json").read_text())
OUT = ED / "layout"; OUT.mkdir(exist_ok=True)
B = P["brand"]; FONT = str(SKILL / "templates/overlay/assets/fonts/Nunito.ttf")
W, H, R = 1920, 1080, 22
rgb = lambda h: tuple(int(h.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))


def font(size):
    f = ImageFont.truetype(FONT, size)
    try: f.set_variation_by_axes([800])
    except Exception: pass
    return f


def plate(card, face=None):
    a, b = rgb(B["primary"]), rgb(B["primary_dark"])
    bg = Image.new("RGB", (W, H)); px = bg.load()
    for y in range(H):
        for x in range(W):
            t = min(1, max(0, (x / W) * 0.45 + (y / H) * 0.55))
            px[x, y] = tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))
    glow = Image.new("L", (W, H), 0); ImageDraw.Draw(glow).ellipse((-300, -400, 900, 500), fill=60)
    bg = Image.composite(Image.new("RGB", (W, H), (255, 255, 255)), bg, glow.filter(ImageFilter.GaussianBlur(160)))
    x, y, w, h = card
    sh = Image.new("L", (W, H), 0); ImageDraw.Draw(sh).rounded_rectangle((x + 4, y + 18, x + w + 4, y + h + 18), R, fill=120)
    bg = Image.composite(Image.new("RGB", (W, H), (4, 30, 34)), bg, sh.filter(ImageFilter.GaussianBlur(28)))
    if face:
        fx, fy, d = face
        s2 = Image.new("L", (W, H), 0); ImageDraw.Draw(s2).ellipse((fx - 6, fy + 4, fx + d + 6, fy + d + 16), fill=110)
        bg = Image.composite(Image.new("RGB", (W, H), (4, 30, 34)), bg, s2.filter(ImageFilter.GaussianBlur(16)))
    return bg


def rmask(w, h, r):
    m = Image.new("L", (w * 4, h * 4), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, w * 4 - 1, h * 4 - 1), r * 4, fill=255)
    return m.resize((w, h), Image.LANCZOS)


def tag(name):
    f = font(60); tw = int(f.getlength(name)) // 2; hh = 52
    im = Image.new("RGBA", ((tw + 44) * 2, hh * 2), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((0, 0, im.width - 1, im.height - 1), hh, fill=rgb(B["paper"]) + (255,))
    d.text((im.width / 2, im.height / 2 + 1), name, font=f, fill=rgb(B["primary"]), anchor="mm")
    return im.resize((im.width // 2, im.height // 2), Image.LANCZOS)


L = P["layout"]; meta = {"tags": {}}
for mode in ("share", "talk"):
    if mode not in L: continue
    m = L[mode]
    plate(m["card"], m.get("face")).save(OUT / f"bg_{mode}.png")
    rmask(m["card"][2], m["card"][3], R).save(OUT / f"mask_{mode}.png")
if "face" in L.get("share", {}):
    fx, fy, d = L["share"]["face"]
    cm = Image.new("L", (d * 4, d * 4), 0); ImageDraw.Draw(cm).ellipse((0, 0, d * 4 - 1, d * 4 - 1), fill=255)
    cm.resize((d, d), Image.LANCZOS).save(OUT / "facemask.png")
    ring = Image.new("RGBA", ((d + 16) * 4, (d + 16) * 4), (0, 0, 0, 0))
    ImageDraw.Draw(ring).ellipse((0, 0, (d + 16) * 4 - 1, (d + 16) * 4 - 1), outline=rgb(B["accent"]) + (255,), width=24)
    ring.resize((d + 16, d + 16), Image.LANCZOS).save(OUT / "facering.png")
for spk, name in P["names"].items():
    t = tag(name); t.save(OUT / f"tag_{spk}.png")
    if "share" in L and "face" in L["share"]:
        fx, fy, d = L["share"]["face"]; meta["tags"][f"share_{spk}"] = [fx + d // 2 - t.width // 2, fy + d + 18]
    if "talk" in L:
        cx, cy, cw, ch = L["talk"]["card"]; meta["tags"][f"talk_{spk}"] = [cx + 28, cy + ch - 28 - t.height]
(OUT / "layout.json").write_text(json.dumps(meta, indent=1))
print("layout assets ->", OUT, meta["tags"])
