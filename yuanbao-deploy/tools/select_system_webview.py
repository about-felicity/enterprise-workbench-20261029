"""Invoke the documented X5 compatibility API in this App process only."""
import argparse
import json
from pathlib import Path
import subprocess
import time
import frida

BASE=Path('/home/user/redroid-yuanbao')
CONTAINER='yuanbao-hpe14-android13'
PACKAGE='com.tencent.hunyuan.app.chat'
CODE=r'''
Java.perform(function () {
  try {
    const Qb = Java.use('com.tencent.smtt.sdk.QbSdk');
    Qb.forceSysWebView();
    send({event:'system_webview_requested',forced:Qb.getIsSysWebViewForcedByOuter()});
    if (RECREATE) {
      Java.choose('com.tencent.hunyuan.deps.webview.ui.WebActivity', {
        onMatch: function(activity) {
          if (!activity.isFinishing()) {
            Java.scheduleOnMainThread(function () {
              activity.recreate();
              send({event:'existing_web_activity_recreated'});
            });
          }
        },
        onComplete:function () {}
      });
    }
  } catch (error) {
    send({event:'compatibility_call_failed',error_class:String(error).split(':')[0]});
  }
});
'''

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--recreate',action='store_true')
    parser.add_argument('--hold',type=int,default=30)
    args=parser.parse_args()
    pid=int(subprocess.check_output(['docker','exec',CONTAINER,'pidof',PACKAGE],text=True).strip())
    device=frida.get_device_manager().add_remote_device('127.0.0.1:27044')
    session=device.attach(pid,realm='native')
    bridge=Path('/home/user/redroid-doubao/worker-venv/lib/python3.10/site-packages/frida_tools/bridges/java.js').read_text()
    script=session.create_script(bridge+'\nconst Java=bridge;\nconst RECREATE='+json.dumps(args.recreate)+';\n'+CODE)
    events=[]
    def message(value,data):
        if value.get('type')=='send':
            events.append(value['payload'])
            print(json.dumps(value['payload']),flush=True)
        else:
            events.append({'event':'instrumentation_error','kind':value.get('type')})
            print(json.dumps(events[-1]),flush=True)
    script.on('message',message)
    try:
        script.load()
        time.sleep(min(max(args.hold,1),3600))
    finally:
        (BASE/'diagnostics/login-20261015/system-webview-api.json').write_text(json.dumps({'pid':pid,'events':events,'time':time.time()},indent=2))
        session.detach()

if __name__=='__main__':main()
