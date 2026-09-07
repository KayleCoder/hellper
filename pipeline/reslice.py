#!/usr/bin/env python3
"""超长条重切成页：拼接 → 在「横向空白带」处切 → 逐页输出。

用法: python3 pipeline/reslice.py <源目录> <输出目录> [目标页高] [跳过的文件...]

汉化组的长图常常一张就上万像素，流水线按页处理吃不下。本工具找整行都
接近纯色（白或黑）的「装订线」作为切点，避免从画面或对白中间切断。
"""
import os, sys
import numpy as np
from PIL import Image

src, out = sys.argv[1], sys.argv[2]
TARGET = int(sys.argv[3]) if len(sys.argv) > 3 else 2400
skip = set(sys.argv[4:])

fs = [f for f in sorted(os.listdir(src))
      if f.lower().endswith(('.png', '.jpg', '.jpeg')) and f not in skip]
parts = []
W = None
for f in fs:
    im = Image.open(os.path.join(src, f)).convert('RGB')
    if W is None: W = im.size[0]
    if im.size[0] != W:
        print(f'  跳过宽度不符的 {f} ({im.size[0]}px, 期望 {W})'); continue
    parts.append(np.asarray(im))
strip = np.vstack(parts)
H = strip.shape[0]
print(f'拼接后 {W}x{H}px，来自 {len(parts)} 张')

# 逐行判定是否为「装订线」：整行极差小且接近纯色
g = strip.mean(axis=2)
rowmin = g.min(axis=1); rowmax = g.max(axis=1)
flat = (rowmax - rowmin) < 12
gutter = flat & ((g.mean(axis=1) > 236) | (g.mean(axis=1) < 20))
print(f'可切行 {int(gutter.sum())} / {H}')

cuts = [0]
while cuts[-1] + TARGET < H:
    lo = cuts[-1] + int(TARGET * 0.55)
    hi = min(H - 1, cuts[-1] + int(TARGET * 1.45))
    cand = [y for y in range(lo, hi) if gutter[y]]
    if cand:
        # 取最接近目标高度的切点
        cuts.append(min(cand, key=lambda y: abs(y - (cuts[-1] + TARGET))))
    else:
        cuts.append(min(H - 1, cuts[-1] + TARGET))   # 找不到就硬切
        print(f'  ! {cuts[-1]} 处无空白带，硬切')
cuts.append(H)

os.makedirs(out, exist_ok=True)
for i in range(len(cuts) - 1):
    Image.fromarray(strip[cuts[i]:cuts[i+1]]).save(f'{out}/{i:03d}.png')
hs = [cuts[i+1]-cuts[i] for i in range(len(cuts)-1)]
print(f'切成 {len(hs)} 页，高度 {min(hs)}~{max(hs)}px（中位 {sorted(hs)[len(hs)//2]}）')
