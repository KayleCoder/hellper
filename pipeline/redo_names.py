#!/usr/bin/env python3
"""译名订正后，只重排受影响的页，其余页原样保留。

用法（在仓库根）:
    python3 pipeline/redo_names.py s3/188 s3/189 ...      # 指定工作目录
    python3 pipeline/redo_names.py --map 旧=新 旧=新 -- s3/188 ...

工作方式
--------
1. 对每个工作目录，比较 zh.tsv 与备份 zh.tsv.bak（若 --map 给了替换表，先应用并生成备份）
2. 算出哪些「页」的译文变了
3. 底图优先用该目录自己的 ocr_png/（原始生肉页）；没有就从成品 PDF 抽出对应页
4. 只渲染这些页，再把它们拼回成品 PDF，其余页原样取自旧成品

为什么可以拿成品当底图
----------------------
成品 PDF 的嵌入图像像素与 blocks.json 的坐标系一致（实测六话全部精确匹配）。
在旧中文上重擦重排是安全的——**前提是新译名不比旧的长**，否则擦除框会变大、
可能啃到画面。脚本会检查这一点并在变长时警告。
"""
import argparse, json, os, re, shutil, subprocess, sys
import pymupdf
from PIL import Image

ap = argparse.ArgumentParser()
ap.add_argument('--map', nargs='*', default=[], help='旧=新 替换对')
ap.add_argument('--pdf-dir', default='out', help='成品 PDF 所在目录')
ap.add_argument('--suffix', default='_中文版.pdf')
ap.add_argument('dirs', nargs='+')
a = ap.parse_args()

pairs = []
for m in a.map:
    if '=' not in m: sys.exit(f'--map 格式应为 旧=新，收到 {m!r}')
    pairs.append(tuple(m.split('=', 1)))

for wd in a.dirs:
    ep = os.path.basename(wd.rstrip('/'))
    tsv, bak = f'{wd}/zh.tsv', f'{wd}/zh.tsv.bak'
    if pairs:
        shutil.copy(tsv, bak)
        s = open(tsv, encoding='utf-8').read()
        n = 0
        for o, w in pairs:
            n += s.count(o); s = s.replace(o, w)
        open(tsv, 'w', encoding='utf-8').write(s)
        print(f'[{ep}] 替换 {n} 处')
    if not os.path.exists(bak):
        print(f'[{ep}] 没有 zh.tsv.bak，跳过'); continue

    old = dict(l.rstrip('\n').split('\t', 1) for l in open(bak, encoding='utf-8') if '\t' in l)
    new = dict(l.rstrip('\n').split('\t', 1) for l in open(tsv, encoding='utf-8') if '\t' in l)
    changed = [k for k in new if old.get(k) != new[k]]
    if not changed:
        print(f'[{ep}] 无改动'); continue
    grew = [k for k in changed if len(new[k]) > len(old.get(k, ''))]
    if grew:
        print(f'[{ep}] ⚠ 这些块的新译文更长，擦除框会变大，渲染后请人眼复核: {grew}')
    pages = sorted({k.rsplit('.', 1)[0] for k in changed})
    print(f'[{ep}] {len(changed)} 块 / {len(pages)} 页: {" ".join(pages)}')

    pdf = f'{a.pdf_dir}/{ep}{a.suffix}'
    native = os.path.isdir(f'{wd}/ocr_png') and os.listdir(f'{wd}/ocr_png')
    tmp = False
    if not native:
        os.makedirs(f'{wd}/ocr_png', exist_ok=True); tmp = True
        d = pymupdf.open(pdf)
        for p in pages:
            d[int(p)].get_pixmap(matrix=pymupdf.Matrix(1, 1)).save(f'{wd}/ocr_png/{p}.png')
        d.close()
        print(f'       底图：从 {pdf} 抽出 {len(pages)} 页')

    src = open(f'{wd}/render_zh.py', encoding='utf-8').read()
    src = src.replace("    im = Image.open(f'ocr_png/{pg}.png').convert('RGB')",
                      "    if not os.path.exists(f'ocr_png/{pg}.png'): continue\n"
                      "    im = Image.open(f'ocr_png/{pg}.png').convert('RGB')", 1)
    open(f'{wd}/_redo.py', 'w', encoding='utf-8').write(src)
    shutil.rmtree(f'{wd}/out_png', ignore_errors=True)
    r = subprocess.run([sys.executable, '_redo.py'], cwd=wd, capture_output=True, text=True)
    if r.returncode:
        print('       !! 渲染失败:', r.stderr.strip()[-300:]); continue
    print('       render:', (r.stdout.strip().splitlines() or ['?'])[0])

    doc = pymupdf.open(pdf); imgs = []
    for i in range(doc.page_count):
        t = f'{i:03d}'
        f = f'{wd}/out_png/{t}.png'
        if t in pages and os.path.exists(f):
            imgs.append(Image.open(f).convert('RGB'))
        else:
            pm = doc[i].get_pixmap(matrix=pymupdf.Matrix(1, 1))
            imgs.append(Image.frombytes('RGB', (pm.width, pm.height), pm.samples))
    doc.close()
    imgs[0].save(pdf, save_all=True, append_images=imgs[1:], resolution=150.0)
    for im in imgs[1:]: im.close()
    print(f'       → {pdf}  {len(imgs)} 页  {os.path.getsize(pdf)/1048576:.1f} MB')
    os.remove(f'{wd}/_redo.py')
    if tmp: shutil.rmtree(f'{wd}/ocr_png', ignore_errors=True)
print('完成')
