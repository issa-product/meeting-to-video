# Setup (Claude does this; ask before each install)

Run `bash ~/.claude/skills/meeting-to-video/setup/doctor.sh`. It prints what's missing. Fix each item:

| Need | Why | macOS | Linux (Debian/Ubuntu) |
|---|---|---|---|
| ffmpeg + ffprobe (with libvpx-vp9) | cutting, layout, zooms, compositing | `brew install ffmpeg` | `sudo apt-get install -y ffmpeg` |
| Python 3.10+ | layout assets, timing, audio | `brew install python` | `sudo apt-get install -y python3 python3-venv` |
| Skill venv | numpy, pillow, requests | `python3 -m venv ~/.config/meeting-to-video/venv && ~/.config/meeting-to-video/venv/bin/pip install numpy pillow requests` | same |
| Node.js 22+ | HyperFrames (motion graphics renderer, runs via npx, no global install) | `brew install node` | NodeSource / `nvm install 22` |
| puppeteer-core (in the skill's own folder) | layout_audit.py measures the real overlay layout | `mkdir -p ~/.config/meeting-to-video/node && cd ~/.config/meeting-to-video/node && npm init -y && PUPPETEER_SKIP_DOWNLOAD=1 npm i puppeteer-core@23` | same |
| HyperFrames headless Chrome | renders the overlay (layout_audit reuses it) | downloaded automatically on first `npx --yes hyperframes@0.7.60 render` (~150 MB) | same |
| ElevenLabs API key | transcription (Scribe), sound effects, music | user creates it at elevenlabs.io → Settings → API keys and pastes it | same |

Store the key (never echo it back, never put it in the project folder):
```
mkdir -p ~/.config/meeting-to-video && printf 'ELEVENLABS_API_KEY=%s\n' "<key>" > ~/.config/meeting-to-video/.env && chmod 600 ~/.config/meeting-to-video/.env
```
Validate it: `curl -s -o /dev/null -w '%{http_code}' -H "xi-api-key: <key>" https://api.elevenlabs.io/v1/user` → 200.

If `brew`/`apt` needs a password, give the user the exact command to run themselves and wait.
Windows: use WSL2 (Ubuntu) and follow the Linux column.

Fonts: SF Pro is used through the macOS system font (it can't be bundled); Inter (bundled) is the fallback on Linux.

Optional (not required): the HyperFrames authoring skills (`npx --yes hyperframes@0.7.60 skills`) if you want
HyperFrames' own docs available while customising the overlay.

Machine check: ~15 GB free disk for a 30-minute recording; 8 GB RAM works (renders use one worker, ~2 min per
output minute). Close heavy apps before the overlay render.
