"""Provision one independent Yuanbao Android using the current official APK."""
import hashlib
import json
from pathlib import Path
import subprocess
import time
import zipfile

import requests

BASE = Path('/home/user/redroid-yuanbao')
NAME = 'yuanbao-hpe14-android13'
VOLUME = 'yuanbao-hpe14-android13-data'
IMAGE = 'sha256:18244ad4ab1c36047438bb9c524d8f8d6f848ee8d7537a98483a26c5dda7601f'
PACKAGE = 'com.tencent.hunyuan.app.chat'
APK_URL = 'https://cdn-hybrid-prod.hunyuan.tencent.com/Android/business/yuanbao-release-prod-signed-5040.apk'
ADB = '/home/user/redroid-doubao/linux-tools/platform-tools/adb'
SERIAL = '127.0.0.1:5559'

def run(*args, timeout=30):
    return subprocess.check_output(args, text=True, timeout=timeout, stderr=subprocess.STDOUT).strip()

def save(name, data):
    path = BASE / name
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf8')
    tmp.replace(path)

def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024*1024), b''):
            value.update(block)
    return value.hexdigest()

def main():
    BASE.mkdir(mode=0o700, parents=True, exist_ok=True)
    (BASE / 'artifacts').mkdir(exist_ok=True)
    apk = BASE / 'artifacts/yuanbao-official-5040.apk'
    if not apk.exists():
        session = requests.Session()
        session.trust_env = False
        temp = apk.with_suffix('.download')
        complete_download = temp.exists() and zipfile.is_zipfile(temp)
        request = session.head if complete_download else session.get
        with request(APK_URL, stream=True, timeout=(20, 60)) as response:
            response.raise_for_status()
            assert response.url.startswith('https://cdn-hybrid-prod.hunyuan.tencent.com/')
            if not complete_download:
                with temp.open('wb') as out:
                    for block in response.iter_content(1024*1024):
                        out.write(block)
            with zipfile.ZipFile(temp) as archive:
                assert 'AndroidManifest.xml' in archive.namelist()
            save('apk-download.json', {'url': APK_URL, 'resolved_url': response.url,
                 'downloaded_at': time.time(), 'last_modified': response.headers.get('Last-Modified'),
                 'sha256': digest(temp),
                 'size': temp.stat().st_size,
                 'official_source': 'yuanbao.tencent.com official JS default mobile channel 5040'})
            temp.replace(apk)
    names = run('docker','ps','-a','--format','{{.Names}}').splitlines()
    if NAME not in names:
        assert VOLUME not in run('docker','volume','ls','--format','{{.Name}}').splitlines(), 'Existing unowned volume'
        run('docker','volume','create',VOLUME)
        run('docker','run','-d','--name',NAME,'--restart','unless-stopped',
            '--label','geo.collector=yuanbao','--privileged','--cpus','2','--memory','3g',
            '-p','127.0.0.1:5559:5555','-v',VOLUME+':/data',IMAGE,
            'ro.enable.native.bridge.exec64=1','ro.dalvik.vm.native.bridge=libhoudini.so',
            'androidboot.use_memfd=1','androidboot.redroid_gpu_mode=guest',
            'androidboot.redroid_width=720','androidboot.redroid_height=1280',
            'androidboot.redroid_dpi=320','androidboot.redroid_net_ndns=2',
            'androidboot.redroid_net_dns1=223.5.5.5','androidboot.redroid_net_dns2=119.29.29.29')
    info = json.loads(run('docker','inspect',NAME))[0]
    assert info['Image'] == IMAGE
    assert info['Config']['Labels'].get('geo.collector') == 'yuanbao'
    assert next(m['Name'] for m in info['Mounts'] if m['Destination']=='/data') == VOLUME
    if not info['State']['Running']:
        run('docker','start',NAME)
    end = time.monotonic()+180
    while time.monotonic()<end:
        try:
            if run('docker','exec',NAME,'getprop','sys.boot_completed') == '1':
                break
        except subprocess.CalledProcessError:
            pass
        time.sleep(3)
    else:
        raise RuntimeError('Android boot not ready; preserved for diagnosis')
    if run('docker','exec',NAME,'getprop','persist.sys.locale') != 'zh-CN':
        for key, value in [('persist.sys.locale','zh-CN'),
                           ('persist.sys.language','zh'),('persist.sys.country','CN')]:
            run('docker','exec',NAME,'setprop',key,value)
        run('docker','restart','--timeout','15',NAME, timeout=45)
        end = time.monotonic()+180
        while time.monotonic()<end:
            try:
                if run('docker','exec',NAME,'getprop','sys.boot_completed') == '1':
                    break
            except subprocess.CalledProcessError:
                pass
            time.sleep(3)
        else:
            raise RuntimeError('Chinese locale restart not ready')
    run(ADB,'connect',SERIAL)
    existing = subprocess.run([ADB,'-s',SERIAL,'shell','pm','path',PACKAGE],
                              capture_output=True, text=True, timeout=30).stdout.strip()
    if not existing.startswith('package:'):
        result = run(ADB,'-s',SERIAL,'install',str(apk), timeout=240)
        assert 'Success' in result, result
    component = run(ADB,'-s',SERIAL,'shell','cmd','package','resolve-activity','--brief',PACKAGE).splitlines()[-1]
    assert component.startswith(PACKAGE+'/'), component
    run(ADB,'-s',SERIAL,'shell','cmd','locale','set-app-locales',PACKAGE,
        '--user','0','--locales','zh-CN')
    run(ADB,'-s',SERIAL,'shell','settings','put','system','screen_off_timeout','2147483647')
    run(ADB,'-s',SERIAL,'shell','svc','power','stayon','true')
    run(ADB,'-s',SERIAL,'shell','am','start','-W','-n',component, timeout=60)
    package = run(ADB,'-s',SERIAL,'shell','dumpsys','package',PACKAGE)
    versions = [line.strip() for line in package.splitlines() if 'versionName=' in line or 'versionCode=' in line]
    save('installation.json', {'container': NAME, 'volume': VOLUME, 'image': IMAGE,
         'serial': SERIAL, 'package': PACKAGE, 'activity': component,
         'versions': versions, 'installed_at': time.time(),
         'locale': 'zh-CN', 'login': 'awaiting_user', 'capture_enabled': False})
    print(json.dumps({'container':NAME,'activity':component,'versions':versions,'ready_for_login':True}))

if __name__ == '__main__':
    main()
