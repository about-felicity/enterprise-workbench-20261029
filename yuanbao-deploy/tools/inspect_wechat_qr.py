"""Observe only QR flow stages, HTTP host/path and status; no auth material."""
import json
from pathlib import Path
import time
import subprocess
import frida

BASE=Path('/home/user/redroid-yuanbao/diagnostics/wechat-qr-20261015')
CODE=r'''
Java.perform(function () {
 function around(cls, name, event) {
  try {
   const C=Java.use(cls);
   C[name].overloads.forEach(function(method) {
    method.implementation=function() {
     send({event:event});
     return method.apply(this,arguments);
    };
   });
   send({event:'observer_ready',stage:event});
  } catch(e) {send({event:'observer_unavailable',stage:event});}
 }
 around('Kp.f','g','wx_auth_start');
 around('oQ.b','t0','wx_signature_request');
 around('Kp.e','onAuthGotQrcode','wx_qrcode_received');
 around('Kp.e','onAuthFinish','wx_auth_callback');
 around('Kp.e','onQrcodeScanned','wx_qrcode_scanned');
 try {
  const U=Java.use('java.net.URL');
  U.openConnection.overloads.forEach(function(method) {
   method.implementation=function() {
    const host=String(this.getHost());
    if (host.indexOf('weixin.qq.com')>=0 || host.indexOf('yuanbao.tencent.com')>=0) {
     const path=String(this.getPath()).replace(/[0-9a-fA-F]{24,}/g,'<id>');
     send({event:'network_open',host:host,path:path});
    }
    return method.apply(this,arguments);
   };
  });
  send({event:'observer_ready',stage:'network'});
 } catch(e) {send({event:'observer_unavailable',stage:'network'});}
});
'''

def main():
    pid=int(subprocess.check_output(['docker','exec','yuanbao-hpe14-android13','pidof','com.tencent.hunyuan.app.chat'],text=True))
    device=frida.get_device_manager().add_remote_device('127.0.0.1:27044')
    session=device.attach(pid,realm='native')
    bridge=Path('/home/user/redroid-doubao/worker-venv/lib/python3.10/site-packages/frida_tools/bridges/java.js').read_text()
    script=session.create_script(bridge+'\nconst Java=bridge;\n'+CODE)
    log=BASE/'flow-events.jsonl'
    def message(value,data):
        if value.get('type')=='send':
            event={'time':time.time(),**value['payload']}
        else:event={'time':time.time(),'event':'observer_error','kind':value.get('type')}
        with log.open('a') as out:out.write(json.dumps(event)+'\n')
        log.chmod(0o600)
        print(json.dumps(event),flush=True)
    script.on('message',message)
    try:
        script.load()
        time.sleep(100)
    finally:session.detach()

if __name__=='__main__':main()
