import json,subprocess,sys
from pathlib import Path
import frida
sys.path.insert(0,'/home/user/redroid-yuanbao/tools')
from wechat_qr_compat import validate
validate()
root=Path('/home/user/redroid-yuanbao/batches/geo-yuanbao-21x5-20261015')
data=json.loads((root/'native-model-first.json').read_text())
context=next(r['value']['h'] for r in data if r['kind']=='markdown' and r['value']['h'].get('conversationId'))
pid=int(subprocess.check_output(['docker','exec','yuanbao-hpe14-android13','pidof','com.tencent.hunyuan.app.chat']))
session=frida.get_device_manager().add_remote_device('127.0.0.1:27044').attach(pid,realm='native')
bridge=Path('/home/user/redroid-doubao/worker-venv/lib/python3.10/site-packages/frida_tools/bridges/java.js').read_text()
schema=Path('/home/user/redroid-yuanbao/tools/chat_model_schema.json').read_text()
script=session.create_script(bridge+'\nconst Java=bridge;\nconst MODEL_SCHEMA='+schema+';\n'+Path('/tmp/yuanbao_native_models.js').read_text())
script.load()
try:
    result=script.exports_sync.read_known(context['conversationId'],context['msgId'])
    target=root/'native-getters-first.json';target.write_text(json.dumps(result,ensure_ascii=False));target.chmod(0o600)
    print(json.dumps({'keys':list(result),'message_id':result['message'].get('id'),'state':result['message'].get('state'),'speaker':result['message'].get('speaker'),'content':result.get('content'),'conversation':result.get('conversation')}))
finally:session.detach()
