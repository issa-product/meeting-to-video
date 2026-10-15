"""Sound design: SFX tied to visible events, a ducked music bed, one loudness master.

  sheet <edit_dir>                         print the cue sheet from audio/sfx_plan.json  (USER APPROVES THIS FIRST)
  gen   <edit_dir>                         generate missing SFX with ElevenLabs (cached), measure each one's attack
  music <edit_dir> <out.mp3> "<prompt>"    generate a music option (ElevenLabs music); or use the user's own track
  mix   <edit_dir> [--music f] [--duck 13] dialogue + SFX (each starts `attack` early so it lands ON the frame)
                                           + music ducked under speech, faded before the end card
                                           -> two-pass loudnorm -14 LUFS / -1 dBTP -> audio/master.wav, prints numbers

audio/sfx_plan.json: {"cues": [{"id": "whoosh_ch2", "t": 22.63, "prompt": "short soft whoosh, airy",
                                "dur": 0.8, "gain_db": -8, "event": "chapter 2 card slides in"}]}
t = output time of the VISIBLE event (card landing, stamp hit, zoom start). Keep it sparse: ~1 cue per 3-4s at most.
"""
import json, os, subprocess, sys
from pathlib import Path
import numpy as np
import requests

SR = 48000


def key():
    k = os.environ.get("ELEVENLABS_API_KEY")
    if k: return k.strip()
    env = Path.home() / ".config/meeting-to-video/.env"
    for line in env.read_text().splitlines() if env.exists() else []:
        if line.startswith("ELEVENLABS_API_KEY="): return line.split("=", 1)[1].strip()
    sys.exit("No ElevenLabs key (see setup/SETUP.md).")


def pcm(path):
    return np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                                        capture_output=True, check=True).stdout, np.float32)


def attack(path):
    a = np.abs(pcm(path)); pk = a.max() or 1
    i = int(np.argmax(a > pk * 0.0316))   # first sample above -30 dB of the peak
    return round(i / SR, 3)


def main():
    cmd, ED = sys.argv[1], Path(sys.argv[2]); A = ED / "audio"; (A / "sfx").mkdir(parents=True, exist_ok=True)
    plan_p = A / "sfx_plan.json"
    plan = json.loads(plan_p.read_text()) if plan_p.exists() else {"cues": []}
    if cmd == "sheet":
        print(f"{'time':>8}  {'gain':>5}  {'sound':38s}  event")
        for c in sorted(plan["cues"], key=lambda c: c["t"]):
            print(f"{int(c['t'] // 60)}:{c['t'] % 60:05.2f}  {c.get('gain_db', -8):>5}  {c['prompt'][:38]:38s}  {c.get('event', '')}")
        print(f"{len(plan['cues'])} cues")
    elif cmd == "gen":
        for c in plan["cues"]:
            f = A / "sfx" / f"{c['id']}.mp3"
            if not f.exists():
                r = requests.post("https://api.elevenlabs.io/v1/sound-generation", headers={"xi-api-key": key()},
                                  json={"text": c["prompt"], "duration_seconds": c.get("dur", 1.0), "prompt_influence": 0.45}, timeout=120)
                if r.status_code != 200: sys.exit(f"SFX error {r.status_code}: {r.text[:300]}")
                f.write_bytes(r.content); print("generated", f.name)
            c["attack"] = attack(f)
        plan_p.write_text(json.dumps(plan, indent=1)); print("attacks measured")
    elif cmd == "music":
        out, prompt = Path(sys.argv[3]), sys.argv[4]
        total = json.loads((ED / "motion_plan.json").read_text())["total"]
        r = requests.post("https://api.elevenlabs.io/v1/music", headers={"xi-api-key": key()},
                          json={"prompt": prompt, "music_length_ms": int(min(total, 300) * 1000)}, timeout=600)
        if r.status_code != 200:
            sys.exit(f"Music API error {r.status_code}: {r.text[:300]}\nFallback: ask the user for a royalty-free track (mp3/wav).")
        out.write_bytes(r.content); print("music ->", out)
    elif cmd == "mix":
        args = sys.argv[3:]; music = args[args.index("--music") + 1] if "--music" in args else None
        duck = float(args[args.index("--duck") + 1]) if "--duck" in args else 13.0
        D = json.loads((ED / "mg/data.js").read_text()[len("window.DATA = "):-2]); total = D["total"]; end_start = D["end"]["start"]
        ins = ["-i", str(A / "dialogue.wav")]; fil = []; mixin = ["[d]"]
        fil.append("[0:a]aformat=sample_rates=48000:channel_layouts=mono,asplit=2[d][key]")
        k = 1
        for c in plan["cues"]:
            ins += ["-i", str(A / "sfx" / f"{c['id']}.mp3")]
            ms = max(0, int(round((c["t"] - c.get("attack", 0)) * 1000)))
            fil.append(f"[{k}:a]aformat=sample_rates=48000:channel_layouts=mono,volume={c.get('gain_db', -8)}dB,adelay={ms}:all=1[s{k}]")
            mixin.append(f"[s{k}]"); k += 1
        if music:
            ins += ["-stream_loop", "-1", "-i", music]
            fade_at = max(0, end_start - 1.5)
            fil.append(f"[{k}:a]aformat=sample_rates=48000:channel_layouts=mono,highpass=f=90,atrim=0:{total},volume=-6dB,"
                       f"afade=t=in:d=1.5,afade=t=out:st={fade_at:.2f}:d=1.5[mraw]")
            fil.append(f"[mraw][key]sidechaincompress=threshold=0.03:ratio={max(2, duck / 3):.1f}:attack=15:release=450[m]")
            mixin.append("[m]")
        else:
            fil.append("[key]anullsink")
        fil.append("".join(mixin) + f"amix=inputs={len(mixin)}:normalize=0:duration=first,alimiter=limit=0.97[mix]")
        raw = A / "mix_raw.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-y", *ins, "-filter_complex", ";".join(fil), "-map", "[mix]", "-t", f"{total}",
                        "-c:a", "pcm_s24le", str(raw)], check=True)
        m = subprocess.run(["ffmpeg", "-i", str(raw), "-af", "loudnorm=I=-14:TP=-1:LRA=11:print_format=json", "-f", "null", "-"],
                           capture_output=True, text=True).stderr
        j = json.loads(m[m.rindex("{"):m.rindex("}") + 1])
        af = (f"loudnorm=I=-14:TP=-1:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:measured_LRA={j['input_lra']}:"
              f"measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(raw), "-af", af, "-ar", "48000", "-c:a", "pcm_s24le", str(A / "master.wav")], check=True)
        r = subprocess.run(["ffmpeg", "-i", str(A / "master.wav"), "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True).stderr
        tail = r[r.rindex("Summary:"):]
        print("master ->", A / "master.wav"); print(tail.strip())
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
