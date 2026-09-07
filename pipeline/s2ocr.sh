#!/bin/bash
cd /Users/zhouzibo/Workspaces/hellper
ocr_one() {
  d="$1"; ep=$(basename "$d")
  out="s2ocr/${ep}.txt"
  [ -s "$out" ] && return
  { echo "# ${ep}"
    ./s1ref/ocrbin 1.0 "$d"/*.jpg 2>/dev/null | sed 's/^===FILE:.*$/---/'
  } > "$out"
  echo "done $ep"
}
export -f ocr_one
ls -d Session2/ep* | xargs -P 6 -I{} bash -c 'ocr_one "$@"' _ {} > s2ocr/progress.log 2>&1
echo "=== ALL DONE ===" >> s2ocr/progress.log
