"""把各 batch_*.md 的「逐话一句」合并成 episodes.md，按篇章分段。"""
import re, glob, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
lines = {}
for f in sorted(glob.glob("batch_*.md")):
    s = open(f, encoding="utf-8").read()
    m = re.search(r"## 逐话一句\s*\n(.*?)(?=\n## )", s, re.S)
    if not m: continue
    for ln in m.group(1).splitlines():
        mm = re.match(r"- ep(\d{3})\b(.*)", ln.strip())
        if mm: lines[int(mm.group(1))] = "- ep" + mm.group(1) + mm.group(2)
sections = [("PROLOGUE（ep000–019）", 0, 19), ("MADMAN（ep020–181）", 20, 181), ("EPILOGUE（ep182–187）", 182, 187), ("AND（ep188）", 188, 188)]
out = ["# 地狱尽头（HELLPER 第一季简体）逐话一句", "",
       "> 由 batch_*.md 的「逐话一句」合并而来。话号 = 漫网第 N 话；台版对照 `s1ref/ocr/ep(N+1)`。ep097 站点损坏，已从用户提供的 081-100 合集 PDF 截出补齐。", ""]
for title, a, b in sections:
    out += [f"## {title}", ""]
    for n in range(a, b + 1):
        out.append(lines.get(n, f"- ep{n:03d} （缺）"))
    out.append("")
open("episodes.md", "w", encoding="utf-8").write("\n".join(out))
missing = [n for n in range(189) if n not in lines]
print(f"{len(lines)} 话已合并；缺: {missing}")
