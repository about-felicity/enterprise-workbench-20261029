import ast,fcntl,hashlib,json,os,shutil,sqlite3,subprocess,time
from pathlib import Path
root=Path('/home/user/redroid-yuanbao/batches/geo-panel-yuanbao-20261102-090004-bb1beb6a')
source=Path('/home/user/redroid-doubao/geo-batch-code/question_only_worker.py')
raw=source.read_bytes();assert hashlib.sha256(raw).hexdigest()==CHANGE['before'],'Production code differs; stop'
tree=ast.parse(CHANGE['text']);fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='interrupted_original_expired')
ns={};exec(compile(ast.Module(body=[fn],type_ignores=[]),'<test>','exec'),ns)
f=ns['interrupted_original_expired'];t={'state':'prepared','prepared_at':100,'request_id':'r'};o={'reason':'native_answer_interrupted','native_request_confirmed':True,'request_id':'r'}
assert f('yuanbao',t,o,1001)
assert not f('doubao1',t,o,1001)
assert not f('yuanbao',t,o,1000)
assert not f('yuanbao',t,{**o,'request_id':'other'},1001)
assert not f('yuanbao',t,{**o,'reason':'generating'},1001)
assert not f('yuanbao',{**t,'state':'completed'},o,1001)
work=Path('/home/user/redroid-yuanbao/maintenance/repair-20261102');work.mkdir(parents=True,exist_ok=True)
service='geo-native@'+root.name+'.service'
subprocess.run(['systemctl','stop',service],check=True,timeout=50)
try:
 with open('/run/lock/redroid-yuanbao-yuanbao-hpe14-android13.lock','a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  with sqlite3.connect(root/'tasks.sqlite') as db:
   db.row_factory=sqlite3.Row
   task=dict(db.execute('select * from tasks where ordinal=6').fetchone());tid=task['task_id']
   assert tid=='3050e5fd-fddf-5aaa-b7ee-e925f5b66bdf' and task['state'] in ['prepared','needs_attention'] and task['capture_retries']==0
   native=json.loads((root/(tid+'.native.json')).read_text());binding=json.loads((root/(tid+'.binding.json')).read_text())
   assert native['message']['state']['text']=='INTERRUPTED' and native['content']['state']['text']=='INTERRUPTED'
   assert not native['conversation']['isBusy'] and native['content']['traceId']==task['request_id']
   assert binding['task_id']==tid and binding['server_answer_id']==native['message']['serverId']
   assert native['message']['serverPairId']==native['question']['serverId']
   assert native['message']['pairId']==native['question']['id']
   assert any(e.get('textEntity',{}).get('text')==task['wire_question'] for e in native['question_entities'])
   assert time.time()-task['prepared_at']>900
   assert json.loads((root/(tid+'.history-refresh.json')).read_text())['attempts']==2
   with sqlite3.connect(work/'tasks-before.sqlite') as dest:db.backup(dest)
   completed={r['task_id']:hashlib.sha256(r['result_json'].encode()).hexdigest() for r in db.execute("select task_id,result_json from tasks where state='completed'")}
   (work/'completed-before.json').write_text(json.dumps(completed))
   archive=work/tid;archive.mkdir(exist_ok=False)
   shutil.copy2(source,work/'question_only_worker.py.before')
   temp=source.with_suffix('.repair.tmp');temp.write_text(CHANGE['text']);temp.chmod(source.stat().st_mode & 0o777);os.chown(temp,source.stat().st_uid,source.stat().st_gid);os.replace(temp,source)
   for p in root.glob(tid+'.*'):
    if p.is_file():shutil.move(str(p),str(archive/p.name))
   audit={'reason':'confirmed_native_interrupted','original_request':task['request_id'],'original_answer':binding['server_answer_id'],'history_attempts':2,'authorization':'User requested immediate repair of today GEO capture','retry_limit':1,'archive':str(archive)}
   db.execute('insert into failed_attempts values(?,?,?,?,?,?,?,?)',(tid,0,task['wire_question'],task['request_id'],binding['server_answer_id'],json.dumps(audit),'operator_confirmed_interruption_retry',time.time()))
   db.execute("update tasks set state='pending',capture_retries=1,prepared_at=null,request_id=null,answer_id=null,result_json=null,error=null,not_before=0 where task_id=?",(tid,))
   db.execute('insert into events(task_id,time,event,detail) values(?,?,?,?)',(tid,time.time(),'operator_interrupted_send_recovery_scheduled',json.dumps(audit)))
   db.commit()
   assert all(hashlib.sha256(r['result_json'].encode()).hexdigest()==completed[r['task_id']] for r in db.execute("select task_id,result_json from tasks where state='completed'"))
   print('REPAIRED',json.dumps({'task':tid,'preserved_completed':len(completed),'backup':str(work),'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'tests':6}),flush=True)
finally:
 subprocess.run(['systemctl','start',service],check=True)
