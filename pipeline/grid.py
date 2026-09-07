"""带坐标网格的裁切图，用来手工量准擦除框。
用法: python3 grid.py 输出.png 页号 x0 y0 x1 y1 [步长]"""
import sys
from PIL import Image, ImageDraw, ImageFont
out, pg, x0, y0, x1, y1 = sys.argv[1], sys.argv[2], *map(int, sys.argv[3:7])
step = int(sys.argv[7]) if len(sys.argv) > 7 else 100
im = Image.open(f'ocr_png/{pg}.png').convert('RGB').crop((x0, y0, x1, y1))
sc = min(3.0, 1100 / im.width)
im = im.resize((int(im.width * sc), int(im.height * sc)), Image.LANCZOS)
d = ImageDraw.Draw(im)
F = ImageFont.truetype("/System/Library/Fonts/Menlo.ttc", 15)
for gx in range(x0 - x0 % step + step, x1, step):
    X = int((gx - x0) * sc)
    d.line([(X, 0), (X, im.height)], fill=(255, 0, 0), width=1)
    d.text((X + 2, 2), str(gx), font=F, fill=(200, 0, 0))
for gy in range(y0 - y0 % step + step, y1, step):
    Y = int((gy - y0) * sc)
    d.line([(0, Y), (im.width, Y)], fill=(0, 120, 255), width=1)
    d.text((2, Y + 2), str(gy), font=F, fill=(0, 90, 200))
im.save(out); print(out, im.size, f'scale={sc:.2f}')
