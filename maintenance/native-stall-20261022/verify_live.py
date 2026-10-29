"""Read-only live progress, original request evidence and database receipts."""
import json,sqlite3,subprocess,time,hashlib
from pathlib import Path
D=Path('/opt/monitor/geo-capture/maintenance/20261022-native-stall')
old=json.loads((D/'before.json').read_text());reports=[]
read=lambda p:json.loads(p.read_text()) if p.is_file() else {}
for before in old['batches']:
 root=Path(before['root']);model=before['model'];health=read(root/'bridge_health.json')
 with sqlite3.connect(root.joinpath('tasks.sqlite').as_uri()+'?mode=ro',uri=True) as db:
  db.row_factory=sqlite3.Row
  counts=dict(db.execute('select state,count(*) from tasks group by state'))
  current=db.execute("select ordinal,state,request_id,capture_retries,error from tasks where state not in ('completed','completed_nontext') order by ordinal limit 1").fetchone()
  r={'model':model,'batch':before['batch'],'counts':counts,'health':{k:health.get(k) for k in ('status','captured','geo_processed','delivery_errors','progress','time','memory')},'current':dict(current) if current else None,'pause':read(root/'maintenance_pause.json')}
  r['recovered_cases']=[]
  for ordinal in ([22,26] if model=='doubao1' else [102,112] if model=='yuanbao' else []):
   row=db.execute('select * from tasks where ordinal=?',(ordinal,)).fetchone();value=json.loads(row['result_json'] or '{}')
   r['recovered_cases'].append({'ordinal':ordinal,'state':row['state'],'request_id':row['request_id'],'body_length':len(value.get('body_markdown','')),'sources':len(value.get('sources',[])),
       'conversation_id':value.get('conversation_id'),'first_user_turn':value.get('first_user_turn'),'continuation_request_id':value.get('permission_continuation',{}).get('continuation_request_id'),
       'native_request_confirmed':value.get('native_request_confirmed'),'capture_retries':row['capture_retries'],
       'events':{v['event']:v['n'] for v in db.execute('select event,count(*) n from events where task_id=? group by event',(row['task_id'],))}})
  if before.get('task'):
   tid=before['task']['task_id'];task=dict(db.execute('select * from tasks where task_id=?',(tid,)).fetchone());result=json.loads(task.pop('result_json') or '{}')
   r['original']={k:task.get(k) for k in ('task_id','ordinal','state','request_id','capture_retries','error')}
   r['original'].update(body_length=len(result.get('body_markdown','')),body_sha256=hashlib.sha256(result.get('body_markdown','').encode()).hexdigest(),sources=len(result.get('sources',[])),conversation_id=result.get('conversation_id'),missing_titles=[{k:s.get(k) for k in ('title','original_title','title_missing','title_origin','url')} for s in result.get('sources',[]) if s.get('title_missing')])
   r['original']['events']=[dict(v) for v in db.execute('select event,time,detail from events where task_id=? order by id',(tid,))]
   r['original']['draft_recovery']=read(root/(tid+'-attempt-0.draft-submit-recovery.json'))
   if r['original']['draft_recovery'].get('proof'):r['original']['draft_recovery']['proof']='<two baseline comparisons persisted>'
   envelopes=[]
   for p in (root/'outbox').glob('*.json'):
    item=read(p);record=item.get('record',{});payload=item.get('payload',{})
    if record.get('capture_task_id')==tid or payload.get('native_result',{}).get('task_id')==tid:
     receipt=read(root/'receipts'/p.name)
     envelopes.append({'request_id':item['request_id'],'receipt_present':bool(receipt),'run_id':receipt.get('stored_run_id') or receipt.get('save',{}).get('run_id'),'analysis':{k:receipt.get('analysis',{}).get(k) for k in ('answer_length','source_count','answer_present','source_capture_complete','body_capture_complete','quarantined')}})
   r['original']['receipts']=envelopes
 r['service']=subprocess.check_output(['systemctl','show','geo-native@'+before['batch']+'.service','-p','ActiveState','--value'],text=True).strip()
 reports.append(r)
batches=','.join("'"+r['batch']+"'" for r in reports)
sql="select coalesce(json_agg(t),'[]') from (select e.record->>'batch_id' batch,count(*) n,count(*) filter(where r.status='success') success from monitor_ingest_events e join monitor_runs r on r.model_id=e.model_id and r.run_id=e.run_id where e.record->>'batch_id' in ("+batches+") group by 1)t"
pg=json.loads(subprocess.check_output(['docker','exec','monitor-postgres','psql','-U','monitor_app','-d','monitor','-Atc',sql],text=True))
out={'at':time.time(),'batches':reports,'postgres':pg};(D/'verification.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
for r in reports:
 if r.get('original'):
  events=r['original'].pop('events');r['original']['event_counts']={k:sum(e['event']==k for e in events) for k in sorted({e['event'] for e in events})}
print(json.dumps(out,ensure_ascii=False))
