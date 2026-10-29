import json,sys
from pathlib import Path
sys.path[:0]=['/home/user/redroid-doubao/geo-batch-code','/home/user/redroid-yuanbao']
from native_client import NativeClient,BASE
r=NativeClient(BASE/'batches/geo-panel-yuanbao-20261022-090005-705819fb');r.connect()
bridge=Path('/home/user/redroid-doubao/worker-venv/lib/python3.10/site-packages/frida_tools/bridges/java.js').read_text()
schema=(BASE/'tools/chat_model_schema.json').read_text()
code=(BASE/'native_models.js').read_text().split('rpc.exports =')[0]
script=r.session.create_script(bridge+'\nconst Java=bridge;\nconst MODEL_SCHEMA='+schema+';\n'+code+'''\nrpc.exports={inspect:function(){return new Promise(function(resolve,reject){Java.perform(function(){try{
 const names=Java.enumerateLoadedClassesSync().filter(n=>n.startsWith('com.tencent.hunyuan.mpcommon.generated.') && /[Ll]ist|[Hh]istory|[Dd]rawer/.test(n) && !n.includes('$'));
 const rows=names.map(n=>({name:n,fields:Array.from(Java.use(n).class.getDeclaredFields()).map(f=>String(f))}));resolve(rows);
}catch(e){reject(e);}});});}};''')
try:
 script.load();rows=script.exports_sync.inspect();print(json.dumps(rows,ensure_ascii=False)[:27000])
 Path('/opt/monitor/geo-capture/maintenance/20261022-yuanbao-stall/history-classes.json').write_text(json.dumps(rows))
finally:r.close()
