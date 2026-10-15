"""Three layout options as still frames, so the user can pick. The card takes the SCREEN's own shape (measured crop
aspect) and even pixel sizes, so the renderer never has to trim or letterbox much.
  A: face column on the right (largest face)   B: face in the lower-right corner   C: small face top-right (largest screen)
Usage: python layout_options.py <edit_dir> <share_src_second> [--talk <talk_src_second>]
Writes <edit_dir>/verify/layout_A|B|C.png and layout_options.json (paste the chosen "share"/"talk" into project.json).
"""
import argparse, json, subprocess
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

SKILL = Path(__file__).resolve().parent.parent
ap = argparse.ArgumentParser(); ap.add_argument("edit_dir"); ap.add_argument("t", type=float); ap.add_argument("--talk", type=float)
a = ap.parse_args(); ED = Path(a.edit_dir); P = json.loads((ED / "project.json").read_text())
B = P["brand"]; rgb = lambda h: tuple(int(h.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
(ED / "verify").mkdir(exist_ok=True)


def frame(t):
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", P["video"], "-frames:v", "1", "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True).stdout
    from io import BytesIO
    return Image.open(BytesIO(raw)).convert("RGB")


def bg():
    im = Image.new("RGB", (1920, 1080), rgb(B["primary"])); d = ImageDraw.Draw(im)
    for y in range(1080): d.line([(0, y), (1920, y)], fill=tuple(int(c1 + (c2 - c1) * y / 1080) for c1, c2 in zip(rgb(B["primary"]), rgb(B["primary_dark"]))))
    return im


def card(im, src, box, r=22):
    x, y, w, h = box
    sh = Image.new("L", im.size, 0); ImageDraw.Draw(sh).rounded_rectangle((x + 4, y + 18, x + w + 4, y + h + 18), r, fill=120)
    im.paste(Image.new("RGB", im.size, (4, 30, 34)), (0, 0), sh.filter(ImageFilter.GaussianBlur(26)))
    m = Image.new("L", (w, h), 0); ImageDraw.Draw(m).rounded_rectangle((0, 0, w - 1, h - 1), r, fill=255)
    im.paste(src.resize((w, h), Image.LANCZOS), (x, y), m)


def face(im, src, fx, fy, d, name):
    m = Image.new("L", (d, d), 0); ImageDraw.Draw(m).ellipse((0, 0, d - 1, d - 1), fill=255)
    ImageDraw.Draw(im).ellipse((fx - 8, fy - 8, fx + d + 8, fy + d + 8), outline=rgb(B["accent"]), width=6)
    im.paste(src.resize((d, d), Image.LANCZOS), (fx, fy), m)
    f = ImageFont.truetype(str(SKILL / "templates/overlay/assets/fonts/Nunito.ttf"), max(20, d // 9))
    tw = f.getlength(name); ty = fy + d + 16
    ImageDraw.Draw(im).rounded_rectangle((fx + d / 2 - tw / 2 - 18, ty, fx + d / 2 + tw / 2 + 18, ty + f.size + 18), 99, fill=rgb(B["paper"]))
    ImageDraw.Draw(im).text((fx + d / 2, ty + (f.size + 18) / 2), name, font=f, fill=rgb(B["primary"]), anchor="mm")


fr = frame(a.t)
sx, sy, sw, sh_ = list(P["crops"]["share"].values())[0]
asp = sw / sh_; scr = fr.crop((sx, sy, sx + sw, sy + sh_))
fx_, fy_, fw, fh = P["crops"]["face"]; fc = fr.crop((fx_, fy_, fx_ + fw, fy_ + fh))
name = list(P["names"].values())[0]
opts = {}
for key, h, xy, fd, fpos in (("A", 850, (48, 56), 260, "col"), ("B", 880, (40, 40), 210, "corner"), ("C", 930, (40, 40), 160, "top")):
    w = int(round(h * asp))
    if xy[0] + w > 1920 - (fd + 90 if fpos == "col" else 40): w = 1920 - xy[0] - (fd + 90 if fpos == "col" else 40); h = int(round(w / asp))
    w, h = w // 2 * 2, h // 2 * 2             # even sizes (zooms and yuv420 need them); card = the content's own shape
    cb = [xy[0], xy[1], w, h]
    if fpos == "col": f = [xy[0] + w + (1920 - xy[0] - w - fd) // 2, 92, fd]
    elif fpos == "corner": f = [1920 - fd - 60, 1080 - fd - 90, fd]
    else: f = [1920 - fd - 40, 52, fd]
    im = bg(); card(im, scr, cb); face(im, fc, *f, name); im.save(ED / f"verify/layout_{key}.png")
    opts[key] = {"share": {"card": cb, "face": f}}
if a.talk is not None:
    tx, ty, tw, th = P["crops"]["talk"]; tf = frame(a.talk).crop((tx, ty, tx + tw, ty + th))
    h = 850; w = int(round(h * tw / th)) // 2 * 2; im = bg(); card(im, tf, [48, 56, w, h]); im.save(ED / "verify/layout_talk.png")
    for k in opts: opts[k]["talk"] = {"card": [48, 56, w, h]}
(ED / "layout_options.json").write_text(json.dumps(opts, indent=1))
print("wrote verify/layout_A.png, layout_B.png, layout_C.png" + (", layout_talk.png" if a.talk is not None else "") + " + layout_options.json")
