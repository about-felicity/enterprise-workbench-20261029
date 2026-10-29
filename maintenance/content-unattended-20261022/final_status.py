"""Evidence snapshot; no requests, queue writes or budget changes."""
import sys,json,time,sqlite3,subprocess
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
D=Path('/opt/monitor/geo-capture/maintenance/20261022-content-unattended');seed=runtime.read(D/'trial-requeued.json');rows=[];jobs=[]
for identity in sorted({r['job'] for r in seed['articles']}):
 root=runtime.job_root(identity);tickets=[runtime.read(p) for p in (root/'queue').glob('*/ticket.json')]
 for a in [r for r in seed['articles'] if r['job']==identity]:
  matching=[t for t in tickets if t['meta'].get('category')==a['category'] and t['meta'].get('number')==a['number']]
  latest=max(matching,key=lambda t:t.get('created_at',''));folder=root/'approved/2026-10-21'/a['category']/f"{a['number']:02d}"
  rows.append({k:a[k] for k in ('job','category','number')}|{'state':latest['state'],'stage':latest['stage'],'error':latest.get('error'),
              'approved':(folder/'receipt.json').is_file(),'ticket':latest['id']})
 jobs.append({'job':identity,'control':runtime.read(root/'control.json'),'worker':runtime.read(root/'geo_worker.json'),
              'active':runtime.read(root/'api/active.json'),'budget_limits':runtime.read(root/'job.json').get('budget_limits')})
with sqlite3.connect('file:/home/user/geo-editorial/runtime-api/api/costs.sqlite?mode=ro',uri=True) as db:
 costs=db.execute("select c.date,sum(c.charged),sum(case when c.charged is null then c.reserved else 0 end) from costs c join studio_cost_scopes s on c.id=s.id where s.scope=? group by c.date",('plan-33e7bfca8bb6497da10b28f0444a693b',)).fetchall()
 unknown=sorted(r[0] for r in db.execute('select id from costs where charged is null'))
original=seed['original_unknown_ids']
out={'at':time.time(),'articles':rows,'approved':sum(r['approved'] for r in rows),'jobs':jobs,'costs_by_charge_date':costs,
     'original_unknown_ids_unchanged':unknown==original,'original_unknown_count':len(original),
     'services':subprocess.run(['systemctl','is-active','geo-content-worker','geo-content-api','geo-creation-studio'],capture_output=True,text=True).stdout.splitlines(),
     'deployment':{k:v for k,v in runtime.read(D/'deployment.json').items() if k!='source_files'},
     'recovery_mapping_files':197,'budget_changed':False,'unattended_cross_day_verified':False}
(D/'final-status.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
print(json.dumps({k:v for k,v in out.items() if k not in ('articles','jobs')},ensure_ascii=False))
