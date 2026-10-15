"""Sample-exact dialogue master. Each kept range is trimmed from the source audio to exactly its rendered
video length (frames/30), with 30ms fades, and silence is inserted for card gaps. Never build the master by
concatenating AAC segments: each carries encoder priming and the drift adds up (0.26s over 6 min).
Usage: python build_audio.py <edit_dir> [--sub preview]   -> <edit_dir>/audio/dialogue.wav
"""
import argparse, json, subprocess
from pathlib import Path
import numpy as np

SR = 48000


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("edit_dir"); ap.add_argument("--sub", default="preview")
    a = ap.parse_args(); ED = Path(a.edit_dir)
    P = json.loads((ED / "project.json").read_text())
    R = json.loads((ED / "edl.json").read_text())["ranges"]
    plan = json.loads((ED / "motion_plan.json").read_text())
    segs = json.loads((ED / "timeline.json").read_text())["segs"]
    durs = json.loads((ED / f"clips/durs_{a.sub}.json").read_text())
    src = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", P["video"], "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                                       capture_output=True, check=True).stdout, np.float32)
    fade = int(0.03 * SR); ramp = np.linspace(0, 1, fade, dtype=np.float32); parts = []
    for i, r in enumerate(R):
        for g in plan["gaps"]:
            if g["kind"] != "end" and abs(g["at"] - segs[i]["out_start"]) < 1e-3: parts.append(np.zeros(int(round(g["dur"] * SR)), np.float32))
        n = int(round(durs[i] * SR)); s = int(round(r["start"] * SR))
        seg = src[s:s + n].copy()
        if len(seg) < n: seg = np.pad(seg, (0, n - len(seg)))
        seg[:fade] *= ramp; seg[-fade:] *= ramp[::-1]; parts.append(seg)
    for g in plan["gaps"]:
        if g["kind"] == "end": parts.append(np.zeros(int(round(g["dur"] * SR)), np.float32))
    out = np.concatenate(parts); wav = ED / "audio/dialogue.wav"; wav.parent.mkdir(exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-", "-c:a", "pcm_s24le", str(wav)],
                   input=out.tobytes(), check=True)
    print(f"wrote {wav}  {len(out) / SR:.3f}s  (plan total {plan['total']:.3f}s)")


if __name__ == "__main__":
    main()
