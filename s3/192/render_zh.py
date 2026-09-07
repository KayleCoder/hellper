# -*- coding: utf-8 -*-
import json, os, re, statistics
from PIL import Image, ImageDraw, ImageFont

FONT = "/System/Library/Fonts/Hiragino Sans GB.ttc"
FIDX = 1  # W6
NO_START = set("，。、！？；：）」』】…~-!?,.:;)·・")
NO_END   = set("（「『【(")

blocks = {p['page']: p for p in json.load(open('blocks.json'))}
# blocks whose OCR bbox under-covers the real text (tilted / stylised lettering).
# value = explicit erase rect in page coords, verified by eye to sit inside the bubble.
ERASE_OVERRIDE = {
    # OCR 框没盖住整个标签
    '040.7': [(240, 2230, 532, 2394)],   # 「72체 변신술」框小了一圈
    '085.0': [(580, 764, 866, 1006)],    # 漏掉了「41장」那一行
    # EXTRA 块默认会加 24px 边距，会吃掉左侧画格边框；用 override 精确指定
    '016.0': [(35, 240, 520, 1668)],
    # 尖角气泡：擦除框必须留在白色内腔里，否则会吃掉气泡轮廓
    '003.1': [(291, 1529, 812, 1797)],
    '003.2': [(277, 2043, 846, 2361)],
}
MASK_ERASE = set()
erase_log = {}
FONT_MAX = {
    '005.0': 150, '009.0': 110, '009.1': 140, '012.0': 190,
    '019.1': 96,  '019.2': 190, '031.0': 150, '038.0': 112,
    '040.7': 76,  '042.0': 84,  '050.0': 56,  '052.0': 120,
    '067.0': 100, '071.0': 58,  '072.2': 110, '074.0': 80,
    '079.0': 108, '082.1': 96,  '003.1': 130, '003.2': 130,
    '069.1': 64,  '069.3': 64,  '070.1': 64,  '071.2': 60,
    '076.2': 68,  '084.1': 66,  '085.0': 62,  '086.0': 66,
    '051.0': 48, '040.8': 108, '005.1': 110, '016.0': 118, '054.4': 110, '054.5': 120,  '053.4': 100, '025.0': 70,  '063.0': 62,
}
# 把对白气泡和满格特效字聚在一起的块，手工拆开
EXTRA = {
    '003': [((291, 1529, 812, 1797), '거룩하시다!'),
            ((277, 2043, 846, 2361), '거룩하시다!!')],
    '019': [((236, 1289, 902, 1452), '바베큐 파티!'),
            ((177, 1789, 910, 2530), '천벌 「뢰우」')],
    '031': [((242, 1904, 480, 2151), '클클클.. 가차 없군..')],
    '053': [((398, 34,  668, 127),  '자알~~'),
            ((409, 2061, 857, 2385), '워배트 「여의」'),
            ((556, 2407, 770, 2501), '우리가,')],
    '069': [((595, 1398, 951, 1931), '하르방이랑 현우는 아직 그러고 있어?!?'),
            ((735, 2035, 895, 2205), '쿵.. 응..')],
    # 1x OCR 完全没读到的描边艺术字对白（2x 重 OCR 挖出）
    '040': [((192, 925, 478, 1302), '빨리 샹!!')],
    '005': [((315, 520, 520, 700), '거,')],
    # 全书缩略图扫视才发现的漏译：1x/2x OCR 都没读出的描边艺术字
    '016': [((35, 240, 520, 1668), '전군, 공격―')],
    '054': [((300, 145, 800, 440),  '먹겠습니다~!!!'),
            ((230, 2050, 870, 2325), '정의다!!!')],
}
zh = {}
for ln in open('zh.tsv', encoding='utf-8'):
    ln = ln.rstrip('\n')
    if '\t' not in ln: continue
    k, v = ln.split('\t', 1)
    zh[k] = v.replace('|', '\n')

os.makedirs('out_png', exist_ok=True)
fcache = {}
def font(sz):
    if sz not in fcache:
        fcache[sz] = ImageFont.truetype(FONT, sz, index=FIDX)
    return fcache[sz]

