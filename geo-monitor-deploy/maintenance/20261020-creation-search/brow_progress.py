import json, sys, sqlite3, time, urllib.request
from pathlib import Path
sys.path[:0] = ['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime,studio,materials
task = runtime.read(Path('/opt/monitor/geo-capture/maintenance/20261020-brow-daily/task.json'))
pid = task['plan_id']; day = task['start_date']; root = studio.capture_root(pid)
capture = {}
for model in studio.plan(pid)['channels']:
    lane = root/'days'/day/model
    p = lane/'collector/tasks.sqlite'
    counts = {}
    if p.exists():
        with sqlite3.connect(p.as_uri()+'?mode=ro',uri=True) as db:
            counts = dict(db.execute('select state,count(*) from captures group by state'))
    recovery=next((v.get('recovery',{}) for v in materials.progress(day,store_root=root) if v['id']==model),{})
    capture[model] = {'states': counts, 'blocked':runtime.read(lane.parent/('blocked-'+model+'.json')), 'recovery':recovery}
jobs = []
for p in (runtime.BASE/'runs').glob('*/job.json'):
    j = runtime.read(p)
    if j.get('studio_plan_id') != pid: continue
    r=p.parent; tickets={}
    for f in (r/'queue').glob('*/ticket.json'):
        t=runtime.read(f); key=t.get('stage','')+':'+t.get('state','');tickets[key]=tickets.get(key,0)+1
    allocation=runtime.read(r/'days'/day/'article_allocation.json')
    if allocation.get('selected'):allocation['selected']={k:len(v) for k,v in allocation['selected'].items()}
    jobs.append({'id':j['job_id'],'preparation':j.get('preparation'),'preparation_progress':runtime.read(r/'material_preparation.json'),'day':runtime.read(r/'days'/day/'day.json'),'control':runtime.read(r/'control.json'),'worker':runtime.read(r/'geo_worker.json'),'tickets':tickets,'allocation':allocation,'approved':len(runtime.articles(r))})
with sqlite3.connect('file:/home/user/geo-editorial/runtime-api/api/costs.sqlite?mode=ro',uri=True) as db:
    cost=db.execute('select count(*),coalesce(sum(c.charged),0),coalesce(sum(case when c.charged is null then c.reserved else 0 end),0) from costs c join studio_cost_scopes s on s.id=c.id where s.scope=?',(pid,)).fetchone()
out={'at':time.time(),'plan_id':pid,'capture':capture,'jobs':jobs,'cost':dict(zip(('calls','charged_cny','reserved_cny'),cost)),'health':runtime.read(root/'health.json')}
Path('/tmp/brow-daily-progress.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
print(json.dumps(out,ensure_ascii=False))
