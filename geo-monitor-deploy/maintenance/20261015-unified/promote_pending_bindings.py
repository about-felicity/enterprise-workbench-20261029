import sys,json,sqlite3,subprocess,time
from pathlib import Path
sys.path.insert(0,'/opt/monitor/geo-capture');sys.path.insert(0,'/home/user/redroid-doubao/geo-batch-code')
from native_soak import API,operation,lane
from question_only_adapters import DoubaoReader
pointer=json.loads(Path('/opt/monitor/geo-capture/question_only_acceptance_current.json').read_text());root=Path(pointer['root']);api=API()
for model in ('doubao1','doubao2'):
 current=lane(api.panel(),model)['current']
 if current['service_state'] in ('active','activating'):
  operation(root,api,model+'-ack-read-pause',model,'pause',{})
code=Path('/home/user/redroid-doubao/geo-batch-code')
for name in ('core','adapters'):
 target=code/('question_only_'+name+'.py');backup=root/(target.name+'.before-ack')
 if not backup.exists():backup.write_bytes(target.read_bytes())
 target.write_bytes(Path('/tmp/question_only_'+name+'_ack.py').read_bytes());target.chmod(0o600)
from importlib import reload
import question_only_core,question_only_adapters
reload(question_only_core);reload(question_only_adapters)
for model in ('doubao1','doubao2'):
 batch=pointer['jobs'][model]['batch'];job=Path('/home/user/redroid-doubao/batches')/batch
 db=sqlite3.connect(job/'tasks.sqlite');db.row_factory=sqlite3.Row
 tasks=[dict(r) for r in db.execute("select * from tasks where state='prepared'")];db.close()
 reader=question_only_adapters.DoubaoReader(job,{'doubao1':'doubao-hpe14-13-test','doubao2':'doubao-hpe14-account2'}[model])
 for task in tasks:
  result=reader.lookup(task)
  print(json.dumps({'model':model,'task':task['task_id'],'read_status':result['status'],'body_length':len(result.get('body_markdown','')),'sources':len(result.get('sources',[])),'resend':False}))
