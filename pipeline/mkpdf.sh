#!/bin/bash
cd /Users/zhouzibo/Workspaces/hellper
ls -d Session2/ep* | xargs -P 4 -I{} python3 pipeline/mkpdf.py {} > s2pdf/progress.log 2>&1
echo "=== PDF ALL DONE ===" >> s2pdf/progress.log
