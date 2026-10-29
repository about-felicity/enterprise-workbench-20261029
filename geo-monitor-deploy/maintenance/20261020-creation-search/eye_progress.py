import json,os,sqlite3,time
from pathlib import Path
base=Path('/opt/monitor/geo-content');pid='plan-c32eb3793b6846e39f72cb25f9e06d1c';day='2026-10-20';root=base/'studio/capture'/pid
def read(p):return json.loads(p.read_text()) if p.exists() else {}
progress={}
for model in ('baidu_ai','wenxin_card'):
 lane=root/'days'/day/model;dbpath=lane/'collector/tasks.sqlite';counts={}
 if dbpath.exists():
  with sqlite3.connect(dbpath.as_uri()+'?mode=ro',uri=True) as db:counts=dict(db.execute('select state,count(*) from captures group by state'))
 progress[model]={'counts':counts,'blocked':read(lane.parent/('blocked-'+model+'.json'))}
jobs=[]
for f in (base/'runtime/runs').glob('*/job.json'):
 j=read(f)
 if j.get('studio_plan_id')!=pid:continue
 r=f.parent;counts={}
 for p in (r/'queue').glob('*/ticket.json'):
  t=read(p);key=t.get('stage','')+':'+t.get('state','');counts[key]=counts.get(key,0)+1
 receipts=list((r/'approved'/day).glob('*/*/receipt.json'))
 jobs.append({'id':j['job_id'],'preparation':j.get('preparation'),'material_counts':j.get('material_counts'),'preparation_progress':read(r/'material_preparation.json'),'preparation_retry':read(r/'preparation_retry.json'),'control':read(r/'control.json'),'worker':read(r/'geo_worker.json'),'day':read(r/'days'/day/'day.json'),'allocation':read(r/'days'/day/'article_allocation.json'),'tickets':counts,'approved':len(receipts)})
cost={};ledger=Path('/home/user/geo-editorial/runtime-api/api/costs.sqlite')
with sqlite3.connect(ledger.as_uri()+'?mode=ro',uri=True) as db:
 v=db.execute('select count(*),coalesce(sum(c.charged),0),coalesce(sum(case when c.charged is null then c.reserved else 0 end),0) from costs c join studio_cost_scopes s on s.id=c.id where s.scope=?',(pid,)).fetchone();cost=dict(zip(('calls','charged_cny','reserved_cny'),v))
processes=[]
uptime=float(Path('/proc/uptime').read_text().split()[0]);hz=os.sysconf('SC_CLK_TCK')
for path in Path('/proc').glob('[0-9]*/cmdline'):
 try:
  cmd=path.read_bytes().decode().split('\0')
  if 'geo_source_cards.cli' not in cmd or not any(str(root) in arg for arg in cmd):continue
  stat=(path.parent/'stat').read_text().split(') ',1)[1].split()
  processes.append({'pid':int(path.parent.name),'elapsed_seconds':round(uptime-int(stat[19])/hz),'model':cmd[cmd.index('--model')+1]})
 except (OSError,ValueError,IndexError):continue
out={'at':time.time(),'plan_id':pid,'health':read(root/'health.json'),'capture':progress,'jobs':jobs,'cost':cost,'collector_processes':processes}
Path('/tmp/eye-daily-progress.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
for j in out['jobs']:
 if j['allocation'].get('selected'):j['allocation']['selected']={k:len(v) for k,v in j['allocation']['selected'].items()}
print(json.dumps(out,ensure_ascii=False))
