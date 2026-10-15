#!/bin/bash
# Checks everything meeting-to-video needs. Prints OK / MISSING with the fix. Exit 1 if anything is missing.
miss=0
ok()  { printf "  OK       %s\n" "$1"; }
bad() { printf "  MISSING  %s\n           fix: %s\n" "$1" "$2"; miss=1; }
OS=$(uname -s)
inst() { if [ "$OS" = "Darwin" ]; then echo "brew install $1"; else echo "sudo apt-get install -y $2"; fi; }

echo "meeting-to-video doctor"
command -v ffmpeg >/dev/null && command -v ffprobe >/dev/null && ok "ffmpeg $(ffmpeg -version | head -1 | awk '{print $3}')" || bad "ffmpeg/ffprobe" "$(inst ffmpeg ffmpeg)"
if command -v ffmpeg >/dev/null; then
  ffmpeg -hide_banner -decoders 2>/dev/null | grep -q libvpx-vp9 && ok "ffmpeg libvpx-vp9 (reads the transparent overlay)" || bad "ffmpeg built without libvpx-vp9" "reinstall ffmpeg with libvpx (brew's default build has it)"
fi
PYV=$(python3 -c 'import sys;print("%d.%d"%sys.version_info[:2])' 2>/dev/null)
python3 -c 'import sys;sys.exit(0 if sys.version_info>=(3,10) else 1)' 2>/dev/null && ok "python $PYV" || bad "python 3.10+" "$(inst python python3)"
VENV=~/.config/meeting-to-video/venv
if [ -x "$VENV/bin/python" ] && "$VENV/bin/python" -c "import numpy, PIL, requests" 2>/dev/null; then ok "skill venv (numpy, pillow, requests)"
else bad "skill venv" "python3 -m venv $VENV && $VENV/bin/pip install numpy pillow requests"; fi
NV=$(node -v 2>/dev/null | tr -d v | cut -d. -f1)
[ -n "$NV" ] && [ "$NV" -ge 22 ] && ok "node $(node -v)" || bad "node 22+ (found: ${NV:-none})" "$( [ "$OS" = Darwin ] && echo 'brew install node' || echo 'nvm install 22')"
command -v npx >/dev/null && ok "npx (HyperFrames runs through npx; Chrome downloads on first render)" || bad "npx" "comes with node"
KEYF=~/.config/meeting-to-video/.env
if [ -n "$ELEVENLABS_API_KEY" ] || grep -q '^ELEVENLABS_API_KEY=..' "$KEYF" 2>/dev/null; then ok "ElevenLabs key"
else bad "ElevenLabs API key" "user creates one at elevenlabs.io (Settings > API keys); store it as in setup/SETUP.md"; fi
FREE=$(df -Pk ~ | awk 'NR==2{print int($4/1048576)}')
[ "$FREE" -ge 15 ] && ok "disk ${FREE} GB free" || bad "disk: only ${FREE} GB free" "free up space (need ~15 GB for a 30-min recording)"
if [ "$OS" = "Darwin" ]; then RAM=$(( $(sysctl -n hw.memsize) / 1073741824 )); else RAM=$(( $(grep MemTotal /proc/meminfo | awk '{print $2}') / 1048576 )); fi
echo "  INFO     RAM ${RAM} GB  (8 GB works: overlay renders at ~2 min per output minute)"
[ $miss = 0 ] && echo "all good" || echo "fix the MISSING items (see setup/SETUP.md), then re-run"
exit $miss
