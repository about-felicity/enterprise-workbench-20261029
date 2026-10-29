import hashlib,json,sqlite3,subprocess,sys,time
from pathlib import Path
sys.path[:0]=['/home/user/redroid-yuanbao','/home/user/redroid-doubao/geo-batch-code','/home/user/redroid-doubao']
from delivery import verify_receipt
root=Path('/home/user/redroid-yuanbao/batches/geo-panel-yuanbao-20261022-090005-705819fb')
R=Path('/opt/monitor/geo-capture/maintenance/20261022-yuanbao-stall')
db=sqlite3.connect(root.joinpath('tasks.sqlite').as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
t=dict(db.execute('select * from tasks where ordinal=6').fetchone());result=json.loads(t.pop('result_json'))
assert t['state']=='completed' and result['request_id']=='6679b5f4b1f33941c35d64b60792068a'
clicks=db.execute("select count(*) from events where task_id=? and event='send_click_intent_committed'",(t['task_id'],)).fetchone()[0]
assert clicks==1 and t['capture_retries']==0
assert not db.execute('select 1 from failed_attempts where task_id=?',(t['task_id'],)).fetchone()
receipts=[]
for p in (root/'outbox').glob('*.json'):
 item=json.loads(p.read_text())
 if item['record'].get('capture_result',{}).get('task_id')!=t['task_id']:continue
 receipt=json.loads((root/'receipts'/p.name).read_text());verify_receipt(receipt,item)
 upstream=json.loads((Path('/opt/monitor/runtime/lan_result_receiver/yuanbao/done')/p.name).read_text());assert receipt==upstream
 receipts.append({'stored_run_id':receipt['stored_run_id'],'receiver_id':receipt['request_id']})
assert len(receipts)==1
sql="select coalesce(json_agg(t),'[]') from (select r.run_id,r.day,r.payload->>'answer_raw' answer_raw,r.payload->>'body_capture_complete' body_complete,r.payload->>'source_capture_complete' sources_complete,e.record->>'batch_id' batch,e.record->'capture_result'->>'wire_question' original_question,e.record->'capture_result'->'sources' sources from monitor_runs r join monitor_ingest_events e on r.model_id=e.model_id and r.run_id=e.run_id where r.model_id='yuanbao' and r.run_id='"+receipts[0]['stored_run_id']+"')t"
pg=json.loads(subprocess.check_output(['docker','exec','monitor-postgres','psql','-U','monitor_app','-d','monitor','-Atc',sql],text=True));assert len(pg)==1
assert pg[0]['answer_raw']==result['body_markdown'] and pg[0]['original_question']==t['question']
assert pg[0]['batch']==t['batch'] and pg[0]['sources']==result['sources']
assert pg[0]['body_complete']=='true' and pg[0]['sources_complete']=='true'
pg[0]['body_sha256']=hashlib.sha256(pg[0].pop('answer_raw').encode()).hexdigest();pg[0]['source_count']=len(pg[0].pop('sources'))
health=json.loads((root/'bridge_health.json').read_text())
counts=dict(db.execute('select state,count(*) from tasks group by state').fetchall())
out={'at':time.time(),'original_ordinal':6,'original_send_clicks':clicks,'capture_retries':t['capture_retries'],
 'original_trace':result['request_id'],'body_length':len(result['body_markdown']),'source_count':len(result['sources']),
 'receipt_pairs':receipts,'pg':pg,'tasks':counts,'current':{k:health.get(k) for k in ('batch','captured','geo_processed','status','tasks','progress','delivery_errors')}}
(R/'verification.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out,ensure_ascii=False))
