#!/usr/bin/env python3
"""Naver 原图 (690px 宽) -> ocr_png/ (1170px 宽)，供 ocrtool2 / cluster.py 使用。

用法（在工作目录下）:  python3 ../../pipeline/prep_from_jpg.py ../ep007

放大到 1170px 是为了对齐 188~193 的工作分辨率——CLAUDE.md 里的
FONT_MAX、pad、巨型拟声字面积阈值都是按那个尺度定的。
"""
import os, sys
from PIL import Image

TARGET_W = 1170
src = sys.argv[1]
out = 'ocr_png'
os.makedirs(out, exist_ok=True)

fs = sorted(f for f in os.listdir(src) if f.lower().endswith(('.jpg', '.png')))
scale = None
for i, f in enumerate(fs):
    im = Image.open(os.path.join(src, f)).convert('RGB')
    w, h = im.size
    if scale is None:
        scale = TARGET_W / w
        print(f'原始宽 {w}px → {TARGET_W}px  (x{scale:.4f})')
    nh = max(1, round(h * scale))
    im.resize((TARGET_W, nh), Image.LANCZOS).save(f'{out}/{i:03d}.png')
    im.close()
print(f'已生成 {len(fs)} 页 → {out}/')
