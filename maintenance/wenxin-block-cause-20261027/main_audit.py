import json,sqlite3,datetime,hashlib
from pathlib import Path
from urllib.parse import urlsplit
zone=datetime.timezone(datetime.timedelta(hours=8))
def stamp(t):return datetime.datetime.fromtimestamp(float(t),zone).isoformat()
root=Path('/opt/monitor/geo-capture/batches/geo-panel-wenxin-card-20261026-112314-9a29529d/collector')
with sqlite3.connect((root/'tasks.sqlite').as_uri()+'?mode=ro',uri=True) as db:
 db.row_factory=sqlite3.Row
 attempts=[dict(r) for r in db.execute('select kind,error,epoch from search_recovery_attempts order by epoch')]
 for a in attempts:a['time']=stamp(a.pop('epoch'))
 print(json.dumps({'main_geo_attempts':attempts},ensure_ascii=False))
snapshots=[]
for p in root.glob('recovery_evidence/*/*/snapshot.json'):
 v=json.loads(p.read_text());snapshots.append({'time':stamp(int(p.parent.name)/1e9),'host':urlsplit(v.get('url','')).hostname,'title':v.get('title'),'text':v.get('pageText','')[:250],'screenshot':str(p.with_name('page.png')) if p.with_name('page.png').exists() else None})
print(json.dumps({'evidence':sorted(snapshots,key=lambda v:v['time'])},ensure_ascii=False))
print(json.dumps({'profile_schema':7,'worker_state_is_durable':True}))
