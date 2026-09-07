import os, sys
from PIL import Image
ep = sys.argv[1]                      # 形如 ep050
n  = int(ep[2:])                      # 50
out = f'上传/第一季/{n-1:03d}.pdf'      # ep001=預告→000，ep002=第1話→001
if os.path.exists(out) and os.path.getsize(out) > 10000:
    print(f'skip {out}'); sys.exit()
d = f's1ref/img/{ep}'
fs = sorted(f for f in os.listdir(d) if f.lower().endswith(('.jpg','.jpeg','.png')))
if not fs:
    print(f'empty {ep}'); sys.exit()
ims = []
try:
    first = Image.open(os.path.join(d, fs[0])).convert('RGB')
    for f in fs[1:]:
        ims.append(Image.open(os.path.join(d, f)).convert('RGB'))
    first.save(out, save_all=True, append_images=ims, resolution=150.0)
    print(f'ok {out} {len(fs)}p')
finally:
    for im in ims: im.close()
