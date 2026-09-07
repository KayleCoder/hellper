#!/usr/bin/env python3
"""排版体检：模拟 render_zh.py 的真实折行，找出孤字行和被拆散的标点。

用法（在某话工作目录下）: python3 ../../pipeline/check_wrap.py
读 blocks.json / zh.tsv / render_zh.py（取 FONT_MAX 与 EXTRA）。
"""
import json, re, sys, os
from PIL import Image, ImageDraw, ImageFont

src = open('render_zh.py', encoding='utf-8').read()
ns = {}
exec(re.search(r"(NO_START.*?)\nblocks =", src, re.S).group(1), ns)
exec(re.search(r"(def tokenize.*?)\ndef ", src, re.S).group(1), ns)
exec(re.search(r"(def wrap.*?)\n\ndef ", src, re.S).group(1), ns)
wrap = ns['wrap']
FONT_MAX = eval(re.search(r"FONT_MAX = (\{.*?\n\})", src, re.S).group(1))
EXTRA = eval(re.search(r"EXTRA = (\{.*?\n\})", src, re.S).group(1))
FONT = re.search(r'FONT = "(.*?)"', src).group(1)
FIDX = int(re.search(r'FIDX = (\d+)', src).group(1))

blk = {p['page']: p['blocks'] for p in json.load(open('blocks.json'))}
for pg, items in EXTRA.items():
    blk.setdefault(pg, [])
    for rect, ko in items:
        blk[pg].append({'x': rect[0], 'y': rect[1], 'x1': rect[2], 'y1': rect[3],
                        'nlines': 1, 'ko': ko})
zh = {}
for ln in open('zh.tsv', encoding='utf-8'):
    if '\t' in ln:
        k, v = ln.rstrip('\n').split('\t', 1)
        zh[k] = v.replace('|', '\n')

d = ImageDraw.Draw(Image.new('RGB', (10, 10)))
fc = {}
def font(s):
    if s not in fc: fc[s] = ImageFont.truetype(FONT, s, index=FIDX)
    return fc[s]

LONELY = set('，。、！？；：）」』】…~—-!?,.:;)（「『【(《》')
bad = []
for pg in sorted(blk):
    for i, b in enumerate(blk[pg]):
        k = f'{pg}.{i}'
        if k not in zh: continue
        text = zh[k]
        bw, bh = b['x1'] - b['x'], b['y1'] - b['y']
        nl = max(1, b.get('nlines', 1))
        aw = max(40, int(bw * 1.04)); ah = max(24, int(bh * 1.32))
        start = max(11, min(int(bh / nl * 0.92), FONT_MAX.get(k, 60)))
        ch = None
        for sz in range(start, 8, -1):
            f = font(sz); lh = int(sz * 1.28); ls = wrap(text, f, aw, d)
            if len(ls) * lh <= ah and max(d.textlength(l, font=f) for l in ls) <= aw:
                ch = (sz, ls); break
        if ch is None:
            ch = (9, wrap(text, font(9), aw, d))
        sz, ls = ch
        why = []
        for l in ls:
            s = l.strip()
            if len(s) == 1 and s not in '?!。':
                why.append(f'孤字「{s}」')
            elif s and all(c in LONELY for c in s):
                why.append(f'孤立标点「{s}」')
        if sz <= 12: why.append(f'字号被压到 {sz}px')
        if why:
            bad.append((k, sz, ls, why))

print(f'排版问题: {len(bad)} 条')
for k, sz, ls, why in bad:
    print(f"  {k}  字号{sz}  {' / '.join(ls)}   ← {'、'.join(why)}")
sys.exit(1 if bad else 0)