def tokenize(text):
    # keep runs of latin letters/digits atomic so words never break mid-word
    out, buf = [], ''
    for ch in text:
        if (ch.isascii() and (ch.isalnum() or ch == "'")):
            buf += ch
        else:
            if buf: out.append(buf); buf = ''
            out.append(ch)
    if buf: out.append(buf)
    return out

def wrap(text, f, maxw, draw):
    lines, cur = [], ''
    for ch in tokenize(text):
        if ch == '\n':
            lines.append(cur); cur = ''; continue
        t = cur + ch
        if draw.textlength(t, font=f) > maxw and cur:
            # punctuation hang: don't start a line with these
            if ch in NO_START:
                cur = t; continue
            if cur and cur[-1] in NO_END:
                lines.append(cur[:-1]); cur = cur[-1] + ch; continue
            lines.append(cur); cur = ch
        else:
            cur = t
    if cur: lines.append(cur)
    return lines

def paper_colour(im, rects):
    """Median of the bright near-greyscale pixels: the bubble's paper tone, unaffected
    by any coloured artwork that happens to fall inside the rect."""
    px = im.load(); W, H = im.size; s = []
    for x0, y0, x1, y1 in rects:
        for x in range(max(0, x0), min(W, x1), 2):
            for y in range(max(0, y0), min(H, y1), 2):
                p = px[x, y]
                if max(p) - min(p) < 46 and min(p) > 200: s.append(p)
    if not s: return (255, 255, 255)
    return tuple(int(statistics.median([c[i] for c in s])) for i in range(3))

def mask_erase(im, rect, fill):
    """Repaint only the near-greyscale pixels in `rect` (paper and lettering),
    leaving coloured artwork untouched -- for text sitting in an irregular bubble."""
    x0, y0, x1, y1 = rect
    px = im.load(); W, H = im.size
    for x in range(max(0, x0), min(W, x1)):
        for y in range(max(0, y0), min(H, y1)):
            r, g, b = px[x, y]
            if max(r, g, b) - min(r, g, b) < 46:
                px[x, y] = fill

def bg_inside(im, box):
    """median of the pixels INSIDE an override rect: the rect is measured to sit in a
    uniform area, so the background dominates and the lettering is the minority."""
    x0, y0, x1, y1 = box
    px = im.load(); W, H = im.size
    r, g, b = [], [], []
    for x in range(max(0, x0), min(W, x1), 4):
        for y in range(max(0, y0), min(H, y1), 4):
            p = px[x, y]; r.append(p[0]); g.append(p[1]); b.append(p[2])
    if not r: return (255, 255, 255)
    return (int(statistics.median(r)), int(statistics.median(g)), int(statistics.median(b)))

def bg_stats(im, box):
    """sample a ring just outside the text box"""
    x0, y0, x1, y1 = box
    px = im.load()
    W, H = im.size
    samples = []
    for pad in (4, 9):
        for x in range(max(0, x0 - pad), min(W, x1 + pad), 3):
            for y in (y0 - pad, y1 + pad - 1):
                if 0 <= y < H: samples.append(px[x, y])
        for y in range(max(0, y0 - pad), min(H, y1 + pad), 3):
            for x in (x0 - pad, x1 + pad - 1):
                if 0 <= x < W: samples.append(px[x, y])
    if not samples: return (255, 255, 255), 999
    r = [s[0] for s in samples]; g = [s[1] for s in samples]; b = [s[2] for s in samples]
    med = (int(statistics.median(r)), int(statistics.median(g)), int(statistics.median(b)))
    spread = max(statistics.pstdev(r), statistics.pstdev(g), statistics.pstdev(b))
    return med, spread

stats = {'filled': 0, 'boxed': 0, 'shrunk': 0}
# EXTRA 可以补在完全没有 OCR 结果的页上，这些页 blocks.json 里没有条目
for pg in EXTRA:
    blocks.setdefault(pg, {'page': pg, 'blocks': []})
