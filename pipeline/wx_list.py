# ⚠️ 已失效，不要用。留档仅作参考。
# 公众号后台「超链接」枚举接口已被微信官方于 2026-07-30 封禁。
# 依赖该接口的 wechat-article-exporter (12.5k star) 因此停止维护：
#   https://github.com/wechat-article/wechat-article-exporter/issues/200
# 仍然活着的是 Credential + profile_ext 路线，见 wx_hist.py。
#
# 枚举某公众号的全部已发表文章 → urls.txt（给 wx_fetch.py 吃）
#
# 需要一个「公众号后台」的登录态。作者本人的号最省事；你也可以自己注册个免费订阅号，
# 后台的「超链接」功能本来就允许列出任意公众号的历史文章。
#
# 取参数：
#   1. Chrome 登录 https://mp.weixin.qq.com/ ，地址栏 URL 里的 token=xxxxxxx 就是 WX_TOKEN
#   2. F12 → Network → 随便一个 cgi-bin 请求 → 复制整条 Cookie → WX_COOKIE
#   3. fakeid：后台 新建图文 → 工具栏「超链接」→ 选择其他公众号 → 搜账号名 → 点进去，
#      Network 里 appmsg?...fakeid=XXX 的那串就是。查自己的号可以留空。
#
# 用法：
#   export WX_TOKEN=1234567 WX_COOKIE='...' WX_FAKEID='...'
#   python3 wx_list.py > s2/all.txt
#   awk -F'\t' '$1>=331 && $1<=416' s2/all.txt > s2/urls.txt
#
# 限速：这个接口卡得紧，大约几十次请求就会返回 freq control，需要等一小时。
# 脚本一次取 20 条、间隔 5 秒，遇到限速会停下并把已拿到的写出来，重跑会接着上次的 begin。

import os, sys, json, time, re, ssl, urllib.request, urllib.parse
try:
    import certifi; CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    CTX = ssl.create_default_context()

TOKEN  = os.environ['WX_TOKEN']
COOKIE = os.environ['WX_COOKIE']
FAKEID = os.environ.get('WX_FAKEID', '')
COUNT  = int(os.environ.get('WX_COUNT', '20'))
BEGIN  = int(os.environ.get('WX_BEGIN', '0'))

API = 'https://mp.weixin.qq.com/cgi-bin/appmsg'
H = {'User-Agent': ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
                    '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'),
     'Referer': f'https://mp.weixin.qq.com/cgi-bin/appmsg?t=media/appmsg_edit&token={TOKEN}&lang=zh_CN',
     'Cookie': COOKIE}

def page(begin):
    q = urllib.parse.urlencode({'action':'list_ex','begin':begin,'count':COUNT,'fakeid':FAKEID,
                                'type':9,'query':'','token':TOKEN,'lang':'zh_CN','f':'json','ajax':1})
    r = urllib.request.urlopen(urllib.request.Request(f'{API}?{q}', headers=H), timeout=30, context=CTX)
    return json.loads(r.read().decode('utf-8'))

def ep(title):
    # 【KBRS】第2部 第417话 END+后记  →  417
    m = re.search(r'第\s*(\d{1,4})\s*话', title) or re.search(r'(\d{2,4})', title)
    return m.group(1) if m else '?'

rows, begin = [], BEGIN
while True:
    d = page(begin)
    base = d.get('base_resp', {})
    if base.get('ret') not in (0, None):
        print(f'# 接口返回 ret={base.get("ret")} {base.get("err_msg")}  '
              f'(freq control 就是被限速了，等一小时后 WX_BEGIN={begin} 续跑)', file=sys.stderr)
        break
    lst = d.get('app_msg_list', [])
    if not lst: break
    for a in lst:
        rows.append((ep(a['title']), a['link'], a['title']))
    print(f'# begin={begin} 取到 {len(lst)} 条，累计 {len(rows)}', file=sys.stderr)
    begin += COUNT
    if begin >= d.get('app_msg_cnt', 0): break
    time.sleep(5)

for e, link, title in rows:
    print(f'{e}\t{link}\t{title}')
print(f'# 共 {len(rows)} 篇', file=sys.stderr)
