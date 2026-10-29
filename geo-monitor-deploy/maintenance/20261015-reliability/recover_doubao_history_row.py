"""Evidence-bound repair of a historical rowid false positive; no send/reset."""
import ast,hashlib,json,shutil,sqlite3,subprocess,sys,time
from pathlib import Path
stage=Path('/tmp/geo-doubao-rowid-stage')
sys.path[:0]=[str(stage),'/opt/monitor/geo-capture','/home/user/redroid-doubao/geo-batch-code']
from question_only_core import Queue,request_fingerprint,message_text,correlate,lookup_bound
from question_only_adapters import DoubaoReader
from runtime_reliability import CompletionFence
from native_soak import API,operation,atomic,read,lane
base=Path('/opt/monitor/geo-capture');out=base/'maintenance/20261015-reliability/doubao-history-row-fix'
out.mkdir(mode=0o700,exist_ok=True)
if (out/'deployed.json').exists():print(json.dumps({'already_deployed':True}));raise SystemExit(0)
p=read(base/'soak12h_current.json');assert p['test_id']=='question-only-soak12h-videofix-1792066775'
m=read(Path(p['root'])/'manifest.json');api=API();panel=api.panel()
for model in ('doubao1','doubao2'):assert lane(panel,model)['current']['batch']==m['jobs'][model]['batch']
home=Path('/home/user/redroid-doubao/batches')/m['jobs']['doubao1']['batch']
q=Queue(home/'tasks.sqlite');task_id='512cd59d-44e5-5569-80ad-83aa515e8981'
task=dict(q.db.execute('select * from tasks where task_id=?',(task_id,)).fetchone())
assert task['state']=='needs_attention' and task['ordinal']==188 and task['error']=='Question was sent in an existing conversation'
assert q.db.execute("select count(*) from events where task_id=? and event='send_click_intent_committed'",(task_id,)).fetchone()[0]==1
with sqlite3.connect(out/'tasks.before.sqlite') as saved:q.db.backup(saved)
before=home/(task_id+'-attempt-0.pre-send.json');shutil.copy2(before,out/before.name)
snapshot=read(before);amended=json.loads(json.dumps(snapshot));proof=[]
for item in amended['databases']:
    with sqlite3.connect(Path(item['database']).as_uri()+'?mode=ro',uri=True) as db:
        db.row_factory=sqlite3.Row
        for row in db.execute('select rowid,* from im_message where rowid>? and user_type=1',(item['max_rowid'],)):
            if message_text(row)!=task['question'] or row['conversation_id'] not in item['conversations']:continue
            prior=q.db.execute("select * from tasks where state='completed' and json_extract(result_json,'$.question_id')=?",(row['local_message_id'],)).fetchall()
            assert len(prior)==1
            old=json.loads(prior[0]['result_json'])
            old_text='\n\n'.join(b['content']['text_block']['text'] for b in old['raw_question_blocks'] if 'text_block' in b['content'])
            assert old['conversation_id']==row['conversation_id'] and old_text==message_text(row)==task['question']
            finished=q.db.execute("select max(time) from events where task_id=? and event='completed'",(prior[0]['task_id'],)).fetchone()[0]
            assert finished<snapshot['created_at'] and row['create_time']<snapshot['created_at']-30
            assert row['server_index']==1 and db.execute('select count(*) from im_message where conversation_id=? and user_type=1',(row['conversation_id'],)).fetchone()[0]==1
            item.setdefault('prior_requests',[]).append(request_fingerprint(row))
            proof.append({'prior_task_id':prior[0]['task_id'],'prior_ordinal':prior[0]['ordinal'],'request_id':row['local_message_id'],
                'same_message_identity':True,'original_completed_at':finished,'native_created_at':row['create_time'],
                'replacement_rowid':row['rowid'],'baseline_max_rowid':item['max_rowid']})
assert len(proof)==1
binding=correlate(amended,task['question']);assert binding and binding['conversation_id'] not in next(i for i in amended['databases'] if i['database']==binding['database'])['conversations']
fence=CompletionFence();reads=[]
for index in range(2):
    value=lookup_bound(task,binding)
    assert value['status']=='complete' and value['sources'] and value['first_user_turn'] and value['body_capture_complete'] and value['source_capture_complete']
    stable=fence.ready(task_id,value);atomic(out/('original-result-read-'+str(index)+'.json'),value)
    reads.append({'at':time.time(),'result_sha256':hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()})
    if index==0:time.sleep(3)
assert stable
atomic(out/'proof.json',{'at':time.time(),'task_id':task_id,'historical_rows':proof,'original_new_binding':binding,'stable_reads':reads,'native_clicks':1,'model_resends':0})
for model in ('doubao1','doubao2'):operation(out,api,model+'-drain',model,'pause',{})
print(json.dumps({'phase':'draining_only_two_doubao_workers','original_new_reply_proven':True}),flush=True)
until=time.time()+1000
while True:
    panel=api.panel();currents={model:lane(panel,model)['current'] for model in ('doubao1','doubao2')}
    if all(c['service_state'] not in ('active','activating','deactivating','reloading') for c in currents.values()):break
    if time.time()>until:raise RuntimeError('Drain timeout; no force stop')
    time.sleep(3)
assert not currents['doubao2']['needs_review'] and currents['doubao2']['captured']==currents['doubao2']['processed']
for name in ('question_only_core.py','question_only_adapters.py'):
    target=Path('/home/user/redroid-doubao/geo-batch-code')/name
    ast.parse((stage/name).read_text());shutil.copy2(target,out/(name+'.before'))
    shutil.copyfile(stage/name,target)
amended['historical_identity_reconciliation']={'at':time.time(),'proof':str(out/'proof.json'),'original_baseline_sha256':hashlib.sha256(before.read_bytes()).hexdigest()}
atomic(before,amended)
# Let the real reader persist its normal binding and conversation ledger.
reader=DoubaoReader(home,'doubao-hpe14-13-test');observed=reader.lookup(task)
assert observed==value
with q.db:
    assert q.db.execute("update tasks set state='prepared',request_id=?,error=null where task_id=? and state='needs_attention'",(value['request_id'],task_id)).rowcount==1
    q.event(task_id,'historical_row_identity_reconciled','Prior completed message reinserted above baseline rowid; same original new request read, no resend')
q.complete(task_id,value);q.db.close()
for model in ('doubao1','doubao2'):
    assert lane(api.panel(),model)['current']['batch']==m['jobs'][model]['batch']
    operation(out,api,model+'-resume-original',model,'resume',{})
atomic(out/'deployed.json',{'at':time.time(),'old_test':p['test_id'],'task_id':task_id,'same_batches':{x:m['jobs'][x]['batch'] for x in ('doubao1','doubao2')},
    'historical_reinsert_proven':True,'new_request_fresh_first_turn':True,'native_clicks':1,'model_resends':0,'other_collectors_restarted':False,'core_android_restarted':False})
print(json.dumps({'phase':'same_two_batches_resumed','original_task_completed_without_resend':True}),flush=True)
