"""全书缩略图扫视。在某话目录下运行: python3 sweep.py [每行页数]"""
import os, sys
from PIL import Image, ImageDraw, ImageFont
F = ImageFont.truetype("/System/Library/Fonts/Hiragino Sans GB.ttc", 14, index=1)
fns = sorted(os.listdir('out_png'))
cols = int(sys.argv[1]) if len(sys.argv) > 1 else 20
tw, th = 104, 225
rows = (len(fns) + cols - 1) // cols
s = Image.new('RGB', (cols * (tw + 4), rows * (th + 18)), (210, 210, 218))
d = ImageDraw.Draw(s)
for j, fn in enumerate(fns):
    im = Image.open('out_png/' + fn).convert('RGB').resize((tw, th), Image.LANCZOS)
    r, q = divmod(j, cols); X, Y = q * (tw + 4) + 2, r * (th + 18) + 2
    d.text((X, Y), fn[:3], font=F, fill=(120, 0, 0)); s.paste(im, (X, Y + 16))
s.save('sweep.png'); print('sweep.png', s.size, len(fns), '页')
