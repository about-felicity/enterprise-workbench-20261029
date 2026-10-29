"""Read-only queue, source hashes, native identity and actual ingestion evidence."""
import hashlib,json,sqlite3,subprocess,time
from pathlib import Path
D=Path('/opt/monitor/geo-capture/maintenance/20261023-yuanbao-unbound')
R=Path('/home/user/redroid-yuanbao/batches/geo-panel-yuanbao-20261023-090004-d6b66215')
read=lambda p:json.loads(p.read_text()) if p.exists() else {}
manifest=read(Path('/tmp/yuanbao-final-mapping.json'));mismatches=[]
for row in manifest['files']:
 p=Path(row['server']);actual=hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
 if actual!=row['sha256']:mismatches.append({'server':str(p),'expected':row['sha256'],'actual':actual})
with sqlite3.connect(R.joinpath('tasks.sqlite').as_uri()+'?mode=ro',uri=True) as db:
 db.row_factory=sqlite3.Row
 counts=dict(db.execute('select state,count(*) from tasks group by state'));cases=[]
 for row in db.execute('select * from tasks where ordinal between 13 and 25'):
  result=json.loads(row['result_json'] or '{}')
  cases.append({'ordinal':row['ordinal'],'state':row['state'],'request_id':row['request_id'],'capture_retries':row['capture_retries'],
   'body_chars':len(result.get('body_markdown','')),'sources':len(result.get('sources',[])),
   'conversation_id':result.get('conversation_id'),'body_sha256':hashlib.sha256(result.get('body_markdown','').encode()).hexdigest(),
   'events':dict(db.execute('select event,count(*) from events where task_id=? group by event',(row['task_id'],)))})
sql="select coalesce(json_agg(t),'[]') from (select e.record->>'batch_id' batch,count(*) n,count(*) filter(where r.status='success') success from monitor_ingest_events e join monitor_runs r on r.model_id=e.model_id and r.run_id=e.run_id where e.record->>'batch_id'='"+R.name+"' group by 1)t"
pg=json.loads(subprocess.check_output(['docker','exec','monitor-postgres','psql','-U','monitor_app','-d','monitor','-Atc',sql],text=True,timeout=15))
services={unit:subprocess.check_output(['systemctl','show',unit,'-p','ActiveState','--value'],text=True).strip() for unit in ['geo-native@'+R.name+'.service','geo-daily-control.service']}
out={'at':time.time(),'health':read(R/'bridge_health.json'),'counts':counts,'cases':cases,'postgres':pg,'services':services,
 'recovery_mapping':{'files':len(manifest['files']),'mismatches':mismatches},'guard_deployment':read(D/'guard-deployment.json'),'lightweight_live':read(D/'lightweight-live.json')}
(D/'verification-final.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
print(json.dumps({**out,'cases':cases[:2]+[c for c in cases[2:] if c['state']=='completed']},ensure_ascii=False))
