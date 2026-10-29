"""Stop only the reader, preserve the original task, navigate existing history."""
import sys,json,sqlite3,subprocess,time,hashlib
from pathlib import Path
D=Path('/opt/monitor/geo-capture/maintenance/20261023-yuanbao-unbound');S=D/'stage'
sys.path[:0]=[str(S/'yuanbao'),str(S/'doubao')]
from question_only_adapters import android,yuanbao_reader
from unbound_history import recover
R=Path('/home/user/redroid-yuanbao/batches/geo-panel-yuanbao-20261023-090004-d6b66215');unit='geo-native@'+R.name+'.service'
assert not (R/'maintenance_pause.json').exists(),'Preserve an existing pause'
subprocess.run(['systemctl','mask','--runtime',unit],check=True)
subprocess.run(['systemctl','stop',unit],check=True,timeout=45)
with sqlite3.connect(R/'tasks.sqlite') as db:
 db.row_factory=sqlite3.Row
 with sqlite3.connect(D/'before-tasks.sqlite') as backup:db.backup(backup)
 task=dict(db.execute("select * from tasks where state='prepared' order by ordinal limit 1").fetchone())
 assert task['ordinal']==13 and not task['request_id']
 task.pop('result_json',None)
def event(tid,name,detail):
 with sqlite3.connect(R/'tasks.sqlite') as db:db.execute('insert into events(task_id,time,event,detail) values(?,?,?,?)',(tid,time.time(),name,detail))
client=yuanbao_reader(R);app=android('yuanbao',None,None);out={'at':time.time(),'task_before':task,'unit':unit}
try:
 out['navigation']=recover(R,task,{'status':'absent'},app,client.close,event)
 for _ in range(6):
  value=client.lookup(task)
  out['lookup']={k:v for k,v in value.items() if k not in ('native_snapshot','sources','body_markdown')}
  if value.get('status') in ('complete','pending') and value.get('request_id'):break
  time.sleep(2)
 client.connect();ids=client.script.exports_sync.conversation_ids()
 out['lightweight_ids']=ids;out['lightweight_ids_only']=all(isinstance(v,str) for v in ids)
 binding=R/(task['task_id']+'.binding.json')
 if binding.exists():out['binding']=json.loads(binding.read_text())
 if value.get('body_markdown'):out.update(body_chars=len(value['body_markdown']),body_sha256=hashlib.sha256(value['body_markdown'].encode()).hexdigest(),sources=len(value.get('sources',[])))
finally:
 client.close();(D/'live-recovery.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
print(json.dumps(out,ensure_ascii=False))
