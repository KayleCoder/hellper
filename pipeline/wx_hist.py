# 用微信客户端的登录参数枚举公众号全部历史文章 → urls.txt
#
# 参数怎么来：wechatDownload（或 mitmproxy/Charles 等任意抓包工具）会在你用
# 微信内置浏览器打开该号任意一篇文章时，截到一条 mp/profile_ext 请求，
# 里面就带着下面四个值。key 大约 30 分钟过期，但本脚本吐出的是永久链接，
# 枚举完一次就够了，下载可以慢慢来。
#
#   export WX_BIZ=...  WX_UIN=...  WX_KEY=...  WX_PASSTICKET=...
#   python3 wx_hist.py > s2/all.txt
#   awk -F'\t' '$1>=331 && $1<=416' s2/all.txt > s2/urls.txt
#   python3 wx_fetch.py s2/urls.txt s2/

import os, sys, re, json, time, ssl, urllib.request, urllib.parse
try:
    import certifi
    # 系统代理若指向 mitmproxy，需把它的 CA 一并信任（WX_CA 指向合并包）
    CTX = ssl.create_default_context(cafile=os.environ.get('WX_CA') or certifi.where())
except ImportError:
    CTX = ssl.create_default_context()

# 两种取参方式：wx_credential.py 吐的 json，或四个环境变量
if '--from' in sys.argv:
    _c = json.load(open(sys.argv[sys.argv.index('--from') + 1]))[-1]
    BIZ, UIN, KEY = _c['biz'], _c['uin'], _c['key']
    PT, COOKIE = _c.get('pass_ticket', ''), _c.get('cookie', '')
else:
    BIZ = os.environ['WX_BIZ']; UIN = os.environ['WX_UIN']
    KEY = os.environ['WX_KEY']; PT  = os.environ.get('WX_PASSTICKET', '')
    COOKIE = os.environ.get('WX_COOKIE', '')
UA = ('Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 '
      '(KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.49(0x18003128) NetType/WIFI Language/zh_CN')

def getmsg(offset):
    q = urllib.parse.urlencode({'action':'getmsg','__biz':BIZ,'f':'json','offset':offset,
                                'count':10,'is_ok':1,'scene':124,'uin':UIN,'key':KEY,
                                'pass_ticket':PT,'wxtoken':'','appmsg_token':'','x5':0})
    url = f'https://mp.weixin.qq.com/mp/profile_ext?{q}'
    h = {'User-Agent': UA}
    if COOKIE: h['Cookie'] = COOKIE
    r = urllib.request.urlopen(urllib.request.Request(url, headers=h), timeout=30, context=CTX)
    return json.loads(r.read().decode('utf-8', 'ignore'))

def ep(title):
    m = re.search(r'第\s*(\d{1,4})\s*话', title)
    return m.group(1) if m else '?'

rows, offset = [], 0
while True:
    d = getmsg(offset)
    if d.get('ret') not in (0, '0', None):
        print(f'# ret={d.get("ret")} {d.get("errmsg")}  '
              f'(-3 通常是 key 过期，重新抓一次参数)', file=sys.stderr); break
    msgs = json.loads(d.get('general_msg_list', '{}')).get('list', [])
    if not msgs: break
    for m in msgs:
        info = m.get('app_msg_ext_info')
        if not info: continue
        for a in [info] + (info.get('multi_app_msg_item_list') or []):
            t, u = a.get('title', ''), a.get('content_url', '')
            if u: rows.append((ep(t), u.replace('\\/', '/').replace('&amp;', '&'), t))
    print(f'# offset={offset} 累计 {len(rows)}', file=sys.stderr)
    if not d.get('can_msg_continue'): break
    offset = d.get('next_offset', offset + 10)
    time.sleep(2)

seen = set()
for e, u, t in rows:
    if u in seen: continue
    seen.add(u); print(f'{e}\t{u}\t{t}')
print(f'# 共 {len(seen)} 篇', file=sys.stderr)
