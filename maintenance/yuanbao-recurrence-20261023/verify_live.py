"""Actual progress, receipt/PG and deployed-source verification; no model API."""
import hashlib,json,sqlite3,subprocess,time
from pathlib import Path
D=Path('/opt/monitor/geo-capture/maintenance/20261023-yuanbao-recurrence');R=Path('/home/user/redroid-yuanbao/batches/geo-panel-yuanbao-20261023-090004-d6b66215')
run=lambda *a:subprocess.check_output(a,text=True,timeout=25).strip()
read=lambda p:json.loads(p.read_text())
health=read(R/'bridge_health.json');cases=[]
with sqlite3.connect(R.joinpath('tasks.sqlite').as_uri()+'?mode=ro',uri=True) as db:
 db.row_factory=sqlite3.Row
 for row in db.execute('select * from tasks where ordinal between 125 and 136'):
  value=dict(row);result=json.loads(value.get('result_json') or '{}')
  cases.append({'ordinal':value['ordinal'],'state':value['state'],'request_id':value['request_id'],'answer_id':value['answer_id'],
    'capture_retries':value['capture_retries'],'body_chars':len(result.get('body_markdown','')),'sources':len(result.get('sources',[])),
    'kind':result.get('native_answer_kind'),'rich_cards':len(result.get('rich_cards',[])),
    'events':dict(db.execute('select event,count(*) from events where task_id=? group by event',(value['task_id'],)))})
 m=read(Path('/tmp/yuanbao-recurrence-mapping.json'));mismatches=[]
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
 'nontext_receipts':len(list((R/'nontext-receipts').glob('*.json'))),'deployment':read(D/'deployment.json'),'regression':text}
original=next(c for c in cases if c['ordinal']==125)
assert original['state']=='completed_nontext' and original['kind']=='video_only' and original['events']['send_click_intent_committed']==1 and original['capture_retries']==0
assert out['app_pid']=='4403' and not mismatches and not health['delivery_errors']
assert health['nontext_observations']==health['nontext_processed']==1 and health['nontext_pending']==0
assert sum(r['n'] for r in pg if r['status']=='success')==health['geo_processed']
(D/('verification-'+str(time.time_ns())+'.json')).write_text(json.dumps(out,ensure_ascii=False,indent=2))
(D/'verification-latest.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
print(json.dumps({'at':out['at'],'captured':health['captured'],'geo_processed':health['geo_processed'],'nontext_processed':health['nontext_processed'],
 'planned':health['planned'],'progress':health.get('progress'),'postgres':pg,'mapping_files':len(m['files']),'mismatches':mismatches,
 'task125':original,'app_pid':out['app_pid'],'service':out['service']},ensure_ascii=False))
