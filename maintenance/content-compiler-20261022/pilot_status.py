import sys,json,time,sqlite3
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
D=Path('/opt/monitor/geo-capture/maintenance/20261022-content-compiler');seed=runtime.read(D/'pilots-published.json');rows=[]
for item in seed.get('articles',[]):
 root=runtime.job_root(item['job']);tickets=[runtime.read(p) for p in (root/'queue').glob('*/ticket.json')]
 own=[j for j in tickets if j['meta'].get('compiler_pilot_release')=='practical-v1' and (j['meta'].get('category'),j['meta'].get('number'))==(item['category'],item['number'])]
 latest=max(own,key=lambda j:j['created_at']);run=root/'api/runs'/latest.get('execution',{}).get('run_id','missing')
 row={**item,'latest':{k:latest.get(k) for k in ('id','stage','state','error')},'call':runtime.read(run/'call/api_state.json').get('state'),
      'logic':runtime.read(run/'logic-call/api_state.json').get('state'),'approved':(root/'approved/2026-10-21'/item['category']/f"{item['number']:02d}"/'receipt.json').is_file()}
 rows.append(row)
with sqlite3.connect('file:/home/user/geo-editorial/runtime-api/api/costs.sqlite?mode=ro',uri=True) as db:
 costs=db.execute("select c.date,sum(c.charged),sum(case when c.charged is null then c.reserved else 0 end) from costs c join studio_cost_scopes s on c.id=s.id where s.scope=? group by c.date",('plan-33e7bfca8bb6497da10b28f0444a693b',)).fetchall()
 unknown=sorted(r[0] for r in db.execute('select id from costs where charged is null'))
out={'at':time.time(),'articles':rows,'costs':costs,'unknown_count':len(unknown),'unknown_ids':unknown}
atomic=__import__('geo_source_cards.runtime',fromlist=['atomic_json']).atomic_json
atomic(D/'pilot-status.json',out);print(json.dumps(out,ensure_ascii=False))
