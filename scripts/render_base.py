"""Base video: per-segment extract with the layout baked in, driven only by project.json (no per-video code).

For every EDL range it classifies each 0.1s (using the colour signatures Claude measured): mode (share/talk),
which screen (for multi-app shares), who is on camera. Then one ffmpeg graph per segment: paint boxes (e.g. over
Zoom's face tile, so the slide is never cropped) -> blur boxes -> crop -> LETTERBOX into the card (never trims
content) -> verified zooms only -> rounded card on the brand plate, face circle + name tag (share) or speaker
card + tag (talk), screen offsets, 30ms audio fades, 30fps. All sizes even. Gap holds come from motion_plan.json.
Lossless concat -> base_preview.mp4 / base_final.mp4.

Usage: python render_base.py <edit_dir> [--preview] [--only 3,4] [--jobs 4] [--concat-only]
"""
import argparse, json, subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np

STEP, RAMP = 0.1, 0.8


def load(ED):
    P = json.loads((ED / "project.json").read_text())
    plan = json.loads((ED / "motion_plan.json").read_text()) if (ED / "motion_plan.json").exists() else dict(zooms=[], gaps=[])
    tl = json.loads((ED / "timeline.json").read_text()) if (ED / "timeline.json").exists() else None
    return P, plan, tl


def grab(src, a, b, reg):
    x, y, w, h = reg
    out = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{a:.3f}", "-to", f"{b:.3f}", "-i", src, "-vf",
                          f"fps={1 / STEP:g},crop={w}:{h}:{x}:{y}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(out, np.uint8).reshape(-1, h, w, 3).astype(int)


def nearest(vals, rgb):
    return min(vals, key=lambda k: sum((a - b) ** 2 for a, b in zip(vals[k], rgb)))


def runs(states, min_len=4):
    """[(state, t0, t1)]; flicker shorter than min_len samples merges into its neighbour."""
    st = list(states)
    for _ in range(2):
        i = 0
        while i < len(st):
            j = i
            while j < len(st) and st[j] == st[i]: j += 1
            if j - i < min_len and (i > 0 or j < len(st)): st[i:j] = [st[i - 1] if i > 0 else st[j]] * (j - i)
            i = j
    res, s = [], 0
    for i in range(1, len(st) + 1):
        if i == len(st) or st[i] != st[s]: res.append((st[s], round(s * STEP, 2), round(i * STEP, 2))); s = i
    return res


def even(v): return int(v) // 2 * 2


def letterbox(crop, cw, ch):
    """Fit the crop INSIDE the card (no trimming, no stretching); returns even (crop, fit_w, fit_h)."""
    x, y, w, h = crop; w, h = even(w), even(h)
    s = min(cw / w, ch / h)
    return [x, y, w, h], even(round(w * s)), even(round(h * s))


def offset_for(P, a):
    for o in P.get("screen_offsets", []):
        if o["src"] <= a < o["src"] + 1.0: return o
    return None


def analyze(P, src, a, b):
    C = P["classify"]
    m = C["mode"]; reg = grab(src, a, b, m["probe"])
    share = [(np.abs(f - m["share_rgb"]).max(2) < m.get("tol", 40)).mean() > 0.3 for f in reg]
    mode = "share" if sum(share) >= len(share) / 2 else "talk"
    o = offset_for(P, a); so = o["offset"] if o else 0.0
    screens = [("default", 0, round(len(share) * STEP, 2))]
    if mode == "share" and len(C.get("screen", {}).get("values", {})) > 1:
        sc = grab(src, a + so, b + so, C["screen"]["probe"])
        screens = runs([nearest(C["screen"]["values"], f.reshape(-1, 3).mean(0)) for f in sc], 3)
    who_cfg = C["who"].get(mode)
    wsrc = (a + so, b + so) if (o and o.get("face")) else (a, b)
    if who_cfg:
        fr = grab(src, *wsrc, who_cfg["probe"])
        who = runs([nearest(who_cfg["values"], f.reshape(-1, 3).mean(0)) for f in fr])
    else:
        who = [(list(P["names"])[0], 0, b - a)]
    return mode, screens, who, bool(0 < sum(share) < len(share))


