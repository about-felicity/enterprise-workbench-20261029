"""Read-only current acceptance, ledger, paused controls and remaining work."""
import sys,json,sqlite3,time,hashlib
from pathlib import Path
from collections import Counter
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime,observation as o
from datetime import datetime
root=runtime.BASE/'runs/creation-1792556219-bbc55e13';M=Path('/opt/monitor/geo-capture/maintenance/20261021-article-logic')
now=datetime.now(o.ZONE);current=o.collect(now);baseline=o.read(o.OUTPUT/'baseline.json');articles=runtime.articles(root)
repairs=runtime.read(M/'repairs.json').get('articles',[])
report={'at':now.isoformat(),'original_fourteen_audit':dict(Counter(x['state'] for x in runtime.read(M/'audit.json')['articles'])),'current_mask_counts':dict(Counter(a['quality_status'] for a in articles)),'current_mask_articles':[{k:a[k] for k in ('id','title','quality_status','quality_issues')} for a in articles],'repair_states':dict(Counter(a['state'] for a in repairs)),'repair_results':repairs,'ledger_today':current['ledger'],'unknown_request_ids':current['unknown_request_ids'],'unknown_ids_unchanged':current['unknown_request_ids']==baseline['unknown_request_ids'],'protected_pauses_unchanged':all(current['protected_controls'].get(p)==h for p,h in baseline['protected_controls'].items()),'observation_assessment':o.evaluate(current,baseline,now),'budget_limits':runtime.read(root/'job.json').get('budget_limits')}
with sqlite3.connect('file:/home/user/geo-editorial/runtime-api/api/costs.sqlite?mode=ro',uri=True) as db:
 ids=set()
 for directory in (runtime.BASE/'logic-review/20261021-mask',runtime.BASE/'logic-revision/20261021-mask04',runtime.BASE/'quality-repair/20261021-mask-logic'):
  for p in directory.rglob('api_state.json'):
   identity=runtime.read(p).get('reservation')
   if identity:ids.add(identity)
 report['logic_change_settled_cny']=sum((db.execute('select coalesce(charged,0) from costs where id=?',(identity,)).fetchone() or [0])[0] for identity in ids)
(M/'current-summary.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False))
