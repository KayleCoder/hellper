# mitmproxy addon：从微信内打开的文章请求里截取 profile_ext 所需的凭证。
#
# 思路照搬 wechat-article-exporter 的 public/plugins/credential.py：
# 只拦 https://mp.weixin.qq.com/s?__biz=... 这个**文章页**，不碰微信自己的 API。
# 文章页是 WebView 的标准 HTTPS，所以不涉及腾讯自研的 mmtls，
# 不会触发微信"被中间人攻击"的判定。
#
# 用法：
#   brew install mitmproxy
#   mitmdump -s pipeline/wx_credential.py --listen-port 8080
#   # 系统代理指向 127.0.0.1:8080，浏览器访问 mitm.it 装并信任证书
#   # 然后在 Mac 微信里随便点开该公众号的一篇文章
#   # → 凭证写入 wx_credential.json
#
# 凭证里的 key 约 30 分钟过期，但 wx_hist.py 吐出的是永久链接，枚举一次就够。

import json, time
from urllib.parse import urlparse, parse_qs

OUT = 'wx_credential.json'

class GrabCredential:
    def __init__(self):
        self.store = {}

    def response(self, flow):
        url = flow.request.url
        if not url.startswith('https://mp.weixin.qq.com/s?__biz='):
            return
        q = parse_qs(urlparse(url).query)
        one = lambda k: q.get(k, [''])[0]
        biz = one('__biz')
        if not biz:
            return
        rec = {
            'biz':         biz,
            'uin':         one('uin'),
            'key':         one('key'),
            'pass_ticket': one('pass_ticket'),
            'cookie':      flow.response.headers.get('Set-Cookie', ''),
            'url':         url,
            'timestamp':   int(time.time() * 1000),
        }
        # key 是关键，没截到说明这篇不是从微信内打开的
        if not rec['key']:
            print(f'[credential] {biz} 拿到 URL 但没有 key —— 请在**微信内**打开文章，不要用浏览器')
            return
        self.store[biz] = rec
        with open(OUT, 'w') as f:
            json.dump(list(self.store.values()), f, ensure_ascii=False, indent=2)
        print(f'[credential] ✓ 已截获 biz={biz}  uin={rec["uin"]}  key={rec["key"][:12]}…')
        print(f'[credential]   → {OUT}；接着跑：')
        print(f'[credential]   python3 pipeline/wx_hist.py --from {OUT} > s2/all.txt')

addons = [GrabCredential()]
