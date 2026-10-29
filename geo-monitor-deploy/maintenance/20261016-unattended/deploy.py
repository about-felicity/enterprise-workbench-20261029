"""Atomic source update and daily timer. Never pause/restart a running collector."""
from datetime import datetime,timedelta
import hashlib
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import time
import uuid
from zoneinfo import ZoneInfo
import requests

BASE=Path('/opt/monitor/geo-capture')
ROOT=BASE/'maintenance/20261016-unattended'
STAGE=ROOT/'stage'
POINTER=ROOT/'deployed.json'
ROUNDS={'doubao1':10,'doubao2':10,'wenxin_card':8,'baidu_ai':5,'yuanbao':8,'deepseek':3}
http=requests.Session();http.trust_env=False

def run(*args):return subprocess.check_output(args,text=True,timeout=35).strip()
def panel():
    response=http.get('http://127.0.0.1:8803/api/panel',timeout=20);response.raise_for_status();return response.json()
def pids(data):
    with sqlite3.connect(BASE/'panel/control.sqlite') as db:
        services=dict(db.execute('select model,service from jobs where batch in (select current_batch from settings)'))
    return {m:run('systemctl','show',services[m],'--property=MainPID,ActiveEnterTimestampMonotonic') for m in services}
def write_target(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    stage=path.with_name(path.name+'.unattended-staged');stage.write_bytes(data);stage.chmod(0o644);stage.replace(path)

assert not POINTER.exists(),'Inspect existing deployment before repeating'
assert json.loads((ROOT/'tests.json').read_text())['passed']
manifest=json.loads((STAGE/'manifest.json').read_text())
before=panel();before_pids=pids(before)
questions=next(m['settings']['questions'] for m in before['models'] if m['id']=='deepseek')
assert len(questions)==21
backup=ROOT/'backup';backup.mkdir(exist_ok=False)
for item in manifest['files']:
    target=Path(item['target'])
    actual=hashlib.sha256(target.read_bytes()).hexdigest() if target.exists() else None
    assert actual==item['before'],item['target']+' drifted'
    assert hashlib.sha256((STAGE/item['stage']).read_bytes()).hexdigest()==item['sha256']
    if target.exists():
        saved=backup/str(target).lstrip('/');saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,saved)
with sqlite3.connect(BASE/'panel/control.sqlite') as source,sqlite3.connect(backup/'control.sqlite') as dest:source.backup(dest)
(ROOT/'before.json').write_text(json.dumps({'at':time.time(),'models':before['models'],'pids':before_pids},ensure_ascii=False,indent=2))
order={'unattended_core.py':0,'question_only_core.py':1,'journal.py':2,'collector.py':3,'search_recovery.py':4,'cli.py':5,'question_only_worker.py':6,'capture_bridge.py':7}
for item in sorted(manifest['files'],key=lambda x:order.get(Path(x['stage']).name,8)):
    write_target(Path(item['target']),(STAGE/item['stage']).read_bytes())

# Existing children adopt recovery policy on their next CLI invocation; no
# signal is sent to a current collector or Android process.
write_target(BASE/'unattended_policy.json',json.dumps({'enabled':True,'version':1,'auth_exit_status':77,'pause_markers_respected':True}).encode())
actions=[]
for model,rounds in ROUNDS.items():
    data=panel();item=next(m for m in data['models'] if m['id']==model)
    action={'model':model,'id':uuid.uuid4().hex,'payload':{'questions':questions,'rounds':rounds,
            'interval':600 if model=='deepseek' else item['settings']['interval'],'revision':item['revision']}}
    actions.append(action);(ROOT/'settings-actions.json').write_text(json.dumps(actions,ensure_ascii=False,indent=2))
    reply=http.post('http://127.0.0.1:8803/api/control/'+model+'/settings',json=action['payload'],
                    headers={'Origin':'http://127.0.0.1:8803','X-CSRF-Token':data['csrf'],'X-Action-Id':action['id']},timeout=25)
    reply.raise_for_status();action['result']=reply.json();assert action['result']['ok']
    (ROOT/'settings-actions.json').write_text(json.dumps(actions,ensure_ascii=False,indent=2))

