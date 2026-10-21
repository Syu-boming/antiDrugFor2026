import json,sys
m=json.load(open('metrics.json'))
el=m['el']; ed=m['edge']
def bad(rec):
    a=rec['checks']['a']['models']
    return {k:[(b['ref'],b['hyp'],b['kind'][:4]) for b in v['bad']] for k,v in a.items()}
for k in ed:
    e=ed[k]; l=el.get(k)
    if not l: print(k,e['role'],'EL缺'); continue
    lb=bad(l); eb=bad(e)
    flags=[]
    if l['failed'] or e['failed']:
        print(k,l['role'],'EL fail',l['failed'],'edge fail',e['failed'])
        if any(lb.values()): print('   EL :',lb)
        if any(eb.values()): print('   edg:',eb)
        if 'b' in l['failed']: print('   ELb',l['checks']['b']['words'])
        if 'b' in e['failed']: print('   edb',e['checks']['b']['words'])
        if 'd' in l['failed']: print('   ELd',l['checks']['d']['value'],l['checks']['d']['range'])
        if 'd' in e['failed']: print('   edd',e['checks']['d']['value'],e['checks']['d']['range'])