pages = sorted(blocks)
for pg in pages:
    p = blocks[pg]
    for rect, ko in EXTRA.get(pg, []):
        p['blocks'].append({'x': rect[0], 'y': rect[1], 'x1': rect[2], 'y1': rect[3],
                            'ko': ko, 'nlines': 1, 'conf': 1.0})
    im = Image.open(f'ocr_png/{pg}.png').convert('RGB')
    d = ImageDraw.Draw(im)
    todo = [(i, b) for i, b in enumerate(p['blocks']) if f'{pg}.{i}' in zh]
    if not todo:
        im.save(f'out_png/{pg}.png'); continue
    for i, b in todo:
        text = zh[f'{pg}.{i}']
        x0, y0, x1, y1 = b['x'], b['y'], b['x1'], b['y1']
        bw, bh = x1 - x0, y1 - y0
        med, spread = bg_stats(im, (x0, y0, x1, y1))
        pad = max(4, min(int(bh * 0.10), 24))
        aw = max(40, int(bw * 1.04)); ah = max(24, int(bh * 1.32))
        cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
        start = max(11, min(int(bh / max(1, b['nlines']) * 0.92), FONT_MAX.get(f'{pg}.{i}', 60)))
        chosen = None
        for sz in range(start, 8, -1):
            f = font(sz); lh = int(sz * 1.28)
            ls = wrap(text, f, aw, d)
            if len(ls) * lh <= ah and max(d.textlength(l, font=f) for l in ls) <= aw:
                chosen = (f, ls, lh); break
        if chosen is None:
            f = font(9); chosen = (f, wrap(text, f, aw, d), 12); stats['shrunk'] += 1
        f, ls, lh = chosen
        tw = max(d.textlength(l, font=f) for l in ls); th = len(ls) * lh
        tx0, ty0 = cx - tw / 2, cy - th / 2
        # erase area = union of original text bbox and the new text extent
        ex = (int(min(x0, tx0) - pad), int(min(y0, ty0) - pad),
              int(max(x1, tx0 + tw) + pad), int(max(y1, ty0 + th) + pad))
        ov = ERASE_OVERRIDE.get(f'{pg}.{i}')
        rects = None
        if ov:
            rects = list(ov) if isinstance(ov[0], (list, tuple)) else [ov]
            ex = (min(r[0] for r in rects), min(r[1] for r in rects),
                  max(r[2] for r in rects), max(r[3] for r in rects))
            if f'{pg}.{i}' in MASK_ERASE:
                med = paper_colour(im, rects)
            else:
                med = bg_inside(im, (rects[0][0] + 3, rects[0][1] + 3,
                                     rects[0][2] - 3, rects[0][3] - 3))
            fg = (245, 245, 245) if sum(med) < 330 else (26, 26, 26)
            cx, cy = (ex[0] + ex[2]) // 2, (ex[1] + ex[3]) // 2
            ty0 = cy - th / 2
        erase_log.setdefault(pg, []).append(list(ex))
        if rects and f'{pg}.{i}' in MASK_ERASE:
            for r in rects: mask_erase(im, r, med)
            stats['filled'] += 1
        elif rects:
            for r in rects: d.rectangle(r, fill=med)
            stats['filled'] += 1
        elif spread < 26:
            d.rectangle(ex, fill=med); stats['filled'] += 1
        else:
            d.rounded_rectangle(ex, radius=max(6, pad), fill=med); stats['boxed'] += 1
        fg = (245, 245, 245) if sum(med) < 330 else (26, 26, 26)
        ty = ty0
        for l in ls:
            w = d.textlength(l, font=f)
            d.text((cx - w / 2, ty), l, font=f, fill=fg)
            ty += lh
    im.save(f'out_png/{pg}.png')
# copy untouched pages
import shutil
for fn in os.listdir('ocr_png'):
    if not os.path.exists(f'out_png/{fn}'):
        shutil.copy(f'ocr_png/{fn}', f'out_png/{fn}')
json.dump(erase_log, open('erase.json', 'w'))
print(stats, 'pages out:', len(os.listdir('out_png')))
