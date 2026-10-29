import json,subprocess,sys
from pathlib import Path
import frida
sys.path.insert(0,'/home/user/redroid-yuanbao/tools')
from wechat_qr_compat import validate
sys.path.insert(0,'/home/user/redroid-doubao')
from unattended_core import Queue
validate()
root=Path('/home/user/redroid-yuanbao/batches/geo-yuanbao-21x5-20261015')
q=Queue(root/'tasks.sqlite');task=q.next_task()
pid=int(subprocess.check_output(['docker','exec','yuanbao-hpe14-android13','pidof','com.tencent.hunyuan.app.chat']))
session=frida.get_device_manager().add_remote_device('127.0.0.1:27044').attach(pid,realm='native')
bridge=Path('/home/user/redroid-doubao/worker-venv/lib/python3.10/site-packages/frida_tools/bridges/java.js').read_text()
script=session.create_script(bridge+'\nconst Java=bridge;\n'+Path('/tmp/yuanbao_wcdb_reader.js').read_text())
script.load()
def shape(value,depth=0):
    if depth>7:return type(value).__name__
    if isinstance(value,dict):return {k:shape(v,depth+1) for k,v in value.items()}
    if isinstance(value,list):return {'length':len(value),'first':shape(value[0],depth+1) if value else None}
    return type(value).__name__
try:
    script.exports_sync.discover()
    result=script.exports_sync.read(task['task_id'])
    target=root/'native-wcdb-first.json';target.write_text(json.dumps(result,ensure_ascii=False));target.chmod(0o600)
    for store in result:
        rows=[]
        for row in store['messages']:
            raw=json.loads(row['rawContent'])
            rows.append({'speaker':row['speaker'],'status':row['status'],'msgIndex':row['msgIndex'],'raw_shape':shape(raw)})
        print(json.dumps({'messages':rows,'conversation_flags':[{k:r[k] for k in ['stopGenerating','endConv']} for r in store['conversation']],'state_shape':shape(store['state'])}))
finally:session.detach()
