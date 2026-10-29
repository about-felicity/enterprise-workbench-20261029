import hashlib,json,sqlite3,subprocess,sys,time
from pathlib import Path
sys.path[:0]=['/home/user/redroid-doubao/geo-batch-code','/home/user/redroid-doubao']
from question_only_delivery import DoubaoDelivery
R=Path('/home/user/redroid-doubao/batches/geo-panel-doubao1-20261024-090002-8e65185c');D=Path('/opt/monitor/geo-capture/maintenance/20261024-doubao-stall')
db=sqlite3.connect('file:'+str(R/'tasks.sqlite')+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
t=dict(db.execute('select * from tasks where ordinal=53').fetchone());r=json.loads(t.pop('result_json') or '{}')
if t['state']!='completed':print(json.dumps({'ready':False,'state':t['state']}));raise SystemExit(2)
events=dict(db.execute('select event,count(*) from events where task_id=? group by event',(t['task_id'],)))
assert events['native_existing_draft_submit_intent']==events['native_draft_trailing_newline_normalize_intent']==1
assert t['capture_retries']==0 and r['first_user_turn'] and r['native_request_confirmed']
assert r['wire_question']==t['question'] and not r['wire_question'].endswith('\n')
receipt_ids=[]
for p in (R/'outbox').glob('*.json'):
 item=json.loads(p.read_text())
 if item.get('payload',{}).get('native_result',{}).get('task_id')!=t['task_id']:continue
 receipt=json.loads((R/'receipts'/p.name).read_text());DoubaoDelivery.verify(None,receipt,item);receipt_ids.append(receipt['save']['run_id'])
assert len(receipt_ids)==1
sql="select json_agg(t) from (select run_id,day,payload->>'answer' answer,payload->>'source_capture_complete' complete from monitor_runs where model_id='doubao' and run_id='"+receipt_ids[0]+"')t"
pg=json.loads(subprocess.check_output(['docker','exec','monitor-postgres','psql','-U','monitor_app','-d','monitor','-Atc',sql],text=True));assert len(pg)==1
assert pg[0]['answer']==r['body_markdown'].strip() and pg[0]['complete']=='true';pg[0]['answer_sha256']=hashlib.sha256(pg[0].pop('answer').encode()).hexdigest()
binding=json.loads((R/(t['task_id']+'-attempt-0.binding.json')).read_text())
with sqlite3.connect('file:'+binding['database']+'?mode=ro',uri=True) as native:
 native_count=native.execute('select count(*) from im_message where conversation_id=? and user_type=1',(binding['conversation_id'],)).fetchone()[0]
assert native_count==1
health=json.loads((R/'bridge_health.json').read_text());rows=[dict(row) for row in db.execute('select ordinal,state,request_id,capture_retries from tasks where ordinal between 53 and 56')]
out={'at':time.time(),'ready':True,'recovered_task':53,'original_task_id':t['task_id'],'request_id':r['request_id'],'conversation_id':binding['conversation_id'],'native_user_messages':native_count,'question_unchanged':True,'capture_retries':0,'body_length':len(r['body_markdown']),'sources':len(r['sources']),'events':events,'postgres':pg,'following_tasks':rows,'current':{k:health.get(k) for k in ['status','captured','geo_processed','delivery_errors','progress']}}
(D/'verification.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out,ensure_ascii=False))
