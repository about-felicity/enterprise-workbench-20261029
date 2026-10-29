"""Install only the new Yuanbao worker and the native launcher dispatch."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import time
import zipfile

BASE=Path('/home/user/redroid-yuanbao')
PANEL=Path('/opt/monitor/geo-capture')
NAMES={'native_core.py','native_client.py','android_ui.py','delivery.py','worker.py','native_models.js'}


def main():
    backup=PANEL/'backups'/('yuanbao-native-'+str(int(time.time())))
    backup.mkdir(mode=0o700,parents=True)
    launcher=PANEL/'native_entry.py'
    digest=hashlib.sha256(launcher.read_bytes()).hexdigest()
    if digest!='702dcee9d4f40a2825ce7e75a4639741dd181100315b406893c642f1f7f032f5':
        if "config['model']=='yuanbao'" not in launcher.read_text():raise RuntimeError('Native launcher changed; inspect before installing')
    shutil.copy2(launcher,backup/'native_entry.py.before')
    with zipfile.ZipFile('/tmp/yuanbao-capture-runtime.zip') as archive:
        if set(archive.namelist())!=NAMES|{'native_entry.py'}:raise RuntimeError('Unexpected release paths')
        for name in NAMES:
            target=BASE/name
            if target.exists():shutil.copy2(target,backup/(name+'.before'))
            temporary=target.with_suffix(target.suffix+'.install')
            temporary.write_bytes(archive.read(name));temporary.chmod(0o600);temporary.replace(target)
        temporary=launcher.with_suffix('.install');temporary.write_bytes(archive.read('native_entry.py'));temporary.chmod(0o644);temporary.replace(launcher)
    batch='geo-yuanbao-21x5-20261015'
    source=BASE/'batches'/batch/'capture_manifest.json'
    target=PANEL/'panel/jobs'/(batch+'.json')
    if target.exists() and json.loads(target.read_text())!=json.loads(source.read_text()):raise RuntimeError('Batch configuration differs')
    shutil.copy2(source,target);target.chmod(0o644)
    drop=Path('/etc/systemd/system')/('geo-native@'+batch+'.service.d')
    drop.mkdir(exist_ok=True)
    (drop/'acceptance.conf').write_text('[Service]\nEnvironment=YUANBAO_CAPTURE_LIMIT=3\n')
    subprocess.run(['systemctl','daemon-reload'],check=True)
    subprocess.run(['systemctl','start','--no-block','geo-native@'+batch+'.service'],check=True)
    print(json.dumps({'installed':'yuanbao','batch':batch,'acceptance_limit':3,'backup':str(backup),'other_services_restarted':False}))


if __name__=='__main__':main()
