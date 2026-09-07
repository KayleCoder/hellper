"""求气泡白色内腔的安全擦除框（避开彩色轮廓/锯齿）。
用法: python3 safebox.py 页号 y0 y1 中心y [中心x]
输出可直接填进 ERASE_OVERRIDE / EXTRA 的矩形。"""
import sys
from PIL import Image
pg, y0, y1, cy = sys.argv[1], *map(int, sys.argv[2:5])
cx = int(sys.argv[5]) if len(sys.argv) > 5 else None
im = Image.open(f'ocr_png/{pg}.png').convert('RGB'); px = im.load(); W, H = im.size
if cx is None: cx = W // 2
def sat(p): return max(p) - min(p) > 24
L, R = [], []
for y in range(y0, y1):
    if sat(px[cx, y]): continue
    l = cx
    while l > 60 and not sat(px[l, y]): l -= 1
    r = cx
    while r < W - 60 and not sat(px[r, y]): r += 1
    L.append(l + 1); R.append(r - 1)
x0, x1 = max(L), min(R)
T, B = [], []
for x in range(x0 + 10, x1 - 10, 3):
    if sat(px[x, cy]): continue
    t = cy
    while t > 60 and not sat(px[x, t]): t -= 1
    b = cy
    while b < H - 60 and not sat(px[x, b]): b += 1
    T.append(t + 1); B.append(b - 1)
print(f'安全框 = ({x0+4}, {max(T)+4}, {x1-4}, {min(B)-4})')
