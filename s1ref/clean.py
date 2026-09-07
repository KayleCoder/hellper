import sys, re, glob, os
SFX = re.compile(r'^[嗶嗡咕嘟噗通抖咻啪嘰喀啦砰哐咚唰沙嘶隔呃嗝呼哈嘻科唧咿呀啊噢喔嘎登哼嘖咔嚓啼扭動探頭撓晃顫發燙掉淚騷動喧嘩跳動翻開挺直躬噠甩擦咬咕嚕滴答朧朦怒瞪叭唷嗚嘿哇喏噁髒]+[~！!？?\-—…\.。、]*$')
NOISE = {'HELLPER','HELLPJR','HELLPAR','HELLPaR','HELLP3R','HELLPSR','HELLP当R','HELLPER.','朔','地獄盡頭','待續','KILLBEROS','KILLBERTE','KILL BEROS','KILCBEROS','MELL','HELL','SEASON 1','—','-','·','•','口','5','E','A','M','G','①','）','(',')'}
def clean(path):
    out=[]
    for ln in open(path,encoding='utf-8'):
        s=ln.strip()
        if not s or s=='---': continue
        if s in NOISE: continue
        if len(s)<=1: continue
        if SFX.match(s): continue
        if re.fullmatch(r'(.)\1{1,}[~！!？?\-—…]*', s): continue
        if re.fullmatch(r'[0-9A-Za-z\W_]{1,4}', s): continue
        out.append(s)
    # collapse consecutive duplicates
    res=[]
    for x in out:
        if not res or res[-1]!=x: res.append(x)
    return res
for p in sys.argv[1:]:
    print(f"##### {os.path.basename(p)}")
    print('|'.join(clean(p)))
