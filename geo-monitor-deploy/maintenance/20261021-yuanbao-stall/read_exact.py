import json,sys
from pathlib import Path
sys.path.insert(0,'/home/user/redroid-yuanbao')
from native_client import NativeClient
r=NativeClient(Path('/tmp'));r.connect();r.script.unload()
bridge=Path('/home/user/redroid-doubao/worker-venv/lib/python3.10/site-packages/frida_tools/bridges/java.js').read_text()
schema=Path('/home/user/redroid-yuanbao/tools/chat_model_schema.json').read_text()
r.script=r.session.create_script(bridge+'\nconst Java=bridge;\nconst MODEL_SCHEMA='+schema+';\n'+Path('/tmp/yuanbao-exact-probe.js').read_text());r.script.load()
try:
 raw=r.script.exports_sync.read_known('0RPgFhBs0yO','0RPgFhBs0yO_2')
 Path('/opt/monitor/geo-capture/maintenance/20261021-yuanbao-stall/exact-native.json').write_text(json.dumps(raw,ensure_ascii=False))
 print(json.dumps({'message':{k:raw.get('message',{}).get(k) for k in ('id','serverId','state','pairId','serverPairId','serverIndex')},'content':{k:raw.get('content',{}).get(k) for k in ('isEof','traceId','entityCount')},'entities':len(raw.get('entities',[]))},ensure_ascii=False))
finally:r.close()
