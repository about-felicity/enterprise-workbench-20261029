import json,sys
from pathlib import Path
sys.path[:0]=['/home/user/redroid-doubao/geo-batch-code','/home/user/redroid-yuanbao']
from native_client import NativeClient,BASE
r=NativeClient(BASE/'batches/geo-panel-yuanbao-20261022-090005-705819fb');r.connect()
bridge=Path('/home/user/redroid-doubao/worker-venv/lib/python3.10/site-packages/frida_tools/bridges/java.js').read_text()
script=r.session.create_script(bridge+'''\nconst Java=bridge;
rpc.exports={inspect:function(){return new Promise(function(resolve,reject){Java.perform(function(){try{
 const names=Java.enumerateLoadedClassesSync().filter(n=>n.startsWith('com.tencent.hunyuan.') && /Session/.test(n));
 const rows=names.map(n=>{let c=Java.use(n).class;return {name:n,fields:Array.from(c.getDeclaredFields()).map(f=>String(f)),methods:Array.from(c.getDeclaredMethods()).filter(m=>String(m).indexOf('native ')===-1).map(m=>String(m))};});
 resolve(rows);
}catch(e){reject(e);}});});}};''')
try:
 script.load();rows=script.exports_sync.inspect()
 Path('/opt/monitor/geo-capture/maintenance/20261022-yuanbao-stall/classes.json').write_text(json.dumps(rows))
 print(json.dumps([x for x in rows if any('title' in f.lower() or 'cid' in f.lower() for f in x['fields'])],ensure_ascii=False)[:20000])
 print('classes',[x['name'] for x in rows])
finally:r.close()
