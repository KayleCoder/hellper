# 用法: python3 sheet.py 输出.png 块编号 [块编号...]
# 或   python3 sheet.py 输出.png --page 页号 [页号...]
import json, sys
from PIL import Image, ImageDraw, ImageFont
F=ImageFont.truetype("/System/Library/Fonts/Hiragino Sans GB.ttc", 20, index=1)
B={p['page']:p for p in json.load(open('blocks.json'))}
out=sys.argv[1]; args=sys.argv[2:]
tiles=[]
if args and args[0]=='--page':
    for pg in args[1:]:
        im=Image.open(f'ocr_png/{pg}.png').convert('RGB')
        sc=min(1.0, 300/im.width, 900/im.height)
        tiles.append((pg, '', im.resize((int(im.width*sc),int(im.height*sc)), Image.LANCZOS)))
else:
    for k in args:
        pg,i=k.split('.'); b=B[pg]['blocks'][int(i)]
        im=Image.open(f'ocr_png/{pg}.png').convert('RGB'); pad=34
        box=(max(0,b['x']-pad),max(0,b['y']-pad),min(im.width,b['x1']+pad),min(im.height,b['y1']+pad))
        c=im.crop(box); sc=min(2.4, 640/max(1,c.width), 500/max(1,c.height))
        tiles.append((k, b['ko'][:40], c.resize((max(1,int(c.width*sc)),max(1,int(c.height*sc))), Image.LANCZOS)))
W=max(t[2].width for t in tiles)+16
H=sum(t[2].height+38 for t in tiles)+16
s=Image.new('RGB',(W,H),(238,238,242)); d=ImageDraw.Draw(s); y=8
for k,ko,c in tiles:
    d.text((8,y+6), f'{k}  |  {ko}', font=F, fill=(150,0,0)); y+=34
    s.paste(c,(8,y)); d.rectangle((8,y,8+c.width,y+c.height),outline=(0,0,0)); y+=c.height+4
s.save(out); print(out, s.size)
