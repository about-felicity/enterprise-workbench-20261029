"""Metadata-only tracing of OpenSDK QR listener lifecycle."""
import json
from pathlib import Path
import subprocess
import time
import frida

CODE=r'''
Java.perform(function(){
 const C=Java.use('com.tencent.mm.opensdk.diffdev.a.a');
 const listField=C.class.getDeclaredField('c');listField.setAccessible(true);
 const List=Java.use('java.util.List');
 function count(obj){try{const v=Java.cast(listField.get(obj),List);return List.size.call(v);}catch(e){return -1;}}
 function callers(){try{return Java.backtrace({limit:7}).frames.map(f=>f.className+'.'+f.methodName).slice(0,7);}catch(e){return [];}}
 Java.choose('com.tencent.mm.opensdk.diffdev.a.a',{
  onMatch:function(o){send({event:'current_sdk_state',listeners:count(o),hasTask:o.d.value!==null});},onComplete:function(){}
 });
 ['addListener','removeListener','removeAllListeners','auth','stopAuth'].forEach(function(name){
  C[name].overloads.forEach(function(method){
   method.implementation=function(){
    send({event:'sdk_'+name+'_before',listeners:count(this),callers:callers()});
    const result=method.apply(this,arguments);
    send({event:'sdk_'+name+'_after',listeners:count(this)});
    return result;
   };
  });
 });
 const B=Java.use('com.tencent.mm.opensdk.diffdev.a.b');
 const got=B.onAuthGotQrcode.overload('java.lang.String','[B');
 got.implementation=function(path,bytes){
  send({event:'sdk_qr_fanout',listeners:count(this.f.value),imageBytes:bytes?bytes.length:0});
  return got.call(this,path,bytes);
 };
 const E=Java.use('Kp.e');
 const appGot=E.onAuthGotQrcode.overload('java.lang.String','[B');
 appGot.implementation=function(path,bytes){
  send({event:'app_qr_callback',imageBytes:bytes?bytes.length:0});
  return appGot.call(this,path,bytes);
 };
 send({event:'lifecycle_observer_ready'});
});
'''

pid=int(subprocess.check_output(['docker','exec','yuanbao-hpe14-android13','pidof','com.tencent.hunyuan.app.chat'],text=True))
device=frida.get_device_manager().add_remote_device('127.0.0.1:27044')
session=device.attach(pid,realm='native')
bridge=Path('/home/user/redroid-doubao/worker-venv/lib/python3.10/site-packages/frida_tools/bridges/java.js').read_text()
script=session.create_script(bridge+'\nconst Java=bridge;\n'+CODE)
path=Path('/home/user/redroid-yuanbao/diagnostics/wechat-qr-20261015/lifecycle.jsonl')
def message(value,data):
    event={'time':time.time(),**value['payload']} if value.get('type')=='send' else {'time':time.time(),'event':'observer_error','kind':value.get('type')}
    with path.open('a') as out:out.write(json.dumps(event)+'\n')
    path.chmod(0o600)
    print(json.dumps(event),flush=True)
script.on('message',message)
try:script.load();time.sleep(100)
finally:session.detach()
