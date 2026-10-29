import json,sqlite3,datetime
from pathlib import Path
from urllib.parse import urlsplit
zone=datetime.timezone(datetime.timedelta(hours=8))
def stamp(t):return datetime.datetime.fromtimestamp(float(t),zone).isoformat() if t else None
def read(p):
 try:return json.loads(p.read_text())
 except (FileNotFoundError,ValueError):return {}
base=Path('/opt/monitor/geo-content/studio/capture')
for pid in ['plan-53eaaebbc537459f81d55a3f8a43f969','plan-195abff2413a421dac589112f24c7596']:
 root=base/pid/'days/2026-10-26/wenxin_card/collector'
 with sqlite3.connect(root.joinpath('tasks.sqlite').as_uri()+'?mode=ro',uri=True) as db:
  db.row_factory=sqlite3.Row
  attempts=[dict(r) for r in db.execute('select task_id,kind,error,epoch from search_recovery_attempts order by epoch')]
  for r in attempts:r['time']=stamp(r.pop('epoch'))
  states=[dict(r) for r in db.execute('select state,count(*) as n from captures group by state')]
 print(json.dumps({'plan':pid,'attempts':attempts,'states':states},ensure_ascii=False))
 snapshots=[]
 for p in root.glob('recovery_evidence/*/*/snapshot.json'):
  v=read(p);snapshots.append({'time':stamp(int(p.parent.name)/1e9),'host':urlsplit(v.get('url','')).hostname,'path':urlsplit(v.get('url','')).path,'title':v.get('title'),'text':v.get('pageText','')[:300],'evidence':str(p)})
 print(json.dumps({'evidence':sorted(snapshots,key=lambda v:v['time'])},ensure_ascii=False))
geo=Path('/opt/monitor/geo-capture')
print(json.dumps({'geo_profile':read(geo/'profiles/search/wenxin_card/migration.json')},ensure_ascii=False))
rows=[]
for p in (geo/'batches').glob('*/manifest.json'):
 v=read(p)
 if v.get('model')=='wenxin_card':
  h=read(p.parent/'bridge_health.json');rows.append({'batch':p.parent.name,'created':stamp(v.get('created_at')),'status':h.get('status'),'tasks':h.get('tasks'),'recovery':read(p.parent/'collector/search_recovery.json')})
print(json.dumps({'geo_recent':sorted(rows,key=lambda v:v['created'] or '')[-4:]},ensure_ascii=False))
