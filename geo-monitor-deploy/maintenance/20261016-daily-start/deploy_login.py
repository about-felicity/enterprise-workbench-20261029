"""Stage and publish only the control service and frontend for manual login."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import time
import urllib.request
import zipfile

BASE = Path('/opt/monitor/geo-capture')
ROOT = BASE / 'maintenance/20261016-manual-login'
STAGE = ROOT / 'stage'
RUNTIME = ['control_panel.py','fleet_status.py','panel.html','manual_login.py',
           'deepseek_login_ui.py','deepseek_login.html','baidu_body_delivery.py']
JOBS = ['geo-web@geo-panel-deepseek-20261016-094039-dc64b7e1.service',
        'geo-native@geo-panel-yuanbao-20261016-100013-89d43fdd.service']
SOURCE = Path('/opt/monitor/yuanbao_monitor/dashboard/app')
FRONTEND = ['Dashboard.tsx','api/geo-capture/[...path]/route.ts']
IMAGE = 'monitor-dashboard:manual-login-20261016'
PREVIEW = 'monitor-dashboard-manual-login-preview'
POINTER = ROOT / 'release.json'

def run(*args, timeout=60):
    return subprocess.check_output(args,text=True,timeout=timeout).strip()

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(value):POINTER.write_text(json.dumps(value,ensure_ascii=False,indent=2))
def jobs():return {job:run('systemctl','show',job,'--property=MainPID,ActiveEnterTimestampMonotonic') for job in JOBS}
def containers():
    names=[name for name in run('docker','ps','--format','{{.Names}}').splitlines() if name not in {'monitor-dashboard',PREVIEW}]
    return {v['Name']:{'image':v['Image'],'started':v['State']['StartedAt']} for v in json.loads(run('docker','inspect',*names))}

def panel(port):
    with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/geo-capture/panel',timeout=15) as response:return json.load(response)

def ready(port):
    for _ in range(30):
        try:
            if len(panel(port)['models'])==6:return
        except Exception:pass
        time.sleep(.5)
    raise RuntimeError('Frontend did not become ready')

def main(mode):
    if mode=='stage':
        assert not POINTER.exists() or json.loads(POINTER.read_text())['status']=='staged','Inspect existing release before repeating'
        STAGE.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile('/tmp/manual-login-input-20261016.zip') as archive:
            for name in archive.namelist():assert (STAGE/name).resolve().is_relative_to(STAGE.resolve())
            archive.extractall(STAGE)
        for pattern in ['test_control_panel.py','test_manual_login.py','test_baidu_body_delivery.py']:
            subprocess.run([str(BASE/'venv/bin/python'),'-B','-m','unittest','discover','-s',str(STAGE/'tests'),'-p',pattern,'-v'],
                           cwd=STAGE,env={**os.environ,'PYTHONPATH':str(STAGE)+os.pathsep+str(BASE)},check=True,timeout=40)
        manifest=json.loads(Path('/tmp/geo-unified-manifest.json').read_text())
        expected={item['server']:item['sha256'] for item in manifest['files']}
        expected.update({str(BASE/'fleet_status.py'):'8cce44ce437185f90133ff81ecebdaaecd12f3e0c026ab16896ef1f84455a5f2'})
        for name in RUNTIME:
            target=BASE/name
            if str(target) in expected:assert digest(target)==expected[str(target)],name+' changed since baseline'
            else:assert not target.exists(),name+' unexpectedly exists'
        value={'status':'staged','at':time.time(),'jobs_before':jobs(),'containers_before':containers(),
               'runtime_before':{name:digest(BASE/name) if (BASE/name).exists() else None for name in RUNTIME},
               'frontend_before':{name:digest(SOURCE/name) for name in FRONTEND}}
        save(value)
        print(json.dumps({'status':'staged','tests':23}))
    elif mode=='control':
        value=json.loads(POINTER.read_text());assert value['status']=='staged'
        backup=ROOT/'backup';backup.mkdir()
        with sqlite3.connect(BASE/'panel/control.sqlite') as source,sqlite3.connect(backup/'control.sqlite') as dest:source.backup(dest)
        for name in RUNTIME:
            target=BASE/name
            assert (digest(target) if target.exists() else None)==value['runtime_before'][name]
            if target.exists():shutil.copy2(target,backup/name)
            stage=target.with_suffix(target.suffix+'.login-staged');stage.write_bytes((STAGE/name).read_bytes());stage.chmod(0o644);stage.replace(target)
        run('systemctl','restart','geo-monitor-status.service')
        for _ in range(20):
            try:
                with urllib.request.urlopen('http://127.0.0.1:8803/api/panel',timeout=5) as response:data=json.load(response)
                assert len(data['models'])==6 and all('readiness' in m for m in data['models'])
                break
            except Exception:time.sleep(.5)
        else:raise RuntimeError('Control readiness check failed; inspect backups')
        assert jobs()==value['jobs_before'],'Collector process changed during control deployment'
        value.update(status='control_published',control_at=time.time());save(value)
        print(json.dumps({'status':'control_published','collector_processes_unchanged':True}))
    elif mode=='preview':
        value=json.loads(POINTER.read_text());assert value['status']=='control_published'
        for name in FRONTEND:assert digest(SOURCE/name)==value['frontend_before'][name]
        old=run('docker','inspect','monitor-dashboard','--format','{{.Image}}')
        rollback='monitor-dashboard:before-manual-login-'+str(int(time.time()))
        run('docker','tag',old,rollback)
        value.update(original_image=old,rollback_tag=rollback);save(value)
        (ROOT/'Dockerfile').write_text(f'FROM {rollback}\nCOPY stage/Dashboard.tsx /dashboard/app/Dashboard.tsx\nCOPY stage/capture-route.ts /dashboard/app/api/geo-capture/[...path]/route.ts\nWORKDIR /dashboard\nRUN node --experimental-strip-types --test tests/capture-gateway.test.mjs tests/creation-gateway.test.mjs\nRUN npm run build\n')
        subprocess.run(['docker','build','-t',IMAGE,str(ROOT)],check=True,timeout=600)
        run('docker','run','-d','--name',PREVIEW,'--network','host',IMAGE,'npm','run','start','--','-H','0.0.0.0','-p','3001')
        for _ in range(25):
            try:assert len(panel(3001)['models'])==6;break
            except Exception:time.sleep(1)
        else:raise RuntimeError('Frontend preview unavailable')
        value.update(status='preview');save(value);print('{"status":"preview","port":3001}')
    elif mode=='publish':
        value=json.loads(POINTER.read_text());assert value['status']=='preview'
        assert json.loads((ROOT/'qa.json').read_text())['passed']
        for name in FRONTEND:assert digest(SOURCE/name)==value['frontend_before'][name]
        assert run('docker','inspect','monitor-dashboard','--format','{{.Image}}')==value['original_image']
        compose=['docker','compose','-p','local-server','-f','/opt/monitor/deploy/local-server/docker-compose.yml','up','-d','--no-deps','--no-build','--force-recreate','dashboard']
        run('docker','tag',IMAGE,'monitor-dashboard:local')
        try:
            run(*compose)
            ready(3000)
            for name,local in zip(FRONTEND,['Dashboard.tsx','capture-route.ts']):
                backup=ROOT/'backup'/('Dashboard.before.tsx' if name=='Dashboard.tsx' else 'capture-route.before.ts')
                shutil.copy2(SOURCE/name,backup);shutil.copy2(STAGE/local,SOURCE/name)
        except Exception:
            run('docker','tag',value['rollback_tag'],'monitor-dashboard:local');run(*compose);ready(3000);raise
        assert containers()==value['containers_before'],'Unrelated containers changed'
        value.update(status='published',published_at=time.time(),jobs_after=jobs(),containers_unchanged=True);save(value)
        print('{"status":"published","unrelated_containers_unchanged":true}')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('mode',choices=['stage','control','preview','publish']);main(parser.parse_args().mode)
