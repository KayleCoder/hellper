#!/bin/bash
cd /Users/zhouzibo/Workspaces/hellper
ocr_one() {
  d="$1"; ep=$(basename "$d")
  out="s2ocr/${ep}.txt"
  [ -s "$out" ] && return
  { echo "# ${ep}"
    ./s1ref/ocrbin 1.0 "$d"/*.jpeg "$d"/*.jpg "$d"/*.png 2>/dev/null | sed 's/^===FILE:.*$/---/'
  } > "$out"
}
export -f ocr_one
ls -d Session2/ep3[3-9][0-9] Session2/ep4[0-1][0-9] 2>/dev/null | xargs -P 6 -I{} bash -c 'ocr_one "$@"' _ {} > s2ocr/rest.log 2>&1
echo "=== REST OCR DONE ===" >> s2ocr/rest.log
