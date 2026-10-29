"""Preserve and summarize an ambiguous provider history; no send/recovery."""
from pathlib import Path
import sys,json,sqlite3,time,hashlib,shutil
sys.path[:0]=['/tmp','/opt/monitor/geo-capture']
import yuanbao_native_storage as ns
from native_soak import read,atomic
from all_channel_soak import audit,audit_nontext
base=Path('/opt/monitor/geo-capture');p=read(base/'soak12h_current.json');m=read(Path(p['root'])/'manifest.json')
home=Path('/home/user/redroid-yuanbao/batches')/m['jobs']['yuanbao']['batch']
out=base/'maintenance/20261015-reliability/yuanbao-ack';out.mkdir(exist_ok=True,mode=0o700)
task_id='2d668639-8b1c-5a6b-955b-566220026fea';cid='0RGfLig07CS'
with sqlite3.connect((home/'tasks.sqlite').as_uri()+'?mode=ro',uri=True) as db:
 db.row_factory=sqlite3.Row
 task=dict(db.execute('select * from tasks where task_id=?',(task_id,)).fetchone())
 clicks=db.execute("select count(*) from events where task_id=? and event='send_click_intent_committed'",(task_id,)).fetchone()[0]
 events=[dict(r) for r in db.execute('select * from events where task_id=? order by id',(task_id,))]
 target=out/'original-tasks.sqlite'
 if not target.exists():
  with sqlite3.connect(target) as dst:db.backup(dst)
atomic(out/'original-events.json',events)
shutil.copy2(home/(task_id+'.pre-send.json'),out/'original-pre-send.json')
observations=[]
for sample in range(2):
 records=[]
 for store,path in enumerate(ns.databases()):
  with ns.open_readonly(path) as db:
   db.execute('begin')
   rows=[dict(r) for r in db.execute('select * from ChatMessages where conversation_id=? order by message_index',(cid,))]
   for row in rows:
    raw=json.loads(row['raw_data']);speech=raw.get('speechesV2',[])
    texts=[c.get('msg','') for s in speech for c in s.get('content',[]) if c.get('type')=='text']
    docs=[d for s in speech for c in s.get('content',[]) if c.get('type')=='searchGuid' for d in c.get('docs',[])]
    request_ids=[s.get('extra',{}).get('requestId') for s in speech]
    records.append({'store':store,'message_id':row['message_id'],'index':row['message_index'],'speaker':row['speaker'],'created_at':row['create_time'],
       'question_equal':raw.get('displayPrompt')==task['question'] if row['speaker']=='human' else None,
       'raw_sha256':hashlib.sha256(row['raw_data'].encode()).hexdigest(),'text_lengths':[len(x) for x in texts],
       'source_count':len(docs),'original_client_request_equal':request_ids==['local_'+cid+'_1_1792077280_Q']})
   atomic(out/('full-history-stable-'+str(sample)+'-'+str(store)+'.json'),rows)
   db.rollback()
 observations.append(records)
 if sample==0:time.sleep(3)
assert observations[0]==observations[1] and len(observations[1])==4 and clicks==1
assert [r['index'] for r in observations[1]]==[1,2,3,4]
assert all(r['original_client_request_equal'] for r in observations[1])
verified=audit('yuanbao',m['jobs']['yuanbao'],set());nontext=audit_nontext('yuanbao',m['jobs']['yuanbao'])
report={'at':time.time(),'test_id':p['test_id'],'test_deadline':p['deadline'],'batch':home.name,'task_id':task_id,'ordinal':task['ordinal'],'question':task['question'],
 'state':task['state'],'error':task['error'],'agent_send_clicks':clicks,'automatic_resend_performed':False,'server_human_messages':2,'server_answer_messages':2,
 'same_original_client_request_id':True,'same_original_question':all(r['question_equal'] for r in observations[1] if r['speaker']=='human'),
 'full_history_two_stable_reads':True,'messages':observations[1],'task_delivery_files':{name:(home/name/(task_id+'.json')).exists() for name in ['outbox','receipts','nontext-outbox','nontext-receipts']},
 'task_has_result':bool(task['result_json']),'prior_text_verified_receipts':len(verified),'prior_nontext_audit':nontext,
 'production_code_changed':False,'worker_or_android_restarted':False,'recovery_status':'blocked_first_turn_and_provider_duplicate_history',
 'limits':['One collector send click does not establish one server generation. Both observed server turns are reported.',
 'Provider/App internal duplicate cause is unproven; do not claim it is a reused old conversation or waive first-user-turn gate.',
 'Original first answer is preserved in SQLite; current immutable reader exposes latest second pair. No unsupported parser substitution or latest-answer ingestion.',
 'No cache clear, login, queue reset, duplicate model request, new batch, or new paid job. Other four capture channels and creation continue.']}
atomic(base/'maintenance/20261015-reliability/yuanbao-duplicate-request-audit.json',report)
target=Path('/tmp/geo-reliability-export/yuanbao-duplicate-request-audit.json');atomic(target,report);target.chmod(0o644)
print(json.dumps(report,ensure_ascii=False))
