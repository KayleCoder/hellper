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
    # rects chosen to clear the lettering while dodging the black disc and the panel border
    '074.4': [(170, 1040, 750, 1190), (620, 1175, 750, 1224)],
    '074.5': [(110, 1488, 345, 1680), (335, 1520, 478, 1680)],
    # 045.0's cluster stopped short of the "FLAG" half of the sub-title, leaving it
    # stranded next to the Chinese; widen to the whole two-line label.
    '045.0': [(92, 14, 734, 158)],
    # 088.0 boxed only the second syllable of "데굴", so a stray "데" survived
    # right beside the Chinese. Cover the whole word.
    '088.0': [(304, 216, 404, 272)],
}
MASK_ERASE = {'074.4', '074.5'}
erase_log = {}
# blocks whose lettering is far larger than a speech bubble (title cards, big sfx)
FONT_MAX = {
    # the default 60px cap left every title band and shout far smaller than the
    # original lettering; raise it per label so the type reads at its drawn weight.
    '014.0': 80,  '022.0': 96,  '030.0': 106, '033.0': 150, '045.0': 66,
    '059.1': 80,  '059.2': 78,  '069.1': 84,  '076.0': 86,  '083.0': 76,
    '093.1': 96,  '082.0': 74,  '080.4': 90,  '079.1': 80,  '055.1': 62, 
    '025.0': 64,  '026.1': 64,  '027.1': 64,  '028.1': 64,  '074.3': 100,
}
# text the OCR missed entirely, or clusters it merged wrongly: page -> [(rect, ko)]
EXTRA = {
    # p074's cluster swallowed a title band and two bubbles into one box; split by hand.
    '074': [((95, 775, 570, 905),    '역주행'),
            ((190, 1060, 570, 1175), '꺄아아아악!!!'),
            ((95, 1495, 285, 1670),  '꼴까닥 입니다다다닥!!')],
    '079': [((478, 1908, 540, 1954), '폴짝')],
    # boxed unit nameplate Vision could not read at all; found by a 2x re-OCR
    # of the erased pages.
    # rect kept well inside the drawn frame: the erase pad must not eat its borders
    '055': [((114, 2130, 718, 2224), '초미세자폭비행단')],
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
