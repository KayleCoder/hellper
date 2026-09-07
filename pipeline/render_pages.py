import pymupdf, os, io
from PIL import Image
SRC='/Users/zhouzibo/Desktop/191.pdf'
d=pymupdf.open(SRC)
# union of content bounds across every page (pages vary in height, and margins vary)
lo,hi=1.0,0.0
for i in range(d.page_count):
    pm=d[i].get_pixmap(matrix=pymupdf.Matrix(0.2,0.2))
    im=Image.open(io.BytesIO(pm.tobytes('png'))).convert('L')
    W,H=im.size; px=im.load(); cols=[]
    for x in range(W):
        for y in range(0,H,3):
            if px[x,y]<245: cols.append(x); break
    if cols: lo=min(lo,min(cols)/W); hi=max(hi,(max(cols)+1)/W)
print('内容横向范围 比例',round(lo,3),round(hi,3))
x0=max(0,int(lo*1170)-8); x1=min(1170,int(hi*1170)+8)
print('裁剪 x',x0,x1)
os.makedirs('ocr_png',exist_ok=True)
for i in range(d.page_count):
    r=d[i].rect
    pm=d[i].get_pixmap(matrix=pymupdf.Matrix(1,1), clip=pymupdf.Rect(x0,0,min(x1,r.width),r.height))
    pm.save(f'ocr_png/{i:03d}.png')
print('已渲染',d.page_count,'页, 宽',x1-x0)