def enable(rs, state):
    p = [f"between(t\\,{t0:.2f}\\,{t1 - 0.001:.3f})" for s, t0, t1 in rs if s == state]
    return "+".join(p) if p else "0"


def zoom_terms(plan, off, d):
    terms = []
    for z in plan.get("zooms", []):
        if not z.get("verified"): continue      # zooms render only after zoom_check.py passed
        if z["t0"] < off + d and z["t1"] > off:
            T = f"(t+{off:.4f})"
            p = f"min(clip(({T}-{z['t0']:.3f})/{RAMP}\\,0\\,1)\\,clip(({z['t1']:.3f}-{T})/{RAMP}\\,0\\,1))"
            terms.append((z, f"{z['z'] - 1:.3f}*if(lt({p}\\,0.5)\\,4*pow({p}\\,3)\\,1-pow(-2*{p}+2\\,3)/2)"))
    return terms


def build(ED, P, plan, seg_out, i, r, preview, out):
    src = P["video"]; a, b = r["start"], r["end"]; d = b - a
    mode, screens, who, mixed = analyze(P, src, a, b)
    L = P["layout"][mode]; cx, cy, cw, ch = L["card"]
    if cw % 2 or ch % 2: raise SystemExit(f"layout.{mode}.card {L['card']}: width and height must be even (zooms need it)")
    lay = ED / "layout"; tags = json.loads((lay / "layout.json").read_text())["tags"]
    o = offset_for(P, a); so = o["offset"] if o else 0.0
    share_end = P.get("share_end")
    vid_len = (min(b, share_end) - a) if share_end and b > share_end else d
    imgs = [f"bg_{mode}", f"mask_{mode}"] + (["facemask", "facering"] if mode == "share" and "face" in L else []) + [f"tag_{s}" for s in P["names"]]
    ins = ["-ss", f"{a:.3f}", "-t", f"{d:.3f}", "-i", src]
    for im in imgs: ins += ["-loop", "1", "-t", f"{d:.3f}", "-i", str(lay / f"{im}.png")]
    k_extra = len(imgs) + 1
    if so: ins += ["-ss", f"{a + so:.3f}", "-t", f"{d:.3f}", "-i", src]
    pad = f",tpad=stop_mode=clone:stop_duration={d - vid_len + 0.2:.3f},trim=duration={d:.3f}" if vid_len < d - 0.01 else ""
    f = [f"[0:v]setpts=PTS-STARTPTS,trim=duration={vid_len:.3f}{pad},fps=30,split[s0][fs0]"]
    if so:
        f.append(f"[{k_extra}:v]setpts=PTS-STARTPTS,fps=30,split[s][fsx];[s0]nullsink")
        f.append("[fsx]null[fs];[fs0]nullsink" if o.get("face") else "[fsx]nullsink;[fs0]null[fs]")
    else:
        f.append("[s0]null[s];[fs0]null[fs]")
    # paint boxes: flat colour over things that sit ON the content (Zoom's face tile, notifications), source px
    paints = [pb for pb in P.get("paint", []) if pb.get("src_from", 0) < b and pb.get("src_to", 1e9) > a]
    if paints:
        boxes = []
        for pb in paints:
            x, y, w, h = pb["rect"]; la, lb = max(0, pb.get("src_from", 0) - a), min(d, pb.get("src_to", 1e9) - a)
            boxes.append(f"drawbox=x={x}:y={y}:w={w}:h={h}:color=0x{pb['color'].lstrip('#')}@1:t=fill:enable='between(t\\,{la:.2f}\\,{lb:.2f})'")
        f.append(f"[s]{','.join(boxes)}[sp]")
    else:
        f.append("[s]null[sp]")
    # blur boxes (source px, active when this segment overlaps their source range)
    blurs = [bx for bx in P.get("blur", []) if bx["src_from"] < b and bx["src_to"] > a]
    if blurs:
        f.append(f"[sp]split={len(blurs) + 1}" + "".join(f"[bl{j}]" for j in range(len(blurs) + 1)))
        last = "bl0"
        for j, bx in enumerate(blurs, 1):
            x, y, w, h = bx["rect"]
            f.append(f"[bl{j}]crop={w}:{h}:{x}:{y},boxblur=10:2[bb{j}];[{last}][bb{j}]overlay={x}:{y}[bo{j}]"); last = f"bo{j}"
        f.append(f"[{last}]null[sb]")
    else:
        f.append("[sp]null[sb]")
    # screen crop(s) -> card (with zoom)
    crops = P["crops"]["share"] if mode == "share" else {"default": P["crops"]["talk"]}
    names = sorted({s for s, _, _ in screens})
    zt = zoom_terms(plan, seg_out, d) if (mode == "share" and seg_out is not None) else []
    pad_rgb = P.get("letterbox", "#FFFFFF").lstrip("#")
    f.append(f"[sb]split={len(names)}" + "".join(f"[a_{n}]" for n in names))
    for n in names:
        (X, Y, CW, CH), FW, FH = letterbox(crops.get(n, crops.get("default")), cw, ch)
        fitc = f"crop={CW}:{CH}:{X}:{Y},scale={FW}:{FH}:flags=lanczos,pad={cw}:{ch}:{(cw - FW) // 2}:{(ch - FH) // 2}:color=0x{pad_rgb}"
        if zt:
            zs = "+".join(e for _, e in zt)
            px = "+".join(f"{cw}*{z['fx']}*({e})" for z, e in zt); py = "+".join(f"{ch}*{z['fy']}*({e})" for z, e in zt)
            f.append(f"[a_{n}]{fitc},scale=w='2*trunc({cw}*(1+{zs})/2)':h='2*trunc({ch}*(1+{zs})/2)':eval=frame:flags=lanczos,"
                     f"crop={cw}:{ch}:'{px}':'{py}',format=rgba[c_{n}]")
        else:
            f.append(f"[a_{n}]{fitc},format=rgba[c_{n}]")
    f.append(f"[2:v]format=gray,split={len(names)}" + "".join(f"[m_{n}]" for n in names))
    last = "1:v"
    for j, n in enumerate(names):
        en = "" if len(names) == 1 else f":enable='{enable(screens, n)}'"
        f.append(f"[c_{n}][m_{n}]alphamerge[k_{n}];[{last}][k_{n}]overlay={cx}:{cy}{en}[o{j}]"); last = f"o{j}"
    t0 = 3
    if mode == "share" and "face" in L:
        fx, fy, fd = L["face"]; Fx, Fy, Fw, Fh = P["crops"]["face"]
        f.append(f"[fs]crop={Fw}:{Fh}:{Fx}:{Fy},scale={fd}:{fd}:flags=lanczos,format=rgba[fc];[3:v]format=gray[fm];[fc][fm]alphamerge[face]")
        f.append(f"[{last}][4:v]overlay={fx - 8}:{fy - 8}[r1];[r1][face]overlay={fx}:{fy}[r2]"); last, t0 = "r2", 5
    else:
        f.append("[fs]nullsink")
    for j, spk in enumerate(P["names"]):
        tx, ty = tags[f"{mode}_{spk}"]
        f.append(f"[{last}][{t0 + j}:v]overlay={tx}:{ty}:enable='{enable(who, spk)}'[t{j}]"); last = f"t{j}"
    f.append(f"[{last}]" + ("scale=1280:720:flags=lanczos," if preview else "") + "format=yuv420p[v]")
    f.append(f"[0:a]afade=t=in:st=0:d=0.03,afade=t=out:st={max(0, d - 0.03):.3f}:d=0.03[aout]")
    gd = ED / "clips/graphs"; gd.mkdir(parents=True, exist_ok=True); (gd / f"seg_{i:03d}.txt").write_text(";\n".join(f))
    subprocess.run(["ffmpeg", "-v", "error", "-y", *ins, "-filter_complex_script", str(gd / f"seg_{i:03d}.txt"), "-map", "[v]",
                    "-map", "[aout]", "-t", f"{d:.3f}", "-c:v", "libx264", "-preset", "veryfast" if preview else "medium",
                    "-crf", "24" if preview else "18", "-r", "30", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", str(out)], check=True)
    return dict(i=i, src=a, mode=mode, screens=screens, who=who, mixed=mixed, zoom=bool(zt))


def gap_clip(ED, g, preview, out):
    vf = "fps=30,format=yuv420p" + (",scale=1280:720:flags=lanczos" if preview else "")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-loop", "1", "-t", f"{g['dur']:.3f}", "-i", str(ED / "layout/bg_share.png" if (ED / "layout/bg_share.png").exists() else ED / "layout/bg_talk.png"),
                    "-f", "lavfi", "-t", f"{g['dur']:.3f}", "-i", "anullsrc=r=48000:cl=mono", "-vf", vf, "-c:v", "libx264",
                    "-preset", "veryfast" if preview else "medium", "-crf", "24" if preview else "18", "-r", "30", "-c:a", "aac",
                    "-b:a", "192k", "-ar", "48000", "-shortest", str(out)], check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("edit_dir"); ap.add_argument("--preview", action="store_true"); ap.add_argument("--only")
    ap.add_argument("--jobs", type=int, default=4); ap.add_argument("--concat-only", action="store_true")
    a = ap.parse_args(); ED = Path(a.edit_dir).resolve()
    P, plan, tl = load(ED)
    R = json.loads((ED / "edl.json").read_text())["ranges"]
    seg_out = [s["out_start"] for s in tl["segs"]] if tl else [None] * len(R)
    sub = "preview" if a.preview else "final"; od = ED / "clips" / sub; od.mkdir(parents=True, exist_ok=True)
    idx = [] if a.concat_only else ([int(x) for x in a.only.split(",")] if a.only else range(len(R)))
    with ThreadPoolExecutor(a.jobs) as ex:
        logs = list(ex.map(lambda i: build(ED, P, plan, seg_out[i], i, R[i], a.preview, od / f"seg_{i:03d}.mp4"), idx))
    if logs:
        lp = ED / "clips" / f"log_{sub}.json"
        old = {x["i"]: x for x in json.loads(lp.read_text())} if lp.exists() else {}
        for x in logs: old[x["i"]] = x
        lp.write_text(json.dumps([old[k] for k in sorted(old)]))
    if not a.only:
        files = []
        for i in range(len(R)):
            for k, g in enumerate(plan.get("gaps", [])):
                if g["kind"] != "end" and seg_out[i] is not None and abs(g["at"] - seg_out[i]) < 1e-3:
                    p = od / f"gap_{k:02d}.mp4"; gap_clip(ED, g, a.preview, p); files.append(p)
            files.append(od / f"seg_{i:03d}.mp4")
        for k, g in enumerate(plan.get("gaps", [])):
            if g["kind"] == "end": p = od / f"gap_{k:02d}.mp4"; gap_clip(ED, g, a.preview, p); files.append(p)
        lst = ED / "clips" / f"concat_{sub}.txt"; lst.write_text("".join(f"file '{p}'\n" for p in files))
        out = ED / f"base_{sub}.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", "-movflags", "+faststart", str(out)], check=True)
        print("wrote", out)
    mixed = [x["i"] for x in logs if x.get("mixed")]
    print(f"segments: {len(logs)}" + (f"  CHECK these (mode changes mid-segment): {mixed}" if mixed else ""))


if __name__ == "__main__":
    main()