start=(datetime.now(ZoneInfo('Asia/Shanghai')).date()+timedelta(days=1)).isoformat()
plan={'enabled':True,'time':'05:00','timezone':'Asia/Shanghai','start_date':start,'models':list(ROUNDS),
      'normal_completion':True,'question_count':21,'rounds':ROUNDS}
assert not (BASE/'daily_plan.json').exists(),'Existing schedule requires review'
write_target(BASE/'daily_plan.json',json.dumps(plan,ensure_ascii=False,indent=2).encode())
for kind in ['web','native']:
    target=Path('/etc/systemd/system/geo-'+kind+'@.service.d/20-unattended.conf')
    assert not target.exists(),'Existing recovery override requires review'
    write_target(target,b'[Unit]\nStartLimitIntervalSec=0\n[Service]\nRestart=on-failure\nRestartPreventExitStatus=\nRestartPreventExitStatus=77\nRestartSec=15s\n')
service=Path('/etc/systemd/system/geo-daily-dispatch.service')
timer=Path('/etc/systemd/system/geo-daily-dispatch.timer')
assert not service.exists() and not timer.exists()
write_target(service,b'[Unit]\nDescription=GEO daily configured batch dispatch\nAfter=network-online.target docker.service geo-monitor-status.service\nWants=network-online.target geo-monitor-status.service\n[Service]\nType=oneshot\nUser=root\nWorkingDirectory=/opt/monitor/geo-capture\nExecStart=/opt/monitor/geo-capture/venv/bin/python -B /opt/monitor/geo-capture/daily_dispatch.py\nTimeoutStartSec=240\nMemoryMax=256M\nTasksMax=128\nUMask=0077\n')
write_target(timer,b'[Unit]\nDescription=GEO daily 05:00 Asia Shanghai timer\n[Timer]\nOnCalendar=*-*-* 05:00:00 Asia/Shanghai\nOnUnitInactiveSec=5min\nPersistent=true\nAccuracySec=1s\nRandomizedDelaySec=0\nUnit=geo-daily-dispatch.service\n[Install]\nWantedBy=timers.target\n')
run('systemctl','daemon-reload')
run('systemctl','enable','--now','geo-daily-dispatch.timer')
run('systemctl','restart','geo-monitor-status.service')
for _ in range(20):
    try:after=panel();assert after['schedule']['time']=='05:00';break
    except Exception:time.sleep(.5)
else:raise RuntimeError('Control readiness failed')
for item in after['models']:
    assert item['settings']['questions']==questions and item['settings']['rounds']==ROUNDS[item['id']]
    original=next(m for m in before['models'] if m['id']==item['id'])
    assert item['current']['batch']==original['current']['batch']
    assert item['current']['config']==original['current']['config'],'Current task settings changed'
after_pids=pids(after)
assert after_pids==before_pids,'A collector process changed; inspect before continuing'
for job in [m['current'] for m in after['models'] if m['current']['service_state']=='active']:
    with sqlite3.connect(BASE/'panel/control.sqlite') as db:service_name=db.execute('select service from jobs where batch=?',(job['batch'],)).fetchone()[0]
    assert run('systemctl','show',service_name,'--property=RestartPreventExitStatus','--value').strip()=='77'
result={'at':time.time(),'files':manifest['files'],'policy':plan,'current_batches_unchanged':True,'collector_pids_unchanged':True,
        'pids':after_pids,'timer':run('systemctl','list-timers','--all','geo-daily-dispatch.timer','--no-pager')}
POINTER.write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps({k:v for k,v in result.items() if k not in {'files','pids'}},ensure_ascii=False))
