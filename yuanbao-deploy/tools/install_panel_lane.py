"""Add the verified Yuanbao lane without restarting capture or analysis."""
from contextlib import closing
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import time
import zipfile

BASE=Path('/opt/monitor/geo-capture')
YB=Path('/home/user/redroid-yuanbao')
STAGE=BASE/'releases/yuanbao-control-20261015'
EXPECTED={'control_panel.py':'1de956a52e3d2e247561de7c92ecebe6071dfc50e9f88f453f9a1ee0e918c5c8',
          'fleet_status.py':'6bde8d880a5e0a4b8b667980d0c18cfa249f791f8e1b25cecf647cbd928faa81',
          'login_probe.py':'4c3d62f3ce0000710ea42957c8a16da69b53c2825f1c9b56692763b04300a346'}
ALLOWED=set(EXPECTED)|{'yuanbao-login-probe.py','worker.py','frontend/Dockerfile','frontend/app/CaptureControl.tsx',
 'frontend/app/api/geo-capture/[...path]/route.ts','frontend/tests/capture-gateway.test.mjs'}


def main():
    for name,digest in EXPECTED.items():
        if hashlib.sha256((BASE/name).read_bytes()).hexdigest()!=digest:raise RuntimeError('Live source changed: '+name)
    root=YB/'batches/geo-yuanbao-21x5-20261015'
    health=json.loads((root/'bridge_health.json').read_text())
    audit=json.loads((root/'capture-audit.json').read_text())
    assert health['captured']==health['geo_processed']==3 and audit['all_processed_database_fidelity']
    assert not audit['duplicate_send_clicks'] and not audit['duplicate_conversations']
    manifest=json.loads((root/'capture_manifest.json').read_text())
    assert manifest['questions']==json.loads((BASE/'config/wenxin_card.json').read_text())['questions']
    backup=BASE/'backups'/('yuanbao-panel-'+str(int(time.time())));backup.mkdir(mode=0o700)
    for name in [*EXPECTED,'fleet.json']:shutil.copy2(BASE/name,backup/name)
    with closing(sqlite3.connect(BASE/'panel/control.sqlite')) as source,closing(sqlite3.connect(backup/'control.sqlite')) as dest:source.backup(dest)
    with zipfile.ZipFile('/tmp/yuanbao-panel-lane.zip') as archive:
        if set(archive.namelist())!=ALLOWED:raise RuntimeError('Unexpected release paths')
        for name in EXPECTED:
            temporary=(BASE/name).with_suffix('.yuanbao-install')
            temporary.write_bytes(archive.read(name));temporary.chmod(0o644);temporary.replace(BASE/name)
        (YB/'login_probe.py').write_bytes(archive.read('yuanbao-login-probe.py'))
        (YB/'worker.py').write_bytes(archive.read('worker.py'))
        for name in archive.namelist():
            if not name.startswith('frontend/'):continue
            target=STAGE/name[len('frontend/'):];target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(archive.read(name));target.chmod(0o644)
    fleet=json.loads((BASE/'fleet.json').read_text())
    assert len(fleet['collectors'])==5 and not any(l['name']=='元宝' for l in fleet['collectors'])
    fleet['collectors'].append({'name':'元宝','service':'geo-native@'+root.name+'.service','health':str(root/'bridge_health.json'),'planned':105})
    if 'yuanbao-hpe14-android13' not in fleet['containers']:fleet['containers'].append('yuanbao-hpe14-android13')
    temp=BASE/'fleet.yuanbao-install';temp.write_text(json.dumps(fleet,ensure_ascii=False,indent=2));temp.chmod(0o644);temp.replace(BASE/'fleet.json')
    sys.path.insert(0,str(BASE));from control_panel import Controller
    result=Controller(BASE).all();assert len(result['models'])==6
    yuanbao=next(m for m in result['models'] if m['id']=='yuanbao')
    assert yuanbao['current']['captured']==yuanbao['current']['processed']==3
    subprocess.run(['systemctl','restart','geo-monitor-status.service'],check=True)
    record={'time':time.time(),'backup':str(backup),'stage':str(STAGE),'status':'backend_installed','models':6,'capture_queues_reset':False}
    (BASE/'yuanbao_control_release.json').write_text(json.dumps(record,indent=2))
    print(json.dumps(record))


if __name__=='__main__':main()
