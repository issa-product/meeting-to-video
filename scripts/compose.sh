#!/bin/bash
# compose.sh <edit_dir> <base.mp4> <out.mp4> [audio.wav]
# base video + transparent overlay + audio master. Both videos are re-timed by frame index (N/30) so concat
# timestamp jitter can never drift them apart. PRESET/CRF env vars: veryfast/22 for previews, medium/18 final.
set -e
ED=$(cd "$1" && pwd); BASE=$2; OUT=$3; AUD=${4:-$ED/audio/dialogue.wav}
H=$(ffprobe -v error -select_streams v -show_entries stream=height -of csv=p=0 "$BASE")
ffmpeg -v error -y -i "$BASE" -c:v libvpx-vp9 -i "${OVERLAY:-$ED/overlay.webm}" -i "$AUD" -filter_complex "
[0:v]setpts=N/30/TB[b];
[1:v]setpts=N/30/TB,format=rgba,scale=-2:$H:flags=lanczos[o];
[b][o]overlay=0:0:format=auto:eof_action=pass,format=yuv420p[v]" \
  -map "[v]" -map 2:a -c:v libx264 -preset ${PRESET:-medium} -crf ${CRF:-18} -r 30 -c:a aac -b:a 192k -ar 48000 \
  -shortest -movflags +faststart "$OUT"
echo "$OUT  $(ffprobe -v error -show_entries format=duration -of csv=p=0 "$OUT")s"
