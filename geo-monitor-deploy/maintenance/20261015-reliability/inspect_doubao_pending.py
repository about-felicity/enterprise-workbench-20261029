"""Read-only original request progress, blocks and UI markers. No recovery."""
import json,sys,time,sqlite3,os,hashlib
from pathlib import Path
import xml.etree.ElementTree as ET
sys.path[:0]=['/opt/monitor/geo-capture','/home/user/redroid-doubao/geo-batch-code']
from native_soak import read,atomic
from question_only_core import lookup_bound,parse_blocks
model=sys.argv[1];assert model in ('doubao1','doubao2')
base=Path('/opt/monitor/geo-capture');p=read(base/'soak12h_current.json');m=read(Path(p['root'])/'manifest.json')
home=Path('/home/user/redroid-doubao/batches')/m['jobs'][model]['batch']
out=base/'maintenance/20261015-reliability'/('pending-'+model);out.mkdir(exist_ok=True,mode=0o700)
with sqlite3.connect((home/'tasks.sqlite').as_uri()+'?mode=ro',uri=True) as db:
 db.row_factory=sqlite3.Row
 row=db.execute("select * from tasks where state in ('prepared','needs_attention') order by ordinal limit 1").fetchone()
 if row is None:print(json.dumps({'model':model,'pending':False}));raise SystemExit(0)
 task=dict(row);events=[dict(r) for r in db.execute('select event,time,detail from events where task_id=? order by time',(task['task_id'],))]
 binding_path=home/(task['task_id']+'-attempt-'+str(task.get('capture_retries',0))+'.binding.json')
 backup=out/(task['task_id']+'-original-tasks.sqlite')
 if not backup.exists():
  with sqlite3.connect(backup) as dst:db.backup(dst)
 report={'at':time.time(),'model':model,'test_id':p['test_id'],'task_id':task['task_id'],'ordinal':task['ordinal'],'question':task['question'],'state':task['state'],'error':task['error'],'prepared_at':task['prepared_at'],'elapsed':time.time()-(task['prepared_at'] or time.time()),'events':events,'model_actions':0}
 if binding_path.exists():
  binding=read(binding_path);observed=lookup_bound(task,binding)
  report['read_status']={k:observed.get(k) for k in ('status','native_request_confirmed','request_id','answer_id')}
  with sqlite3.connect(Path(binding['database']).as_uri()+'?mode=ro',uri=True) as native:
   backup=out/(task['task_id']+'-original-native.sqlite')
   if not backup.exists():
    with sqlite3.connect(backup) as dst:native.backup(dst)
   native.row_factory=sqlite3.Row
   rows=[dict(r) for r in native.execute('select rowid,* from im_message where conversation_id=? order by local_index',(binding['conversation_id'],))]
   atomic(out/(task['task_id']+'-native.json'),rows)
   report['native_messages']=[]
   for r in rows:
    blocks=parse_blocks(r['content']);texts=[b['content']['text_block'].get('text','') for b in blocks if 'text_block' in b['content']]
    report['native_messages'].append({k:r.get(k) for k in ('rowid','local_message_id','local_index','message_id','server_index','user_type')})
    report['native_messages'][-1].update(blocks=[{'type':b.get('type'),'finished':b.get('is_finish'),'content_keys':list(b.get('content',{}))} for b in blocks],body_characters=sum(map(len,texts)),body_sha256=hashlib.sha256('\n\n'.join(texts).encode()).hexdigest(),native_status_fields={k:v for k,v in r.items() if any(x in k.lower() for x in ('status','finish','time')) and k!='content'})
 os.environ['ADBUTILS_ADB_PATH']='/home/user/redroid-doubao/linux-tools/platform-tools/adb'
 import uiautomator2 as u2
 d=u2.connect('127.0.0.1:'+('5557' if model=='doubao1' else '5558'));xml=d.dump_hierarchy();(out/(task['task_id']+'-ui.xml')).write_text(xml)
 report['ui_markers']=[{'text':n.get('text','')[:180],'description':n.get('content-desc','')[:180],'resource_id':n.get('resource-id')} for n in ET.fromstring(xml).iter('node') if any(x in n.get('text','')+' '+n.get('content-desc','') for x in ('停止','生成','重试','网络','登录','验证','繁忙','失败'))]
 report['ui_controls']=[{'text':n.get('text','')[:80],'description':n.get('content-desc','')[:80],'resource_id':n.get('resource-id'),'bounds':n.get('bounds')} for n in ET.fromstring(xml).iter('node') if n.get('clickable')=='true' or n.get('content-desc')][:35]
 atomic(base/'maintenance/20261015-reliability'/(model+'-pending-audit.json'),report)
 export=Path('/tmp/geo-reliability-export')/(model+'-pending-audit.json');atomic(export,report);export.chmod(0o644)
 print(json.dumps(report,ensure_ascii=False))
