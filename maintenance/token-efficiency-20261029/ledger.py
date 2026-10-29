import json,sqlite3,collections
from pathlib import Path
out={'stages':{},'states':{},'policies':[],'samples':[]}
with sqlite3.connect('file:/home/user/geo-editorial/runtime-api/api/costs.sqlite?mode=ro',uri=True) as db:
 db.row_factory=sqlite3.Row
 for row in db.execute("select * from costs where date=?",('2026-10-29',)):
  r=dict(row);u=json.loads(r['usage']) if r['usage'] else {};a=out['stages'].setdefault(r['stage'],{'calls':0,'charged':0,'prompt_tokens':0,'completion_tokens':0,'prompt_cache_hit_tokens':0,'prompt_cache_miss_tokens':0});a['calls']+=1;a['charged']+=r['charged'] or 0
  for k in list(a)[2:]:a[k]+=u.get(k,0) or 0
  out['states'][r['state']]=out['states'].get(r['state'],0)+1
root=Path('/opt/monitor/geo-content/runtime/runs')
for p in root.glob('creation-*/rewrite_policy.json'):
 j=json.loads((p.parent/'job.json').read_text())
 if j.get('date')!='2026-10-29':continue
 out['policies'].append(json.loads(p.read_text()))
 if len(out['samples'])<3:
  for q in p.parent.rglob('request.json'):
   d=json.loads(q.read_text());msgs=d.get('messages',[])
   if not msgs:continue
   out['samples'].append({'path':str(q),'chars':sum(len(m.get('content','')) for m in msgs),'keys':list(d),'content_prefix':msgs[-1].get('content','')[:160]})
   if len(out['samples'])>=3:break
out['policies']=[json.loads(x) for x in set(json.dumps(v,sort_keys=True) for v in out['policies'])]
Path('/tmp/token-ledger29.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out,ensure_ascii=False,indent=2))
