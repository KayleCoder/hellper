import json, os, re, subprocess, sys, time, random

BASE = "/Users/zhouzibo/Workspaces/hellper/s1ref"
PROXY = "http://127.0.0.1:7897"
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
IMG_DIR = os.path.join(BASE, "img")
OCR_DIR = os.path.join(BASE, "ocr")
os.makedirs(IMG_DIR, exist_ok=True); os.makedirs(OCR_DIR, exist_ok=True)


def log(m):
    with open(os.path.join(BASE, "progress.log"), "a") as f:
        f.write(f"[{time.strftime('%H:%M:%S')}] {m}\n")

def get(url, referer, binary=False, tries=4):
    for t in range(tries):
        r = subprocess.run(["curl", "-s", "-x", PROXY, "-A", UA,
                            "-H", f"Referer: {referer}",
                            "-H", "Accept-Language: zh-TW,zh;q=0.9,en;q=0.8",
                            "--compressed", "-m", "60", url],
                           capture_output=True)
        if r.returncode == 0 and len(r.stdout) > 500:
            return r.stdout if binary else r.stdout.decode("utf-8", "replace")
        wait = 5 * (t + 1) + random.uniform(0, 3)
        log(f"  retry {t+1} (rc={r.returncode} n={len(r.stdout)}) sleep {wait:.0f}s :: {url[:80]}")
        time.sleep(wait)
    return None

eps = json.load(open(os.path.join(BASE, "episodes.json")))
order = sorted(eps, key=lambda k: int(k))
LIST_REF = "https://www.webtoons.com/zh-hant/action/hellper/list?title_no=180"

log(f"=== START: {len(order)} episodes ===")
for k in order:
    no = int(k); title = eps[k]["title"]; url = eps[k]["url"]
    out_txt = os.path.join(OCR_DIR, f"ep{no:03d}.txt")
    if os.path.exists(out_txt) and os.path.getsize(out_txt) > 80:
        continue
    log(f"EP {no:03d} {title}")
    html = get(url, LIST_REF)
    if not html:
        log(f"  !! html failed"); continue
    m = re.search(r'id="_imageList"(.*?)</div>', html, re.S)
    urls = re.findall(r'data-url="([^"]+)"', m.group(1)) if m else []
    urls = [u for u in urls if "tw_warning" not in u and "_notice" not in u]
    if not urls:
        log(f"  !! no images (paywalled?)"); continue
    d = os.path.join(IMG_DIR, f"ep{no:03d}"); os.makedirs(d, exist_ok=True)
    paths = []
    for i, u in enumerate(urls):
        p = os.path.join(d, f"{i:03d}.jpg")
        if not os.path.exists(p) or os.path.getsize(p) < 1000:
            data = get(u, "https://www.webtoons.com/", binary=True)
            if not data:
                log(f"  !! img {i} failed"); continue
            open(p, "wb").write(data)
            time.sleep(random.uniform(0.7, 1.4))
        paths.append(p)
    if not paths:
        continue
    try:
        r = subprocess.run([os.path.join(BASE, "ocrbin"), "1.0"] + paths,
                           capture_output=True, text=True, timeout=1800)
        txt = r.stdout
    except Exception as e:
        log(f"  !! ocr failed {e}"); continue
    txt = re.sub(r'^===FILE:.*$', '---', txt, flags=re.M)
    with open(out_txt, "w") as f:
        f.write(f"# EP{no:03d} {title}\n{txt}")
    log(f"  ok: {len(paths)} imgs, {len(txt)} chars")
    time.sleep(random.uniform(2.5, 4.5))
log("=== DONE ===")
