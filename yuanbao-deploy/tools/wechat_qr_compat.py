"""Yuanbao 2.88.0: SDK QR fallback and official system WebView selection.

Changes cosmetic QR decoding, WebView selection, and displays the official
verification QR already held by the page. WeChat signatures, QR images,
polling, scan confirmation and login callbacks remain App-owned.
No image contents, URLs, identifiers or credentials are logged.
"""
import json
from pathlib import Path
import subprocess
import time
import frida

CONTAINER = 'yuanbao-hpe14-android13'
PACKAGE = 'com.tencent.hunyuan.app.chat'
BASE = Path('/home/user/redroid-yuanbao')
ADB = '/home/user/redroid-doubao/linux-tools/platform-tools/adb'
APK_SHA256 = 'b2d6f674358bbc27b10e800bafd49ba4fc596291142148d7d09494097348c7dd'
BRIDGE = Path('/home/user/redroid-doubao/worker-venv/lib/python3.10/site-packages/frida_tools/bridges/java.js')
CODE = r'''
Java.perform(function () {
    const Qb = Java.use('com.tencent.smtt.sdk.QbSdk');
    Qb.forceSysWebView();
    const WebView = Java.use('com.tencent.smtt.sdk.WebView');
    function injectPage(view, delay) {
        const retained = Java.retain(view);
        setTimeout(function () {
            Java.perform(function () {
                Java.scheduleOnMainThread(function () {
                    try {
                        const url = retained.getUrl();
                        if (url && String(url).startsWith('https://yuanbao.tencent.com/e/login') && retained.getWidth() > 0)
                            retained.evaluateJavascript(PAGE_CODE, null);
                    } catch (_) {}
                    finally { retained.$dispose(); }
                });
            });
        }, delay);
    }
    WebView.$init.overloads.forEach(function (constructor) {
        constructor.implementation = function () {
            // The SDK refreshes tbs_pv_config and removes the disk-only core
            // exception. Use its official per-process compatibility API at
            // each new WebView, before an incompatible X5 renderer is chosen.
            Qb.forceSysWebView();
            const result = constructor.apply(this, arguments);
            injectPage(this, 8000);
            return result;
        };
    });
    WebView.loadUrl.overloads.forEach(function (load) {
        load.implementation = function () {
            const result = load.apply(this, arguments);
            if (arguments.length && String(arguments[0]).startsWith('https://yuanbao.tencent.com/e/login')) {
                injectPage(this, 3000);
                injectPage(this, 10000);
            }
            return result;
        };
    });
    Java.choose('com.tencent.smtt.sdk.WebView', {
        onMatch:function (view) { injectPage(view, 1000); },
        onComplete:function () {}
    });
    send({event:'system_webview_forced',forced:Qb.getIsSysWebViewForcedByOuter()});
    const Qbar = Java.use('com.tencent.qbar.b');
    const method = Qbar.b.overload('android.app.Application', '[B');
    method.implementation = function (application, bytes) {
        // Hook the synchronized decoder boundary rather than the tiny suspend
        // wrapper that ART may inline. Restrict the fallback to login styling.
        const login = Java.backtrace({limit:12}).frames.some(function (frame) {
            return frame.className === 'Up.m';
        });
        if (!login) return method.call(this, application, bytes);
        // Null is the App's existing QBar-failure result. Its coroutine then
        // invokes Up.s.U0(original SDK bytes, "qbar-fail", its continuation).
        send({event:'sdk_image_fallback_requested'});
        return null;
    };
    const Bitmap = Java.use('Up.p');
    const decode = Bitmap.invokeSuspend.overload('java.lang.Object');
    decode.implementation = function (result) {
        const bitmap = decode.call(this, result);
        send({event:bitmap === null ? 'sdk_bitmap_failed' : 'sdk_bitmap_ready'});
        return bitmap;
    };
    send({event:'compat_ready',scope:'qr_styling_and_system_webview'});
});
'''

