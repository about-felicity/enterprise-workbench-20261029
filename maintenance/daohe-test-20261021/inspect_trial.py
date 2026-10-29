import sys,json,sqlite3,time
from pathlib import Path
from collections import Counter
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime,studio,materials
M=Path('/opt/monitor/geo-capture/maintenance/20261021-daohe-test');s=runtime.read(M/'task.json');task=runtime.read(studio.day_path(s['plan_id'],s['date']));jobs=[]
for jid in task.get('jobs',{}).values():
 root=runtime.job_root(jid);job=runtime.read(root/'job.json');day=runtime.read(root/'days'/s['date']/'day.json');tickets=[runtime.read(p) for p in (root/'queue').glob('*/ticket.json')]
 calls=[]
 for p in (root/'api/runs').glob('**/api_state.json'):
  v=runtime.read(p)
  if v.get('state') not in {'RESPONDED'}:calls.append({'path':str(p),'state':v.get('state'),'error_type':v.get('error_type'),'status':v.get('http_status')})
 jobs.append({'job_id':jid,'preparation':job.get('preparation'),'day':day,'control':runtime.read(root/'control.json'),'worker':runtime.read(root/'geo_worker.json'),'active':{k:v for k,v in runtime.read(root/'api/active.json').items() if k in {'state','ticket','stage'}},'tickets':dict(Counter(t.get('stage','')+':'+t.get('state','') for t in tickets)),'allocation':runtime.read(root/'days'/s['date']/'article_allocation.json'),'articles':[{'id':a['id'],'title':a['title'],'quality_status':a['quality_status'],'issues':a['quality_issues']} for a in runtime.articles(root)],'incomplete_calls':calls})
with sqlite3.connect('file:/home/user/geo-editorial/runtime-api/api/costs.sqlite?mode=ro',uri=True) as db:
 try:fees=db.execute('select coalesce(sum(c.charged),0),coalesce(sum(case when c.charged is null then c.reserved else 0 end),0) from costs c join studio_cost_scopes s on c.id=s.id where s.scope=?',(s['plan_id'],)).fetchone()
 except sqlite3.OperationalError:fees=(0,0)
result={'at':time.time(),'capture':[v for v in materials.progress(s['date'],store_root=Path(s['capture_root'])) if v['id'] in {'baidu_ai','wenxin_card'}],'task_status':task.get('status'),'task_error':task.get('error'),'jobs':jobs,'test_charged':fees[0],'test_reserved':fees[1],'shared_cap':runtime.pipeline_control.settings(runtime.SHARED)['daily_budget_cny']}
(M/'latest-trial.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
if '--compact' in sys.argv:
 result['jobs']=[{**{k:v for k,v in j.items() if k not in {'allocation','day','articles','control','worker'}},'paused':j['control'].get('paused'),'reason':j['control'].get('reason'),'day':{k:v for k,v in j['day'].items() if k in {'status','planned_articles','accepted_articles'}},'allocated':{k:len(v) for k,v in j['allocation'].get('selected',{}).items()},'approved':len(j['articles']),'worker':j['worker']} for j in jobs]
print(json.dumps(result,ensure_ascii=False))
