"""One-time bounded repair. Original requests/history remain intact. Do not rerun."""
import hashlib,json,shutil,sqlite3,subprocess,time
from pathlib import Path
batch='geo-panel-doubao2-20261020-090001-6bcafb90';root=Path('/home/user/redroid-doubao/batches')/batch
unit='geo-native@'+batch+'.service'
assert subprocess.run(['systemctl','is-active',unit],capture_output=True,text=True).stdout.strip()=='inactive'
backup=Path('/opt/monitor/geo-capture/maintenance/20261020-doubao-recovery')
backup.mkdir(parents=True,exist_ok=False,mode=0o700)
db=sqlite3.connect(root/'tasks.sqlite');db.row_factory=sqlite3.Row
with sqlite3.connect(backup/'tasks.before.sqlite') as saved:db.backup(saved)
t=dict(db.execute("select * from tasks where task_id='565e4e38-0407-50f8-8fd0-f295b4419e5c'").fetchone())
assert t['state']=='prepared' and t['ordinal']==18 and t['capture_retries']==0
assert db.execute("select count(*) from tasks where state='completed'").fetchone()[0]==17
snapshot=json.loads((root/(t['task_id']+'-attempt-0.pre-send.json')).read_text())
native_path=next(item['database'] for item in snapshot['databases'] if '2697541922066524' in item['database'])
native=sqlite3.connect(Path(native_path).as_uri()+'?mode=ro',uri=True);native.row_factory=sqlite3.Row
r=dict(native.execute('select * from im_message where local_message_id=?',('7e05dd72-9965-4fe5-a365-e3421898365a',)).fetchone())
assert r['message_id'] and r['server_index']>0
blocks=json.loads(r['content']);assert '\n\n'.join(b['content']['text_block']['text'] for b in blocks if 'text_block' in b['content'])==t['question']
assert native.execute('select count(*) from im_message where conversation_id=? and user_type=1 and local_index<?',(r['conversation_id'],r['local_index'])).fetchone()[0]>0
answers=[dict(v) for v in native.execute('select * from im_message where conversation_id=? and user_type=2 and local_index>? order by local_index',(r['conversation_id'],r['local_index']))]
assert len(answers)==1 and answers[0]['status']==21 and all(b.get('is_finish') is True for b in json.loads(answers[0]['content']))
proof={'reason':'confirmed_completed_answer_in_existing_context','task_id':t['task_id'],'wire_question':t['question'],'request_id':r['local_message_id'],'answer_id':answers[0]['local_message_id'],'request':r,'answer':answers[0],'finished':True,'not_a_monitoring_sample':True}
(backup/'rejected-context-attempt0.json').write_text(json.dumps(proof,ensure_ascii=False));(backup/'rejected-context-attempt0.json').chmod(0o600)
for name in ['question_only_worker.py','question_only_adapters.py']:
 dest=Path('/home/user/redroid-doubao/geo-batch-code')/name;shutil.copy2(dest,backup/(name+'.before'))
shutil.copy2('/opt/monitor/geo-capture/panel.html',backup/'panel.html.before')
for name in ['question_only_worker.py','question_only_adapters.py','native_readback_guard.py']:
 src=Path('/tmp/doubao-recovery-'+name);dest=Path('/home/user/redroid-doubao/geo-batch-code')/name
 compile(src.read_text(),str(dest),'exec');tmp=dest.with_suffix('.repair-tmp');shutil.copy2(src,tmp);tmp.replace(dest)
shutil.copy2('/tmp/doubao-recovery-panel.html','/opt/monitor/geo-capture/panel.html')
with db:
 db.execute('insert into failed_attempts values(?,?,?,?,?,?,?,?)',(t['task_id'],0,t['question'],proof['request_id'],proof['answer_id'],json.dumps(proof,ensure_ascii=False),proof['reason'],time.time()))
 db.execute("update tasks set state='pending',capture_retries=1,not_before=?,attempts=0,prepared_at=null,request_id=null,answer_id=null,result_json=null,error=null where task_id=?",(time.time()+10,t['task_id']))
 db.execute('insert into events(task_id,time,event,detail) values(?,?,?,?)',(t['task_id'],time.time(),'operator_storage_recovery_scheduled','Confirmed terminal response in wrong conversation retained; retry once in verified empty chat; no unknown-send replay'))
db.close()
print(json.dumps({'backup':str(backup),'original_completed_preserved':17,'known_context_failure_archived':True,'retry_only_ordinal18':True,'worker_and_fresh_composer_guards_deployed':True}))
