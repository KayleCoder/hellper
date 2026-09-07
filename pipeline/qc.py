"""质检：残留韩文（含 2x 重 OCR）+ 画面墨迹流失。在某话目录下运行。"""
import json, os, re, subprocess, sys
from PIL import Image, ImageDraw

hang = re.compile(r'[가-힣]')
E = json.load(open('erase.json'))
B = {p['page']: p for p in json.load(open('blocks.json'))}
zh = set(l.split('\t', 1)[0] for l in open('zh.tsv', encoding='utf-8') if '\t' in l)
skip = {pg: [(b['x'], b['y'], b['x1'], b['y1'])
             for i, b in enumerate(p['blocks']) if f"{pg}.{i}" not in zh]
        for pg, p in B.items()}
def ov(a, b): return not (a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1])

os.makedirs('residual', exist_ok=True); os.makedirs('res2x', exist_ok=True)
for fn in sorted(os.listdir('ocr_png')):
    im = Image.open('ocr_png/' + fn).convert('RGB'); d = ImageDraw.Draw(im)
    for r in E.get(fn[:3], []): d.rectangle(r, fill=(255, 255, 255))
    im.save('residual/' + fn)
    im.resize((im.width * 2, im.height * 2), Image.LANCZOS).save('res2x/' + fn)

def scan(tsv, div, minhang):
    cur = None; bad = []
    for ln in open(tsv, encoding='utf-8'):
        ln = ln.rstrip('\n')
        if ln.startswith('FILE\t'): cur = ln.split('\t')[1][:3]
        elif ln.startswith('L\t'):
            p = ln.split('\t', 6); t = p[6]
            if len(hang.findall(t)) < minhang: continue
            r = (int(p[1])//div, int(p[2])//div,
                 (int(p[1])+int(p[3]))//div, (int(p[2])+int(p[4]))//div)
            if any(ov(r, s) for s in skip.get(cur, [])): continue
            bad.append((cur, t))
    return bad

subprocess.run('./ocrtool2 residual/*.png > residual.tsv 2>/dev/null', shell=True)
subprocess.run('./ocrtool2 res2x/*.png > res2x.tsv 2>/dev/null', shell=True)
b1 = scan('residual.tsv', 1, 2)
b2 = scan('res2x.tsv', 2, 1)
print(f'未预期韩文残留  1x: {len(b1)} 处   {b1 if b1 else ""}')
print(f'未预期韩文残留  2x: {len(b2)} 处')
for c, t in b2: print(f'    {c}.png  {t}')

rows = []
for fn in sorted(os.listdir('ocr_png')):
    a = Image.open('ocr_png/' + fn).convert('L').resize((94, 253))
    b = Image.open('out_png/' + fn).convert('L').resize((94, 253))
    ia = sum(1 for p in a.get_flattened_data() if p < 235)
    ib = sum(1 for p in b.get_flattened_data() if p < 235)
    if ia > 200: rows.append(((ia - ib) / ia, fn))
rows.sort(reverse=True)
print('\n墨迹流失最高的 6 页:')
for l, fn in rows[:6]:
    print(f'    {fn}  {l*100:5.1f}%' + ('   <<< 需人眼复核' if l > 0.12 else ''))
