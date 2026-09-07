import json, collections
pages=[]; cur=None
for ln in open('ocr_box.tsv',encoding='utf-8'):
    ln=ln.rstrip('\n')
    if ln.startswith('FILE\t'):
        _,name,w,h=ln.split('\t'); cur={'page':name[:3],'w':int(w),'h':int(h),'lines':[]}; pages.append(cur)
    elif ln.startswith('L\t'):
        _,x,y,w,h,c,t=ln.split('\t',6)
        cur['lines'].append({'x':int(x),'y':int(y),'w':int(w),'h':int(h),'c':float(c),'t':t})

def cluster(lines):
    lines=sorted(lines,key=lambda l:(l['y'],l['x']))
    blocks=[]
    for l in lines:
        placed=False
        for b in blocks:
            last=b['lines'][-1]
            lh=max(last['h'],l['h'])
            vgap=l['y']-(last['y']+last['h'])
            # horizontal overlap ratio vs block span
            bx0=min(z['x'] for z in b['lines']); bx1=max(z['x']+z['w'] for z in b['lines'])
            ox=min(bx1,l['x']+l['w'])-max(bx0,l['x'])
            if vgap < lh*0.95 and vgap > -lh*0.6 and ox > 0.25*min(bx1-bx0,l['w']):
                b['lines'].append(l); placed=True; break
        if not placed: blocks.append({'lines':[l]})
    for b in blocks:
        ls=b['lines']
        b['x']=min(z['x'] for z in ls); b['y']=min(z['y'] for z in ls)
        b['x1']=max(z['x']+z['w'] for z in ls); b['y1']=max(z['y']+z['h'] for z in ls)
        b['ko']=' '.join(z['t'] for z in ls)
        b['nlines']=len(ls)
        b['conf']=round(min(z['c'] for z in ls),2)
    return sorted(blocks,key=lambda b:(b['y'],b['x']))

out=[]
for p in pages:
    if not p['lines']: continue
    p['blocks']=cluster(p['lines'])
    for l in p['lines']: pass
    out.append({'page':p['page'],'w':p['w'],'h':p['h'],
                'blocks':[{k:b[k] for k in ('x','y','x1','y1','ko','nlines','conf')} for b in p['blocks']]})
json.dump(out,open('blocks.json','w',encoding='utf-8'),ensure_ascii=False,indent=0)
nb=sum(len(p['blocks']) for p in out)
print('pages with text',len(out),'blocks',nb)
# print compact list for translation
for p in out:
    for i,b in enumerate(p['blocks']):
        print(f"{p['page']}.{i}\t{b['ko']}")
