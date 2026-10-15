"""Inspection tools Claude uses to MEASURE a recording (look first, then write numbers into project.json).

  sheet  <video> <out.jpg> [--every 45] [--start 0] [--end END]   contact sheet, timestamp on every tile
  grab   <video> <t> <out.png> [--crop x,y,w,h] [--scale 1]        one full-res frame (optionally cropped/zoomed)
  probe  <video> <x,y,w,h> <t1,t2,...>                             mean RGB + brightness of a region at times
  rowscan <video> <t> <x0,x1> <y0,y1>                              per-row mean brightness (find chrome/URL-bar edges)
  colscan <video> <t> <y0,y1> <x0,x1>                              per-column mean brightness (find window side edges)
  words  <transcript.json> <from> <to> [<from> <to> ...]           word@time dump for cut points and anchors
  share  <video> <x,y,w,h> <r,g,b> [--tol 40]                      seconds where a region matches a colour (e.g. Zoom's
                                                                   green share border) -> on/off ranges
"""
import json, subprocess, sys
from pathlib import Path
import numpy as np


def frame(video, t, crop=None):
    vf = f"crop={crop[2]}:{crop[3]}:{crop[0]}:{crop[1]}" if crop else "null"
    out = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t}", "-i", video, "-frames:v", "1", "-vf", vf, "-f", "rawvideo",
                          "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
    wh = crop[2:] if crop else size(video)
    return np.frombuffer(out, np.uint8).reshape(wh[1], wh[0], 3).astype(int)


def size(video):
    o = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height", "-of", "csv=p=0",
                        video], capture_output=True, text=True).stdout.strip().split(",")
    return int(o[0]), int(o[1])


def duration(video):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video],
                                capture_output=True, text=True).stdout)


def ints(s): return [int(float(v)) for v in s.split(",")]


def main():
    cmd, args = sys.argv[1], sys.argv[2:]
    opt = {args[i][2:]: args[i + 1] for i in range(len(args)) if args[i].startswith("--")}
    pos = [a for i, a in enumerate(args) if not a.startswith("--") and (i == 0 or not args[i - 1].startswith("--"))]
    if cmd == "sheet":
        from PIL import Image, ImageDraw
        video, out = pos[0], pos[1]
        every, start = float(opt.get("every", 45)), float(opt.get("start", 0))
        end = float(opt.get("end", duration(video)))
        tiles, t = [], start + 2
        while t < end and len(tiles) < 48:
            raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t}", "-i", video, "-frames:v", "1", "-vf", "scale=480:270",
                                  "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True).stdout
            if len(raw) == 480 * 270 * 3:
                im = Image.frombytes("RGB", (480, 270), raw); d = ImageDraw.Draw(im)
                d.rectangle([0, 0, 92, 22], fill=(0, 0, 0)); d.text((6, 5), f"{int(t // 60)}:{int(t % 60):02d} ({t:.0f}s)", fill=(255, 255, 0))
                tiles.append(im)
            t += every
        cols = 6; rows = (len(tiles) + cols - 1) // cols
        sheet = Image.new("RGB", (cols * 484, rows * 274), (25, 25, 25))
        for k, im in enumerate(tiles): sheet.paste(im, ((k % cols) * 484, (k // cols) * 274))
        sheet.save(out, quality=82); print(f"wrote {out} ({len(tiles)} tiles every {every:.0f}s)")
    elif cmd == "grab":
        from PIL import Image
        video, t, out = pos[0], float(pos[1]), pos[2]
        crop = ints(opt["crop"]) if "crop" in opt else None
        f = frame(video, t, crop).astype(np.uint8); im = Image.fromarray(f)
        sc = float(opt.get("scale", 1))
        if sc != 1: im = im.resize((int(im.width * sc), int(im.height * sc)), Image.LANCZOS)
        im.save(out); print(f"wrote {out} {im.size}")
    elif cmd == "probe":
        video, reg, ts = pos[0], ints(pos[1]), [float(v) for v in pos[2].split(",")]
        for t in ts:
            f = frame(video, t, reg); m = f.reshape(-1, 3).mean(0)
            print(f"t={t:8.2f}  rgb=({m[0]:.0f},{m[1]:.0f},{m[2]:.0f})  bright={m.mean():.0f}  warmth(R-B)={m[0] - m[2]:.0f}")
    elif cmd in ("rowscan", "colscan"):
        video, t = pos[0], float(pos[1])
        a0, a1 = ints(pos[2]); b0, b1 = ints(pos[3])
        f = frame(video, t).mean(2)
        if cmd == "rowscan":
            prof = f[b0:b1, a0:a1].mean(1); base = b0
        else:
            prof = f[a0:a1, b0:b1].mean(0); base = b0
        for i, v in enumerate(prof):
            jump = abs(v - prof[i - 1]) if i else 0
            print(f"{base + i:5d}  {v:6.1f}" + ("   <-- edge" if jump > 12 else ""))
    elif cmd == "words":
        W = [w for w in json.loads(Path(pos[0]).read_text())["words"] if w["type"] == "word"]
        rng = [float(v) for v in pos[1:]]
        for a, b in zip(rng[::2], rng[1::2]):
            print(f"--- {a}-{b}: " + " ".join(f"{w['text']}@{w['start']:.2f}" for w in W if a <= w["start"] <= b))
    elif cmd == "share":
        video, reg, col = pos[0], ints(pos[1]), ints(pos[2]); tol = float(opt.get("tol", 40))
        x, y, w, h = reg
        out = subprocess.run(["ffmpeg", "-v", "error", "-i", video, "-vf", f"fps=1,crop={w}:{h}:{x}:{y}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                             capture_output=True).stdout
        a = np.frombuffer(out, np.uint8).reshape(-1, h, w, 3).astype(int)
        on = [bool((np.abs(f - col).max(2) < tol).mean() > 0.3) for f in a]
        s = 0
        for i in range(1, len(on) + 1):
            if i == len(on) or on[i] != on[s]:
                print(f"{'ON ' if on[s] else 'off'}  {s // 60}:{s % 60:02d}-{i // 60}:{i % 60:02d}  ({s}-{i}s)"); s = i
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
