import json,sys
from pathlib import Path
sys.path[:0]=['/home/user/redroid-doubao/geo-batch-code','/home/user/redroid-yuanbao']
from native_client import NativeClient,BASE
root=BASE/'batches/geo-panel-yuanbao-20261022-090005-705819fb'
r=NativeClient(root);r.connect()
bridge=Path('/home/user/redroid-doubao/worker-venv/lib/python3.10/site-packages/frida_tools/bridges/java.js').read_text()
schema=(BASE/'tools/chat_model_schema.json').read_text()
code=(BASE/'native_models.js').read_text().split('rpc.exports =')[0]
# Read selected title-bearing model classes, without network or writes.
names=[k for k,v in json.loads(schema).items() if 'conversationId' in v.values() and 'title' in v.values()]
script=r.session.create_script(bridge+'\nconst Java=bridge;\nconst MODEL_SCHEMA='+schema+';\n'+code+'''\nrpc.exports={inspect:function(names){return new Promise(function(resolve,reject){Java.perform(function(){
const rows=[];function run(i){if(i===names.length){resolve(rows);return;}
Java.choose(names[i],{onMatch:function(o){try{const v=serializeModel(o,0);if(v.conversationId==='0RRIw2HvYau')rows.push(v);}catch(e){}},onComplete:function(){run(i+1);}});}run(0);
});});}};''')
try:
 script.load();rows=script.exports_sync.inspect(names)
 print(json.dumps({'classes':names,'matches':rows},ensure_ascii=False))
 Path('/opt/monitor/geo-capture/maintenance/20261022-yuanbao-stall/history-models.json').write_text(json.dumps(rows,ensure_ascii=False))
finally:r.close()
