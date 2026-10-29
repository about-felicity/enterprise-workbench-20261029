import json,sys
from pathlib import Path
sys.path[:0]=['/home/user/redroid-doubao/geo-batch-code','/home/user/redroid-yuanbao']
from native_client import NativeClient,BASE
r=NativeClient(BASE/'batches/geo-panel-yuanbao-20261022-090005-705819fb');r.connect()
bridge=Path('/home/user/redroid-doubao/worker-venv/lib/python3.10/site-packages/frida_tools/bridges/java.js').read_text()
script=r.session.create_script(bridge+'''\nconst Java=bridge;
rpc.exports={inspect:function(){return new Promise(function(resolve,reject){Java.perform(function(){try{
 const rows=[],names=Java.enumerateLoadedClassesSync().filter(n=>n.startsWith('com.tencent.hunyuan.mpcommon.generated.biz.homedrawer.') && n.includes('Session') && !n.includes('$'));
 function run(i){if(i===names.length){resolve({names:names,rows:rows});return;}
 Java.choose(names[i],{onMatch:function(o){const fields={};for(const f of o.getClass().getDeclaredFields()){
 if(String(f.getType().getName())==='java.lang.Object'){f.setAccessible(true);const L=Java.use('XP.e');const v=L.getValue.call(Java.cast(f.get(o),L));fields[String(f.getName())]=v===null?null:String(v.toString()).slice(0,1500);}}
 rows.push({className:names[i],values:fields});},onComplete:function(){run(i+1);}});}run(0);
}catch(e){reject(e);}});});}};''')
try:
 script.load();rows=script.exports_sync.inspect();print(json.dumps(rows,ensure_ascii=False))
 Path('/opt/monitor/geo-capture/maintenance/20261022-yuanbao-stall/history-list.json').write_text(json.dumps(rows,ensure_ascii=False))
finally:r.close()
