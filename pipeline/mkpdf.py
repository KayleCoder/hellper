import os, sys
from PIL import Image
d = sys.argv[1]
ep = os.path.basename(d).replace('ep','')
out = f's2pdf/{ep}.pdf'
if os.path.exists(out) and os.path.getsize(out) > 10000:
    print(f'skip {ep}'); sys.exit()
fs = sorted(f for f in os.listdir(d) if f.lower().endswith(('.jpg','.png')))
if not fs:
    print(f'empty {ep}'); sys.exit()
ims = []
try:
    first = Image.open(os.path.join(d, fs[0])).convert('RGB')
    for f in fs[1:]:
        ims.append(Image.open(os.path.join(d, f)).convert('RGB'))
    first.save(out, save_all=True, append_images=ims, resolution=150.0)
    print(f'ok {ep} {len(fs)}p')
finally:
    for im in ims: im.close()
