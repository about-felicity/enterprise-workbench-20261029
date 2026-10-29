import json,sqlite3,time
from collections import Counter
from pathlib import Path
R=Path('/opt/monitor/geo-content/runtime/quality-repair/20261021-consumer-voice')
items=json.loads((R/'inventory.json').read_text())['articles'];rows=[]
for item in items:
 p=R/item['key']/'status.json';s=json.loads(p.read_text()) if p.exists() else {'state':'pending'}
 rows.append({'key':item['key'],'root':item['root'],'id':item['id'],**s})
with sqlite3.connect('file:/home/user/geo-editorial/runtime-api/api/costs.sqlite?mode=ro',uri=True) as db:
 costs=db.execute('select date,count(*),sum(charged),sum(case when charged is null then 1 else 0 end) from costs group by date order by date desc limit 2').fetchall()
report={'at':time.time(),'states':dict(Counter(r['state'] for r in rows)),'daily_ledger':costs,'articles':rows}
Path('/tmp/creation-quality-progress.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps({k:v for k,v in report.items() if k!='articles'},ensure_ascii=False));print(json.dumps([{'id':r['id'],'state':r['state'],'reason':r.get('reason')} for r in rows if r['state'] in {'unknown_request','budget_blocked','needs_attention'}][-5:],ensure_ascii=False))
