# 微信公众号文章 → PNG → PDF
# 用法：
#   python3 wx_fetch.py urls.txt out_dir
# urls.txt 每行一条，两种格式都认：
#   331<TAB>https://mp.weixin.qq.com/s?__biz=...
#   https://mp.weixin.qq.com/s/xxxxxxxx        (没有话号就按行号编)
# 微信从服务器侧访问会撞"当前环境异常"验证墙。本机浏览器能开的话通常也能跑；
# 撞墙时把 Chrome 里 mp.weixin.qq.com 的 Cookie 整条贴进环境变量 WX_COOKIE。

import sys, os, re, time, io, ssl, urllib.request

# macOS 上 python.org 版 Python 不带根证书，走 certifi
try:
    import certifi
    # 系统代理若指向 mitmproxy，需把它的 CA 一并信任（WX_CA 指向合并包）
    CTX = ssl.create_default_context(cafile=os.environ.get('WX_CA') or certifi.where())
except ImportError:
    CTX = ssl.create_default_context()
from PIL import Image

UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')
COOKIE = os.environ.get('WX_COOKIE', '')

# 直连，不走系统代理（系统代理可能指向 mitmproxy 或 Clash，都没必要经过）
NOPROXY = urllib.request.build_opener(urllib.request.ProxyHandler({}),
                                      urllib.request.HTTPSHandler(context=CTX))

def get(url, referer=None):
    h = {'User-Agent': UA, 'Accept-Language': 'zh-CN,zh;q=0.9'}
    if referer: h['Referer'] = referer          # mmbiz.qpic.cn 少了 Referer 直接 403
    if COOKIE:  h['Cookie'] = COOKIE
    return NOPROXY.open(urllib.request.Request(url, headers=h), timeout=30).read()

def img_urls(html):
    # 正文图片懒加载，真实地址在 data-src；顺序即阅读顺序
    us, seen = [], set()
    for m in re.finditer(r'data-src="(https?://mmbiz\.qpic\.cn/[^"]+)"', html):
        u = m.group(1).replace('&amp;', '&')
        if u not in seen: seen.add(u); us.append(u)
    return us

def title(html):
    m = re.search(r'var msg_title = [\'"](.*?)[\'"]', html) or \
        re.search(r'<h1[^>]*class="rich_media_title"[^>]*>(.*?)</h1>', html, re.S)
    return re.sub(r'<[^>]+>|\s+', '', m.group(1))[:60] if m else ''

def one(tag, url, outdir):
    d = os.path.join(outdir, tag); os.makedirs(d, exist_ok=True)
    html = get(url).decode('utf-8', 'ignore')
    if '环境异常' in html or '完成验证后即可继续访问' in html:
        print(f'  !! {tag} 撞验证墙 —— 在 Chrome 里开一次该链接，再把 Cookie 放进 WX_COOKIE'); return None
    if '该内容已被发布者删除' in html or '此内容因违规无法查看' in html:
        print(f'  !! {tag} 文章已被删除/屏蔽'); return None
    us = img_urls(html)
    print(f'  {tag} 「{title(html)}」 {len(us)} 图')
    ims = []
    for i, u in enumerate(us):
        p = os.path.join(d, f'{i:03d}.png')
        if not os.path.exists(p):
            for attempt in range(3):
                try:
                    im = Image.open(io.BytesIO(get(u, referer='https://mp.weixin.qq.com/')))
                    im.convert('RGB').save(p); break
                except Exception as e:
                    if attempt == 2: print(f'    图 {i} 失败: {e}'); p = None
                    else: time.sleep(2)
            time.sleep(0.3)
        if p and os.path.exists(p): ims.append(p)
    return ims

def to_pdf(ims, path):
    if not ims: return
    pgs = [Image.open(p).convert('RGB') for p in ims]
    pgs[0].save(path, save_all=True, append_images=pgs[1:], resolution=150)
    print(f'  → {path}  ({len(pgs)} 页)')

if __name__ == '__main__':
    src, outdir = sys.argv[1], sys.argv[2]
    os.makedirs(outdir, exist_ok=True)
    rows = []
    for n, line in enumerate(open(src, encoding='utf-8')):
        line = line.strip()
        if not line or line.startswith('#'): continue
        tag, url = (line.split('\t', 1) if '\t' in line else (f'{n:03d}', line))
        rows.append((tag.strip(), url.strip()))
    print(f'共 {len(rows)} 话')
    bad = []
    for tag, url in rows:
        pdf = os.path.join(outdir, f'{tag}.pdf')
        if os.path.exists(pdf): print(f'  {tag} 已存在，跳过'); continue
        try:
            ims = one(tag, url, outdir)
            if ims: to_pdf(ims, pdf)
            else: bad.append(tag)
        except Exception as e:
            print(f'  !! {tag} {e}'); bad.append(tag)
        time.sleep(1)
    print('失败:', bad or '无')
