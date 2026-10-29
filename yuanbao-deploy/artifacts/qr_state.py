import json,subprocess,time
from pathlib import Path
import frida
pid=int(subprocess.check_output(['docker','exec','yuanbao-hpe14-android13','pidof','com.tencent.hunyuan.app.chat']))
session=frida.get_device_manager().add_remote_device('127.0.0.1:27044').attach(pid,realm='native')
bridge=Path('/home/user/redroid-doubao/worker-venv/lib/python3.10/site-packages/frida_tools/bridges/java.js').read_text()
code=r'''
Java.perform(function(){
 const C=Java.use('com.tencent.mm.opensdk.diffdev.a.a');
 const list=C.class.getDeclaredField('c');list.setAccessible(true);
 Java.choose('com.tencent.mm.opensdk.diffdev.a.a',{onMatch:function(o){send({event:'sdk_state',listeners:Java.use('java.util.List').size.call(Java.cast(list.get(o),Java.use('java.util.List'))),hasTask:o.d.value!==null});},onComplete:function(){}});
 Java.choose('com.tencent.mm.opensdk.diffdev.a.d$a',{onMatch:function(o){send({event:'qr_result_present',imageBytes:o.s.value?o.s.value.length:0});},onComplete:function(){}});
 Java.choose('Up.m',{onMatch:function(o){send({event:'decode_coroutine_present'});},onComplete:function(){}});
});
'''
script=session.create_script(bridge+'\nconst Java=bridge;\n'+code)
script.on('message',lambda v,d:print(json.dumps(v.get('payload',{'event':'error','kind':v.get('type')})),flush=True))
script.load();time.sleep(5);session.detach()