def command(*args):
    return subprocess.check_output(args, text=True, timeout=20).strip()

def event(value):
    item = {'time':time.time(), **value}
    path = BASE/'diagnostics/wechat-qr-20261015/compat-events.jsonl'
    with path.open('a') as stream:
        stream.write(json.dumps(item)+'\n')
    path.chmod(0o600)
    health = BASE/'health/wechat-qr-compat.json'
    health.parent.mkdir(mode=0o700, exist_ok=True)
    temporary = health.with_suffix('.tmp')
    temporary.write_text(json.dumps(item)+'\n')
    temporary.chmod(0o600)
    temporary.replace(health)
    print(json.dumps(item), flush=True)

def validate():
    info = json.loads(command('docker','inspect',CONTAINER))[0]
    if info['Config'].get('Labels',{}).get('geo.collector') != 'yuanbao':
        raise RuntimeError('Container ownership changed')
    if not any(m.get('Name') == CONTAINER+'-data' and m['Destination']=='/data' for m in info['Mounts']):
        raise RuntimeError('Unexpected data volume')
    package = command('docker','exec',CONTAINER,'dumpsys','package',PACKAGE)
    if 'versionCode=66517035 ' not in package or 'versionName=2.88.0' not in package:
        raise RuntimeError('Unsupported APK version; compatibility hook not applied')
    apk = command('docker','exec',CONTAINER,'pm','path',PACKAGE)
    if not apk.startswith('package:/data/app/') or '\n' in apk:
        raise RuntimeError('Unexpected APK layout')
    digest = command('docker','exec',CONTAINER,'sha256sum',apk[len('package:'):]).split()[0]
    if digest != APK_SHA256:
        raise RuntimeError('APK digest changed; compatibility hook not applied')

def transport():
    command(ADB,'connect','127.0.0.1:5559')
    mappings = command(ADB,'forward','--list').splitlines()
    for mapping in mappings:
        parts = mapping.split()
        if len(parts)>1 and parts[1]=='tcp:27044' and parts != ['127.0.0.1:5559','tcp:27044','tcp:27042']:
            raise RuntimeError('Diagnostic forward belongs to another device')
    command(ADB,'-s','127.0.0.1:5559','forward','tcp:27044','tcp:27042')
    try:
        command('docker','exec',CONTAINER,'pidof','frida-server')
    except subprocess.CalledProcessError:
        # Disable preload: Android helper preload aborts in this Redroid image.
        command('docker','exec','-d',CONTAINER,'/data/local/tmp/frida-server',
                '--disable-preload','--listen','127.0.0.1:27042')
        time.sleep(1)

def main():
    validate()
    session = None
    attached = None
    while True:
        try:
            pid = command('docker','exec',CONTAINER,'pidof',PACKAGE)
            if not pid or len(pid.split()) != 1 or not pid.isdecimal():
                # During an App process replacement pidof can briefly return
                # both old and new PIDs. Wait instead of attaching arbitrarily.
                time.sleep(2)
                continue
            if pid != attached:
                if session:
                    try:session.detach()
                    except Exception:pass
                validate()
                transport()
                device=frida.get_device_manager().add_remote_device('127.0.0.1:27044')
                session=device.attach(int(pid),realm='native')
                page_code=(BASE/'tools/show_official_verification_qr.js').read_text()
                script=session.create_script(BRIDGE.read_text()+'\nconst Java=bridge;\nconst PAGE_CODE='+json.dumps(page_code)+';\n'+CODE)
                def message(value,data):
                    if value.get('type') == 'send':event(value['payload'])
                    else:event({'event':'compat_script_error','kind':value.get('type')})
                script.on('message',message)
                script.load()
                attached=pid
            if session and session.is_detached:
                attached=None
            time.sleep(2)
        except subprocess.CalledProcessError:
            attached=None
            time.sleep(2)
        except Exception as error:
            event({'event':'compat_error','error_class':type(error).__name__})
            attached=None
            time.sleep(5)

if __name__=='__main__':main()
