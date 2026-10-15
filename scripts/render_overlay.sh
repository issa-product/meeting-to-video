#!/bin/bash
# render_overlay.sh <edit_dir> [--test SECONDS | --tail FROM_SECONDS]
#   (default)  full transparent overlay -> <edit_dir>/overlay.webm
#   --test 30  render only the first 30s in a scratch copy (cards + layout sanity in a REAL render)
#   --tail 800 render FROM..end and append to overlay.webm (recovers a short render without redoing it)
set -e
ED=$(cd "$1" && pwd); MODE=$2; ARG=$3
HF="npx --yes hyperframes@0.7.60"
FLAGS="--format webm --fps 30 --quality standard --protocol-timeout 1800000 --browser-timeout 180 --player-ready-timeout 120000 --quiet"
TOTAL=$(python3 -c "import json;print(json.loads(open('$ED/mg/data.js').read()[14:-2])['total'])")
if [ -z "$MODE" ]; then
  cd "$ED/mg" && $HF render . $FLAGS -o "$ED/overlay.webm" >/dev/null 2>&1
  echo "overlay -> $ED/overlay.webm"; exit 0
fi
TMP=$(mktemp -d); cp -R "$ED/mg/." "$TMP/"
if [ "$MODE" = "--test" ]; then
  python3 - "$TMP/index.html" "$ARG" <<'PY'
import re,sys
p,d=sys.argv[1],sys.argv[2]; s=open(p).read()
open(p,'w').write(re.sub(r'(id="root"[^>]*?data-duration=")[\d.]+(")', rf'\g<1>{d}\g<2>', s))
PY
  (cd "$TMP" && $HF render . $FLAGS -o "$ED/overlay_test.webm" >/dev/null 2>&1)
  echo "test overlay (${ARG}s) -> $ED/overlay_test.webm"
elif [ "$MODE" = "--tail" ]; then
  LEN=$(python3 -c "print(round($TOTAL-$ARG,3))")
  python3 - "$TMP/index.html" "$LEN" "$ARG" <<'PY'
import re,sys
p,length,frm=sys.argv[1],sys.argv[2],sys.argv[3]; s=open(p).read()
s=re.sub(r'(id="root"[^>]*?data-duration=")[\d.]+(")', rf'\g<1>{length}\g<2>', s)
# the renderer drives `outer`, which scrubs the real timeline from FROM to the end
s=s.replace('/* @@TAIL@@ */', 'const outer = gsap.timeline({ paused: true }); outer.add(tl.tweenFromTo(%s, D.total, { ease: "none" }), 0); window.__timelines["main"] = outer;' % frm)
open(p,'w').write(s)
PY
  (cd "$TMP" && $HF render . $FLAGS -o "$TMP/tail.webm" >/dev/null 2>&1)
  OVD=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$ED/overlay.webm")
  if python3 -c "import sys;sys.exit(0 if abs($OVD-$ARG)<0.05 else 1)"; then
    # usual case: the short render ended exactly at FROM -> lossless join
    printf "file '%s'\nfile '%s'\n" "$ED/overlay.webm" "$TMP/tail.webm" > "$TMP/list.txt"
    ffmpeg -v error -y -f concat -safe 0 -i "$TMP/list.txt" -c copy "$ED/overlay_full.webm"
  else
    ffmpeg -v error -y -c:v libvpx-vp9 -i "$ED/overlay.webm" -c:v libvpx-vp9 -i "$TMP/tail.webm" -filter_complex \
      "[0:v]trim=duration=$ARG,setpts=PTS-STARTPTS[a];[1:v]setpts=PTS-STARTPTS[b];[a][b]concat=n=2:v=1[o]" -map "[o]" \
      -c:v libvpx-vp9 -pix_fmt yuva420p -b:v 0 -crf 30 -deadline good -cpu-used 4 "$ED/overlay_full.webm"
  fi
  mv "$ED/overlay_full.webm" "$ED/overlay.webm"; echo "overlay with tail -> $ED/overlay.webm"
fi
