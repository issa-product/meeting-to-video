"""Word-level transcript with speaker labels via ElevenLabs Scribe (cached: never re-transcribes a source).

Usage: python transcribe.py <video> <edit_dir> [--speakers 2]
Key: $ELEVENLABS_API_KEY, else ~/.config/meeting-to-video/.env (ELEVENLABS_API_KEY=...).
Writes <edit_dir>/transcripts/<name>.json (Scribe JSON: words[] with text/start/end/type/speaker_id).
"""
import argparse, json, os, subprocess, sys, tempfile
from pathlib import Path
import requests

API = "https://api.elevenlabs.io/v1/speech-to-text"


def api_key():
    k = os.environ.get("ELEVENLABS_API_KEY")
    if k: return k.strip()
    env = Path.home() / ".config/meeting-to-video/.env"
    if env.exists():
        for line in env.read_text().splitlines():
            if line.startswith("ELEVENLABS_API_KEY="): return line.split("=", 1)[1].strip()
    sys.exit("No ElevenLabs key. Run setup (see setup/SETUP.md) or export ELEVENLABS_API_KEY.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video"); ap.add_argument("edit_dir"); ap.add_argument("--speakers", type=int, default=2)
    a = ap.parse_args()
    out = Path(a.edit_dir) / "transcripts" / (Path(a.video).stem + ".json")
    if out.exists():
        print(f"cached: {out}"); return
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as td:
        wav = Path(td) / "audio.mp3"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", a.video, "-vn", "-ac", "1", "-ar", "16000", "-b:a", "64k", str(wav)], check=True)
        print(f"uploading {wav.stat().st_size / 1e6:.1f} MB to Scribe...")
        with open(wav, "rb") as fh:
            r = requests.post(API, headers={"xi-api-key": api_key()}, timeout=1800,
                              data={"model_id": "scribe_v1", "diarize": "true", "num_speakers": str(a.speakers),
                                    "timestamps_granularity": "word", "tag_audio_events": "true"},
                              files={"file": ("audio.mp3", fh, "audio/mpeg")})
    if r.status_code != 200:
        sys.exit(f"Scribe error {r.status_code}: {r.text[:400]}")
    out.write_text(json.dumps(r.json()))
    words = [w for w in r.json()["words"] if w["type"] == "word"]
    print(f"saved {out}  ({len(words)} words, speakers: {sorted({w.get('speaker_id') for w in words})})")


if __name__ == "__main__":
    main()
