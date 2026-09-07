#!/usr/bin/env python3
"""Naver webtoon 图片清单 -> 逐页 jpg + 合成 PDF。

用法:  python3 pipeline/naver_fetch.py 007
读取   s2ko/urls/007.txt   (每行一个图片 URL，# 开头忽略)
产出   s2ko/ep007/001.jpg ...   和   s2ko/007.pdf

CDN 不需要 cookie，只认 Referer。
"""
import os, sys, time, subprocess
from concurrent.futures import ThreadPoolExecutor
from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REFERER = 'https://comic.naver.com/'
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36')
# 代理走系统设置即可；curl 用系统钥匙串验证证书，MITM 代理也能过。
PROXY = os.environ.get('HELLPER_PROXY', 'http://127.0.0.1:7897')


def grab(job):
    """用 curl 下载单张图。返回 (序号, 成功?, 字节数或错误信息)。"""
    idx, url, dest = job
    cmd = ['curl', '-sS', '--fail', '--max-time', '60',
           '-e', REFERER, '-A', UA, '-o', dest, url]
    if PROXY:
        cmd[1:1] = ['-x', PROXY]
    for attempt in range(4):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True)
            if r.returncode != 0:
                raise RuntimeError(r.stderr.strip() or f'curl exit {r.returncode}')
            size = os.path.getsize(dest)
            if size < 1024:
                raise ValueError(f'too small: {size}B')
            Image.open(dest).verify()          # 确认是完整图片
            return (idx, True, size)
        except Exception as e:
            if attempt == 3:
                return (idx, False, f'{type(e).__name__}: {e}')
            time.sleep(1.5 * (attempt + 1))


def main(ep):
    ep = ep.zfill(3)
    src = os.path.join(ROOT, 's2ko', 'urls', f'{ep}.txt')
    outdir = os.path.join(ROOT, 's2ko', f'ep{ep}')
    if not os.path.exists(src):
        sys.exit(f'找不到清单: {src}')
    urls = [l.strip() for l in open(src, encoding='utf-8')]
    urls = [u for u in urls if u and not u.startswith('#')]
    if not urls:
        sys.exit(f'清单是空的: {src}')
    os.makedirs(outdir, exist_ok=True)

    jobs = []
    for i, u in enumerate(urls, 1):
        ext = '.png' if u.split('?')[0].lower().endswith('.png') else '.jpg'
        jobs.append((i, u, os.path.join(outdir, f'{i:03d}{ext}')))

    print(f'[{ep}] {len(jobs)} 张，开始下载…')
    with ThreadPoolExecutor(max_workers=6) as pool:
        results = list(pool.map(grab, jobs))

    bad = [(i, m) for i, ok, m in results if not ok]
    total = sum(m for _, ok, m in results if ok)
    print(f'[{ep}] 成功 {len(results)-len(bad)}/{len(results)}，共 {total/1048576:.1f} MB')
    for i, m in bad:
        print(f'   !! 第 {i} 张失败: {m}')
    if bad:
        sys.exit(f'[{ep}] 有 {len(bad)} 张没下来，PDF 先不合成。')

    files = sorted(f for f in os.listdir(outdir) if f.lower().endswith(('.jpg', '.png')))
    pdf = os.path.join(ROOT, 's2ko', f'{ep}.pdf')
    first, rest = None, []
    try:
        first = Image.open(os.path.join(outdir, files[0])).convert('RGB')
        for f in files[1:]:
            rest.append(Image.open(os.path.join(outdir, f)).convert('RGB'))
        first.save(pdf, save_all=True, append_images=rest, resolution=150.0)
    finally:
        for im in rest:
            im.close()
    print(f'[{ep}] → s2ko/{ep}.pdf  ({len(files)} 页, {os.path.getsize(pdf)/1048576:.1f} MB)')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit('用法: python3 pipeline/naver_fetch.py 007 [008 ...]')
    for a in sys.argv[1:]:
        main(a)
