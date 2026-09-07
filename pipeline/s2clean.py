import sys, re, os
# 水印「@我与洪X胖的日常」及其 OCR 变体的字符池
WMCHARS = set('我与與洪胖的日常半目吊堂帛写共月进肜彤脱肝眇肛肚胀胜脸腓妈妇@＠ .．·-—~')
SFX = re.compile(r'^[啊呀哦噢嗯哼咳嘿哈嘻呵唔喔哇噗砰咚啪咔嚓唰哗嗡叮铃咕噜滋吱嘶呼轰隆嘭砸踏嗒哐当锵铛喀]+[~！!？?\-—…\.。、]*$')
def is_wm(s):
    if len(s) > 14: return False
    core = [c for c in s if not c.isspace()]
    if not core: return True
    hit = sum(1 for c in core if c in WMCHARS)
    return hit / len(core) >= 0.75
def clean(path):
    out=[]
    for ln in open(path,encoding='utf-8'):
        s = ln.strip(' |　“”"\'\n')
        if not s or s=='---' or s.startswith('#'): continue
        if is_wm(s): continue
        if len(s)<=2: continue
        if s.upper() in ('HELLPER','SEASON','SAKK','-SAKK-','ACID'): continue
        if SFX.match(s): continue
        if re.fullmatch(r'(.)\1{1,}[~！!？?\-—…]*', s): continue
        if re.fullmatch(r'[0-9A-Za-z\W_]{1,4}', s): continue
        out.append(s)
    res=[]
    for x in out:
        if not res or res[-1]!=x: res.append(x)
    return res
if __name__=='__main__':
    for p in sys.argv[1:]:
        print(f"##### {os.path.basename(p)[:-4]}")
        print('|'.join(clean(p)))
