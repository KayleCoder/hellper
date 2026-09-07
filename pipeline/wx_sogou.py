# 经搜狗微信按话号逐话抓取 → PDF。不需要公众号后台。
#
#   python3 wx_sogou.py 331 416 s2/
#
# 原理：搜「<关键词> 第N话」→ 精确命中 → 解析 /link 跳转拿到真实 mp 地址 → 下图 → 拼 PDF。
# 注意：搜狗解析出的 mp 地址带 timestamp+signature，是限时的（几小时），
#      所以必须「搜到就立刻下」，不能先攒链接列表留着以后用。
# 搜狗有反爬，脚本默认每话间隔 15 秒；撞验证码会停下并报出断点，换网络或等一阵重跑即可。
# 已生成 PDF 的话会自动跳过，重跑天然续传。

import sys, os, re, time, html, ssl, random, urllib.request, urllib.parse, http.cookiejar
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import wx_fetch                                     # 复用下图 + 拼 PDF

KEY   = os.environ.get('WX_KEY', 'KBRS')            # 账号里每话标题都带的固定前缀
DELAY = float(os.environ.get('WX_DELAY', '15'))
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')
CTX = wx_fetch.CTX
cj  = http.cookiejar.CookieJar()
OP  = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj),
                                  urllib.request.HTTPSHandler(context=CTX))
OP.addheaders = [('User-Agent', UA), ('Accept-Language', 'zh-CN,zh;q=0.9')]

class Blocked(Exception): pass

def search(ep):
    q = urllib.parse.urlencode({'query': f'{KEY} 第{ep}话', 'type': 2, 'ie': 'utf8'})
    url = f'https://weixin.sogou.com/weixin?{q}'
    s = OP.open(url, timeout=30).read().decode('utf-8', 'ignore')
    if '请输入验证码' in s or 'antispider' in s:
        raise Blocked('搜狗要验证码了')
    titles = [re.sub(r'<[^>]+>|\s+', '', html.unescape(t))
              for t in re.findall(r'uigs="article_title_\d+">(.*?)</a>', s, re.S)]
    links  = [html.unescape(l) for l in re.findall(r'href="(/link\?url=[^"]+)"', s)]
    # 只认标题里确实是「第N话」的那条，防止搭到邻近话数
    pat = re.compile(rf'第\s*{ep}\s*话')
    for t, l in zip(titles, links):
        if pat.search(t) and KEY in t:
            return t, l, url
    return None, None, url

def resolve(link, referer):
    link = urllib.parse.quote(link, safe='/?=&%.-_')     # 跳转链接里带空格
    r = OP.open(urllib.request.Request('https://weixin.sogou.com' + link,
                headers={'User-Agent': UA, 'Referer': referer}), timeout=30)
    body = r.read().decode('utf-8', 'ignore')
    real = ''.join(re.findall(r"url \+= '([^']*)'", body)).replace('@', '')
    if not real:
        if '验证码' in body: raise Blocked('跳转页要验证码')
        return None
    return real

if __name__ == '__main__':
    lo, hi, outdir = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3]
    os.makedirs(outdir, exist_ok=True)
    missing, done = [], 0
    for ep in range(lo, hi + 1):
        tag = str(ep)
        pdf = os.path.join(outdir, f'{tag}.pdf')
        if os.path.exists(pdf):
            print(f'{tag} 已存在，跳过'); continue
        try:
            title, link, ref = search(ep)
            if not link:
                print(f'{tag} ✗ 搜狗没搜到'); missing.append(ep); continue
            real = resolve(link, ref)
            if not real:
                print(f'{tag} ✗ 跳转解析失败'); missing.append(ep); continue
            print(f'{tag} 「{title}」')
            ims = wx_fetch.one(tag, real, outdir)
            if ims: wx_fetch.to_pdf(ims, pdf); done += 1
            else:   missing.append(ep)
        except Blocked as e:
            print(f'\n!! {e} —— 断点在第 {ep} 话。换个网络或等一阵，重跑同一条命令会自动续传。')
            break
        except Exception as e:
            print(f'{tag} ✗ {e}'); missing.append(ep)
        time.sleep(DELAY + random.uniform(0, 5))
    # 缺的话号落盘，交给后续方法（profile_ext / RPA 手工）接力
    have = sorted(int(f[:-4]) for f in os.listdir(outdir)
                  if f.endswith('.pdf') and f[:-4].isdigit())
    gap = [e for e in range(lo, hi + 1) if e not in have]
    with open(os.path.join(outdir, 'missing.txt'), 'w') as f:
        f.write('\n'.join(map(str, gap)) + '\n')
    print(f'\n本轮完成 {done} 话；目录内已有 {len(have)} 话；'
          f'仍缺 {len(gap)} 话 → {os.path.join(outdir, "missing.txt")}')
