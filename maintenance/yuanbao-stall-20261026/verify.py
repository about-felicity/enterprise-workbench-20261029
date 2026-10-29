"""Actual progress, receipt/PG and deployed-source verification; no model API."""
import hashlib,json,sqlite3,subprocess,time
from pathlib import Path
D=Path('/opt/monitor/geo-capture/maintenance/20261026-yuanbao-stall');R=Path('/home/user/redroid-yuanbao/batches/geo-panel-yuanbao-20261025-090004-5b28fa76')
run=lambda *a:subprocess.check_output(a,text=True,timeout=25).strip()
read=lambda p:json.loads(p.read_text())
health=read(R/'bridge_health.json');cases=[]
with sqlite3.connect(R.joinpath('tasks.sqlite').as_uri()+'?mode=ro',uri=True) as db:
 db.row_factory=sqlite3.Row
 for row in db.execute('select * from tasks where ordinal between 84 and 90'):
  value=dict(row);result=json.loads(value.get('result_json') or '{}')
  cases.append({'ordinal':value['ordinal'],'state':value['state'],'request_id':value['request_id'],'answer_id':value['answer_id'],
    'capture_retries':value['capture_retries'],'body_chars':len(result.get('body_markdown','')),'sources':len(result.get('sources',[])),
    'kind':result.get('native_answer_kind'),'rich_cards':len(result.get('rich_cards',[])),
    'events':dict(db.execute('select event,count(*) from events where task_id=? group by event',(value['task_id'],)))})
 m=read(Path('/tmp/yuanbao26-manifest.json'));mismatches=[]
 for r in m['files']:
  p=Path(r['server']);actual=hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
  if actual!=r['sha256']:mismatches.append({'file':str(p),'expected':r['sha256'],'actual':actual})
 sql="select coalesce(json_agg(t),'[]') from (select r.status,count(*) n from monitor_ingest_events e join monitor_runs r on r.model_id=e.model_id and r.run_id=e.run_id where e.record->>'batch_id'='"+R.name+"' group by r.status)t"
 pg=json.loads(run('docker','exec','monitor-postgres','psql','-U','monitor_app','-d','monitor','-Atc',sql))
text=read(D/'yuanbao-regression-summary.json') if (D/'yuanbao-regression-summary.json').exists() else {}
out={'at':time.time(),'health':health,'cases':cases,'postgres':pg,'mapping_files':len(m['files']),'mapping_mismatches':mismatches,
 'app_pid':run('docker','exec','yuanbao-hpe14-android13','pidof','com.tencent.hunyuan.app.chat'),
 'memory_events':run('docker','exec','yuanbao-hpe14-android13','cat','/sys/fs/cgroup/memory.events'),
 'service':run('systemctl','show','geo-native@'+R.name+'.service','-p','ActiveState','--value'),
 'nontext_receipts':len(list((R/'nontext-receipts').glob('*.json'))),'deployment':read(D/'deployed.json'),'regression':text}
original=next(c for c in cases if c['ordinal']==84)
out['original_recovered']=original['state'] in ('completed','completed_nontext')
(D/'verification-latest.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
print(json.dumps({'captured':health['captured'],'geo_processed':health['geo_processed'],'progress':health.get('progress'),'postgres':pg,'task84':original,'cases':cases,'app_pid':out['app_pid'],'service':out['service']},ensure_ascii=False))
