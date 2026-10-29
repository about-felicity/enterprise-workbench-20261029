"""Publish daily controls without restarting collectors or changing their data."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import time
import urllib.request

BASE=Path('/opt/monitor/geo-capture');ROOT=BASE/'maintenance/20261016-daily-controls';STAGE=ROOT/'stage'
SOURCE=Path('/opt/monitor/yuanbao_monitor/dashboard/app/api/geo-capture/[...path]/route.ts')
NAMES=['daily_tasks.py','control_panel.py','daily_dispatch.py','fleet_status.py','panel.html','capture_bridge.py','baidu_body_delivery.py']
IMAGE='monitor-dashboard:daily-controls-20261016';PREVIEW='monitor-dashboard-daily-controls-preview'
POINTER=ROOT/'release.json'
def run(*args,timeout=60):return subprocess.check_output(args,text=True,timeout=timeout).strip()
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
def write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True);temp=path.with_name(path.name+'.daily-staged');temp.write_bytes(data);temp.chmod(0o644);temp.replace(path)
def save(data):POINTER.write_text(json.dumps(data,ensure_ascii=False,indent=2))
def jobs():
    with sqlite3.connect(BASE/'panel/control.sqlite') as db:services=[r[0] for r in db.execute('select service from jobs where batch in (select current_batch from settings)')]
    return {s:run('systemctl','show',s,'--property=MainPID,ActiveEnterTimestampMonotonic') for s in services}
def containers():
    names=[n for n in run('docker','ps','--format','{{.Names}}').splitlines() if n not in {'monitor-dashboard',PREVIEW}]
    return {v['Name']:{'image':v['Image'],'started':v['State']['StartedAt']} for v in json.loads(run('docker','inspect',*names))}
def panel(port):
    with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/geo-capture/panel',timeout=20) as r:return json.load(r)
def ready(port):
    for _ in range(30):
        try:
            data=panel(port)
            if len(data['models'])==6 and all('daily' in m for m in data['models']):return
        except Exception:pass
        time.sleep(.5)
    raise RuntimeError('Daily UI did not become ready')
def main(mode):
    if mode=='control':
        assert not POINTER.exists(),'Inspect release before repeating'
        expected={r['server']:r['sha256'] for r in json.loads(Path('/tmp/daily-controls-baseline.json').read_text())['files']}
        before={'status':'staged','at':time.time(),'jobs_before':jobs(),'containers_before':containers(),
                'runtime_before':{n:sha(BASE/n) for n in NAMES},'gateway_before':sha(SOURCE)}
        for n in NAMES:
            if n=='daily_tasks.py':assert not (BASE/n).exists()
            else:assert sha(BASE/n)==expected[str(BASE/n)],n+' drifted'
        backup=ROOT/'backup';backup.mkdir()
        with sqlite3.connect(BASE/'panel/control.sqlite') as source,sqlite3.connect(backup/'control.sqlite') as target:source.backup(target)
        for n in NAMES:
            if (BASE/n).exists():shutil.copy2(BASE/n,backup/n)
            write(BASE/n,(STAGE/n).read_bytes())
        shutil.copy2(SOURCE,backup/'capture-route.ts')
        save(before)
        run('systemctl','restart','geo-monitor-status.service')
        for _ in range(25):
            try:
                with urllib.request.urlopen('http://127.0.0.1:8803/api/panel',timeout=15) as r:data=json.load(r)
                assert all(m['daily']['progress_available'] for m in data['models']);break
            except Exception:time.sleep(.5)
        else:raise RuntimeError('Control readiness failed; inspect backup')
        assert jobs()==before['jobs_before'],'Collector process changed during control publication'
        before.update(status='control_published');save(before)
    elif mode=='preview':
        data=json.loads(POINTER.read_text());assert data['status']=='control_published'
        assert sha(SOURCE)==data['gateway_before']
        old=run('docker','inspect','monitor-dashboard','--format','{{.Image}}')
        rollback='monitor-dashboard:before-daily-controls-'+str(int(time.time()))
        run('docker','tag',old,rollback);data.update(original_image=old,rollback_tag=rollback);save(data)
        (ROOT/'Dockerfile').write_text(f'FROM {rollback}\nCOPY stage/capture-route.ts /dashboard/app/api/geo-capture/[...path]/route.ts\nCOPY stage/capture-gateway.test.mjs /dashboard/tests/capture-gateway.test.mjs\nWORKDIR /dashboard\nRUN node --experimental-strip-types --test tests/capture-gateway.test.mjs tests/creation-gateway.test.mjs\nRUN npm run build\n')
        subprocess.run(['docker','build','-t',IMAGE,str(ROOT)],check=True,timeout=600)
        run('docker','run','-d','--name',PREVIEW,'--network','host',IMAGE,'npm','run','start','--','-H','0.0.0.0','-p','3001')
        ready(3001);data['status']='preview';save(data)
    elif mode=='publish':
        data=json.loads(POINTER.read_text());assert data['status']=='preview'
        assert json.loads((ROOT/'qa-preview.json').read_text())['passed']
        assert run('docker','inspect','monitor-dashboard','--format','{{.Image}}')==data['original_image']
        compose=['docker','compose','-p','local-server','-f','/opt/monitor/deploy/local-server/docker-compose.yml','up','-d','--no-deps','--no-build','--force-recreate','dashboard']
        run('docker','tag',IMAGE,'monitor-dashboard:local')
        try:run(*compose);ready(3000)
        except Exception:
            run('docker','tag',data['rollback_tag'],'monitor-dashboard:local');run(*compose);raise
        write(SOURCE,(STAGE/'capture-route.ts').read_bytes())
        # A persistent actor applies only explicit daily intents or scheduled
        # future-day plans. Installation does not enqueue today's work.
        plan=read_json(BASE/'daily_plan.json');shutil.copy2(BASE/'daily_plan.json',ROOT/'backup/daily_plan.json')
        plan['daily_control_enabled']=True;write(BASE/'daily_plan.json',json.dumps(plan,ensure_ascii=False,indent=2).encode())
        import sys
        sys.path.insert(0,str(BASE))
        from control_panel import Controller,MODELS
        from daily_tasks import DailyTasks,today
        control=Controller();daily=DailyTasks(control)
        with control.connect() as db:
            for model in MODELS:daily.ensure_scheduled(db,model,today(),'observing')
        service='''[Unit]
Description=GEO daily task controls and safe continuation
After=geo-monitor-status.service docker.service
Wants=geo-monitor-status.service
[Service]
Type=simple
WorkingDirectory=/opt/monitor/geo-capture
ExecStart=/opt/monitor/geo-capture/venv/bin/python -u -B /opt/monitor/geo-capture/daily_tasks.py
Restart=always
RestartSec=5s
MemoryMax=300M
TasksMax=128
[Install]
WantedBy=multi-user.target
'''
        write(Path('/etc/systemd/system/geo-daily-control.service'),service.encode())
        run('systemctl','daemon-reload');run('systemctl','enable','--now','geo-daily-control.service')
        assert containers()==data['containers_before'],'Unrelated containers changed'
        with sqlite3.connect(BASE/'panel/control.sqlite') as db:requests=db.execute("select count(*) from daily_tasks where desired!='observing'").fetchone()[0]
        if not requests:assert jobs()==data['jobs_before'],'Collectors changed without an operator request'
        data.update(status='published',published_at=time.time(),jobs_after=jobs(),containers_unchanged=True,day_requests=requests);save(data)
    print(json.dumps({'mode':mode,'status':json.loads(POINTER.read_text())['status']}))
def read_json(path):return json.loads(path.read_text())
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['control','preview','publish']);main(p.parse_args().mode)
