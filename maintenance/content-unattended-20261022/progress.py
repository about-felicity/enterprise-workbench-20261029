import sys,json,sqlite3,time
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
D=Path('/opt/monitor/geo-capture/maintenance/20261022-content-unattended');seed=runtime.read(D/'trial-requeued.json');items=[];jobs=[]
for identity in sorted({r['job'] for r in seed['articles']}):
 root=runtime.job_root(identity);tickets=[runtime.read(p) for p in (root/'queue').glob('*/ticket.json')]
 release=[t for t in tickets if t.get('meta',{}).get('workflow_release')==seed['release']]
 for a in [r for r in seed['articles'] if r['job']==identity]:
  matching=[t for t in release if t['meta'].get('category')==a['category'] and t['meta'].get('number')==a['number']]
  latest=max(matching,key=lambda t:t.get('created_at',''))
  folder=root/'approved'/'2026-10-21'/a['category']/f"{a['number']:02d}"
  items.append({**a,'latest':{k:latest.get(k) for k in ('stage','state','error','id')},'approved':(folder/'receipt.json').exists()})
 jobs.append({'job':identity,'control':runtime.read(root/'control.json'),'active':runtime.read(root/'api/active.json'),'worker':runtime.read(root/'geo_worker.json'),
    'pending':sum(t['state'] in {'pending','claimed'} for t in release),'approved':sum(a['approved'] for a in items if a['job']==identity)})
with sqlite3.connect('file:/home/user/geo-editorial/runtime-api/api/costs.sqlite?mode=ro',uri=True) as db:
 costs=db.execute("select c.date,c.category,c.article,c.stage,count(*),sum(c.charged),sum(case when c.charged is null then c.reserved else 0 end) from costs c join studio_cost_scopes s on c.id=s.id where s.scope='plan-33e7bfca8bb6497da10b28f0444a693b' group by c.date,c.category,c.article,c.stage").fetchall()
out={'at':time.time(),'articles':items,'jobs':jobs,'costs':costs}
(D/'progress.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out,ensure_ascii=False))
