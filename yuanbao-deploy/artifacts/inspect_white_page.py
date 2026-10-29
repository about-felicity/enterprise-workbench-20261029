import json,re,subprocess,time
from pathlib import Path
import frida
NAME='yuanbao-hpe14-android13'
base=Path('/home/user/redroid-yuanbao/diagnostics/wechat-after-scan-20261015')
base.mkdir(mode=0o700,exist_ok=True)
info=json.loads(subprocess.check_output(['docker','inspect',NAME]))[0]
mount=next(m for m in info['Mounts'] if m['Destination']=='/data')
app=Path(mount['Source'])/'data/com.tencent.hunyuan.app.chat'
config=app/'app_tbs_64/core_private/tbs_pv_config'
text=config.read_text(errors='replace')
value=re.search(r'^disabled_core_version\s*[=:]\s*(\d+)',text,re.M)
print(json.dumps({'disabled_core_version':value[1] if value else None}))
raw=subprocess.check_output(['docker','exec',NAME,'logcat','-d','-t','12000'],timeout=30)
(base/'logcat-private.txt').write_bytes(raw);(base/'logcat-private.txt').chmod(0o600)
patterns=['isX5webview:false','isX5webview:true','WebViewFactory','sandboxed_process','SandboxedProcessService','SIGSEGV','onAuthFinish','onAuthGotQrcode','onQrcodeScanned','net::ERR_','QrLoginViewModel','Chromium','chromium','WebActivity','HYWebActivity']
summary=[]
for line in raw.decode(errors='replace').splitlines():
    for p in patterns:
        if p in line:
            entry={'time':line[:18],'marker':p}
            err=re.search(r'net::(ERR_[A-Z_]+)',line)
            if err:entry['net_error']=err[1]
            summary.append(entry)
print(json.dumps({'log_markers':summary[-100:]}))
pid=int(subprocess.check_output(['docker','exec',NAME,'pidof','com.tencent.hunyuan.app.chat']))
session=frida.get_device_manager().add_remote_device('127.0.0.1:27044').attach(pid,realm='native')
bridge=Path('/home/user/redroid-doubao/worker-venv/lib/python3.10/site-packages/frida_tools/bridges/java.js').read_text()
code=r'''
Java.perform(function(){
 const Uri=Java.use('android.net.Uri');
 Java.scheduleOnMainThread(function(){
  Java.choose('android.webkit.WebView',{
   onMatch:function(v){try{
    const raw=v.getUrl();const u=raw ? Uri.parse(raw) : null;
    send({event:'system_webview',host:u?String(u.getHost()):null,path:u?String(u.getPath()):null,progress:v.getProgress(),width:v.getWidth(),height:v.getHeight()});
    const Callback=Java.registerClass({name:'org.geo.diagnostics.PageMetadata'+Date.now(),implements:[Java.use('android.webkit.ValueCallback')],methods:{onReceiveValue:function(value){send({event:'page_metadata',value:String(value)});}}});
    v.evaluateJavascript('(function(){return JSON.stringify({ready:document.readyState,bodyChildren:document.body?document.body.children.length:0,textLength:document.body?document.body.innerText.length:0,scripts:document.scripts.length,rootChildren:document.getElementById("root")?document.getElementById("root").children.length:-1})})()',Callback.$new());
   }catch(e){send({event:'webview_inspect_error',kind:String(e).split(':')[0]});}},onComplete:function(){send({event:'webviews_done'});}
  });
 });
});
'''
script=session.create_script(bridge+'\nconst Java=bridge;\n'+code)
def message(v,d):
    item=v.get('payload',{'event':'observer_error','kind':v.get('type')})
    print(json.dumps(item),flush=True)
    with (base/'metadata.jsonl').open('a') as out:out.write(json.dumps({'time':time.time(),**item})+'\n')
script.on('message',message)
script.load();time.sleep(8);session.detach()
