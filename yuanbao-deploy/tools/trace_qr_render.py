"""Trace QR display stages without reading image contents or login identifiers."""
import json
from pathlib import Path
import subprocess
import time
import frida

CODE=r'''
Java.perform(function(){
 function stage(cls,name,label){
  const C=Java.use(cls);
  C[name].overloads.forEach(function(method){
   method.implementation=function(){
    const started=Date.now();send({event:'enter',stage:label});
    try{const value=method.apply(this,arguments);send({event:'return',stage:label,elapsedMs:Date.now()-started});return value;}
    catch(e){send({event:'throw',stage:label,errorClass:String(e).split(':')[0]});throw e;}
   };
  });
 }
 stage('Up.n','invokeSuspend','qr_display_coroutine');
 stage('Up.m','invokeSuspend','qbar_decode');
 stage('com.tencent.hunyuan.mpcommon.generated.biz.login.bizmodel.n','c','custom_style_flag');
 stage('com.tencent.hunyuan.mpcommon.generated.biz.login.bizmodel.n','a','branded_qr_generate');
 stage('Up.s','U0','official_sdk_fallback');
 send({event:'render_observer_ready'});
});
'''
pid=int(subprocess.check_output(['docker','exec','yuanbao-hpe14-android13','pidof','com.tencent.hunyuan.app.chat'],text=True))
session=frida.get_device_manager().add_remote_device('127.0.0.1:27044').attach(pid,realm='native')
bridge=Path('/home/user/redroid-doubao/worker-venv/lib/python3.10/site-packages/frida_tools/bridges/java.js').read_text()
script=session.create_script(bridge+'\nconst Java=bridge;\n'+CODE)
path=Path('/home/user/redroid-yuanbao/diagnostics/wechat-qr-20261015/render-stages.jsonl')
def message(value,data):
    event={'time':time.time(),**value['payload']} if value.get('type')=='send' else {'time':time.time(),'event':'observer_error','kind':value.get('type')}
    with path.open('a') as out:out.write(json.dumps(event)+'\n')
    path.chmod(0o600)
    print(json.dumps(event),flush=True)
script.on('message',message)
try:script.load();time.sleep(100)
finally:session.detach()
