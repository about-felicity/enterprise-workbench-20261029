import hashlib,json,sqlite3,subprocess,sys,time
from pathlib import Path
sys.path[:0]=['/home/user/redroid-doubao/geo-batch-code','/home/user/redroid-doubao']
from question_only_delivery import DoubaoDelivery
root=Path('/home/user/redroid-doubao/batches/geo-panel-doubao1-20261021-090003-e1d20b1d');R=Path('/opt/monitor/geo-capture/maintenance/20261021-doubao-stall')
db=sqlite3.connect('file:'+str(root/'tasks.sqlite')+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
t=dict(db.execute('select * from tasks where ordinal=4').fetchone());r=json.loads(t.pop('result_json'))
assert t['state']=='completed' and r['request_id']=='d375664d-794e-4913-bdfc-240100e194c8'
clicks=db.execute('select count(*) from events where task_id=? and event=?',(t['task_id'],'send_click_intent_committed')).fetchone()[0];assert clicks==1 and t['capture_retries']==0
staged=json.loads((R/'staged-result.json').read_text());assert r['raw_answer_blocks']==staged['raw_answer_blocks'] and r['body_markdown']==staged['body_markdown']
items=[]
for p in (root/'outbox').glob('*.json'):
 item=json.loads(p.read_text())
 if item.get('payload',{}).get('native_result',{}).get('task_id')!=t['task_id']:continue
 receipt=json.loads((root/'receipts'/p.name).read_text());DoubaoDelivery.verify(None,receipt,item)
 items.append({'request_id':receipt['request_id'],'stored_run_id':receipt['save']['run_id']})
assert len(items)==1
sql="select json_agg(t) from (select run_id,day,payload->>'answer' answer,payload->>'source_capture_complete' complete from monitor_runs where model_id='doubao' and run_id='"+items[0]['stored_run_id']+"')t"
pg=json.loads(subprocess.check_output(['docker','exec','monitor-postgres','psql','-U','monitor_app','-d','monitor','-Atc',sql],text=True));assert len(pg)==1
assert pg[0]['answer']==r['body_markdown'].strip() and pg[0]['complete']=='true'
pg[0]['answer_sha256']=hashlib.sha256(pg[0].pop('answer').encode()).hexdigest()
health=json.loads((root/'bridge_health.json').read_text())
out={'at':time.time(),'original_task':4,'question':t['question'],'send_clicks':clicks,'capture_retries':t['capture_retries'],'body_length':len(r['body_markdown']),'sources':len(r['sources']),'native_tips':r['native_tips'],'raw_blocks_preserved':True,'receipts':items,'pg':pg,'current':{k:health.get(k) for k in ('status','captured','geo_processed','tasks','progress','delivery_errors')}}
(R/'verification.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out,ensure_ascii=False))
