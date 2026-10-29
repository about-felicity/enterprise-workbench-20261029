import json,subprocess,time
from pathlib import Path
import frida
pid=int(subprocess.check_output(['docker','exec','yuanbao-hpe14-android13','pidof','com.tencent.hunyuan.app.chat']))
session=frida.get_device_manager().add_remote_device('127.0.0.1:27044').attach(pid,realm='native')
bridge=Path('/home/user/redroid-doubao/worker-venv/lib/python3.10/site-packages/frida_tools/bridges/java.js').read_text()
code=r'''
Java.perform(function(){
 for (const name of ['com.tencent.hunyuan.mpcommon.generated.biz.chat.viewmodel.ChatListViewModel','com.tencent.hunyuan.mpcommon.generated.biz.chat.viewmodel.ChatPageScopeViewModel','com.tencent.hunyuan.mpcommon.generated.biz.chat.viewmodel.answer.ChatAnswerMessageContentViewModel','com.tencent.hunyuan.mpcommon.generated.biz.chat.viewmodel.answer.entity.YbMarkdownViewModel']) {
  try { const C=Java.use(name);const methods=C.class.getMethods();const result=[];
   for(let i=0;i<methods.length;i++){const n=String(methods[i].getName());result.push(String(methods[i]));}
   send({name:name,methods:result,fields:Array.from(C.class.getDeclaredFields()).map(String),constructors:Array.from(C.class.getDeclaredConstructors()).map(String)});Java.choose(name,{onMatch:function(o){send({name:name,instance:true});},onComplete:function(){}});
  }catch(e){send({name:name,unavailable:true});}
 }
});
'''
script=session.create_script(bridge+'\nconst Java=bridge;\n'+code)
script.on('message',lambda v,d:print(json.dumps(v.get('payload',{'kind':v.get('type')})),flush=True))
script.load();time.sleep(3);session.detach()


