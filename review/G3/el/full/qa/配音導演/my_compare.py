import json, re, difflib, collections
from opencc import OpenCC
from pypinyin import lazy_pinyin, Style
cc=OpenCC('s2t')
DIG=dict(zip('0123456789','零一二三四五六七八九'))
def norm(t):
    t=cc.convert(t)
    t=''.join(DIG.get(c,c) for c in t)
    return ''.join(re.findall(r'[一-鿿]',t))
def py(t,tone=True): return lazy_pinyin(t,style=Style.TONE3 if tone else Style.NORMAL,neutral_tone_with_five=True)
TW={'zh':'z','ch':'c','sh':'s'}
def flat(p):
    for k,v in TW.items():
        if p.startswith(k): p=v+p[2:]
    p=re.sub(r'ing',"in",p); p=re.sub(r'eng','en',p)
    return p
def diffs(ref,hyp):
    r,h=norm(ref),norm(hyp)
    pr,ph=py(r),py(h)
    out=[]
    sm=difflib.SequenceMatcher(a=pr,b=ph,autojunk=False)
    for op,i1,i2,j1,j2 in sm.get_opcodes():
        if op=='equal': continue
        rs,hs=r[i1:i2],h[j1:j2]
        a=[re.sub(r'\d','',x) for x in pr[i1:i2]]; b=[re.sub(r'\d','',x) for x in ph[j1:j2]]
        if a==b: kind='聲調'
        elif [flat(x) for x in a]==[flat(x) for x in b]: kind='台灣讀音(捲舌/前後鼻)'
        else: kind='字音不同'
        out.append((rs,hs,kind))
    return out
T=collections.defaultdict(dict)
for l in open('my_transcripts.jsonl'):
    d=json.loads(l); T[(d['id'],d['role'],d['ref'])][(d['engine'],d['model'])]=d['hyp']
res=[]
for (lid,role,ref),v in T.items():
    row={'id':lid,'role':role,'ref':ref}
    for eng in ('el','edge'):
        for mdl in ('small','large-v3-turbo'):
            h=v.get((eng,mdl))
            if h is None: continue
            row[f'{eng}|{mdl}']={'hyp':h,'diff':diffs(ref,h),'lead_en':norm(h)[:1]=='嗯' and norm(ref)[:1]!='嗯','tail_en':norm(h)[-1:]=='嗯' and norm(ref)[-1:]!='嗯'}
    res.append(row)
json.dump(res,open('my_compare.json','w'),ensure_ascii=False,indent=1)
# summary
def bad(d): return [x for x in d['diff'] if x[2]!='聲調' or True]
for row in res:
    for eng in ('el','edge'):
        s=row.get(f'{eng}|small'); L=row.get(f'{eng}|large-v3-turbo')
        if not s or not L: continue
        # both models non-tone, non-tw difference at overlapping ref chars
        sd={x[0] for x in s['diff'] if x[2]=='字音不同'}; ld={x[0] for x in L['diff'] if x[2]=='字音不同'}
        both=[x for x in sd if any(x and (x in y or y in x) for y in ld if y)]
        flags=[]
        if both: flags.append('兩模型都字音不同:'+','.join(both))
        if s['tail_en'] or L['tail_en']: flags.append('句尾殘留嗯')
        if s['lead_en'] or L['lead_en']: flags.append('句首殘留嗯')
        if flags: print(row['id'],row['role'],eng,flags,'| S:',s['hyp'],'| L:',L['hyp'])
