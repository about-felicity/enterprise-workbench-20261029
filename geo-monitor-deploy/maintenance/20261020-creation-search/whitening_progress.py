import json,sqlite3,sys,time
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import studio,materials,runtime
pid='plan-6334cde812bd49549df6efd87a51e3b3';day='2026-10-20';root=studio.capture_root(pid)
p=studio.plan(pid);task=runtime.read(studio.day_path(pid,day));jobs=[]
for file in (runtime.BASE/'runs').glob('*/job.json'):
 j=runtime.read(file)
 if j.get('studio_plan_id')!=pid:continue
 r=file.parent
 counts={}
 for ticket_file in (r/'queue').glob('*/ticket.json'):
  t=runtime.read(ticket_file);key=t.get('stage','')+':'+t.get('state','');counts[key]=counts.get(key,0)+1
 d=runtime.read(r/'days'/day/'day.json')
 jobs.append({'id':j['job_id'],'question':j['question'],'preparation':j.get('preparation'),'material_counts':j.get('material_counts'),'control':runtime.read(r/'control.json'),'worker':runtime.read(r/'geo_worker.json'),'day':{k:d.get(k) for k in ('status','error','date')},'tickets':counts,'articles':[{'id':a.get('id'),'title':a.get('title'),'category':a.get('category'),'date':a.get('date')} for a in runtime.articles(r)]})
ledger=runtime.SHARED/'api/costs.sqlite';cost={}
if ledger.exists():
 with sqlite3.connect(ledger.as_uri()+'?mode=ro',uri=True) as db:
  if db.execute("select 1 from sqlite_master where name='studio_cost_scopes'").fetchone():
   value=db.execute('select count(*),coalesce(sum(c.charged),0),coalesce(sum(case when c.charged is null then c.reserved else 0 end),0) from costs c join studio_cost_scopes s on s.id=c.id where s.scope=?',(pid,)).fetchone();cost=dict(zip(('calls','charged_cny','reserved_cny'),value))
out={'at':time.time(),'plan_id':pid,'health':runtime.read(root/'health.json'),'progress':materials.progress(day,store_root=root),'daily':{k:task.get(k) for k in ('daily_task_id','status','paused','error','jobs')},'jobs':jobs,'cost':cost}
Path('/tmp/whitening-progress.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
print(json.dumps(out,ensure_ascii=False))
