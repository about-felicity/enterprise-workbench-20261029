"""Preflight and start the authorized six-channel twelve-hour capture soak."""
import fcntl
import json
import math
from pathlib import Path
import subprocess
import sys
import time
from datetime import datetime,timezone

sys.path.insert(0,'/opt/monitor/geo-capture')
from all_channel_soak import API,BASE,MODELS,NATIVE,BUSY,atomic,lane,operation,command


def main():
    with (BASE/'all-channel-soak-install.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        pointer=BASE/'soak12h_current.json'
        if pointer.exists():
            existing=json.loads(pointer.read_text())
            print(json.dumps({'already_registered':existing}))
            return
        acceptance=BASE/'maintenance/20261015-unified/question-only-acceptance/report.json'
        assert json.loads(acceptance.read_text())['passed'],'Exact-question acceptance required'
        api=API();panel=api.panel()
        original={m:{k:lane(panel,m)[k] for k in ('settings','revision','current')} for m in MODELS}
        questions=original['doubao1']['settings']['questions']
        assert len(questions)==21
        for model in MODELS:
            assert original[model]['settings']['questions']==questions
            assert not original[model]['current']['needs_review'],'Unresolved prior queue: '+model
            assert not original[model]['current']['stop_requested'],'Stopped prior queue: '+model
        root=BASE/'soak'/('question-only-soak12h-'+str(int(time.time())))
        root.mkdir(mode=0o700)
        # Drain only currently busy channels, preserving their old immutable jobs.
        for model in MODELS:
            if original[model]['current']['service_state'] in BUSY:
                operation(root,api,model+'-previous-pause',model,'pause',{})
        until=time.time()+900
        while any(lane(api.panel(),m)['current']['service_state'] in BUSY for m in MODELS):
            if time.time()>until:raise RuntimeError('Previous task did not drain; no forced stop')
            time.sleep(3)
        for model in (*NATIVE,'deepseek'):
            operation(root,api,model+'-preflight-login',model,'login',{})
            until=time.time()+170
            while time.time()<until:
                status=lane(api.panel(),model)['login_status']['status']
                if status!='checking':break
                time.sleep(2)
            expected='ready' if model=='deepseek' else 'locally_logged_in'
            if status!=expected:raise RuntimeError('Login not ready: '+model+':'+status)
        panel=api.panel()
        for model in MODELS:
            value=lane(panel,model)
            assert value['current']['batch']==original[model]['current']['batch']
            assert value['settings']==original[model]['settings'] and value['revision']==original[model]['revision']
            assert not value['current']['needs_review']
        start=time.time();fleet=api.session.get(api.url+'/api/status',timeout=20).json()
        containers=[c['name'] for c in fleet['containers'] if c['name']!='monitor-dashboard']
        unit='geo-question-only-soak12h-'+root.name.rsplit('-',1)[1]
        manifest={'test_id':root.name,'started_at':start,'deadline':start+43200,'duration_seconds':43200,
                  'original':original,'jobs':{},'containers':containers,'capacity_rounds':{m:72 if m in NATIVE else 20 for m in MODELS},
                  'docker_before':command('docker','inspect',*containers,'--format','{{.Name}} {{.State.StartedAt}}'),
                  'scope':'Six exact-question channels, fresh conversation/page for every observation. Native 72-round / web 20-round capacity; original defaults restored. Analysis/database/Android containers monitored; separately authorized creation frontend deployment excluded from container restart verdict. No historical batch rerun.'}
        atomic(root/'manifest.json',manifest)
        python=str(BASE/'venv/bin/python');script=str(BASE/'all_channel_soak.py')
        service=f'''[Unit]
Description=GEO six-channel twelve-hour real capture soak
After=network-online.target geo-monitor-status.service
Wants=geo-monitor-status.service
StartLimitIntervalSec=0
[Service]
Type=simple
ExecStart={python} -u {script} --root {root}
Restart=on-failure
RestartPreventExitStatus=2
RestartSec=20
UMask=0077
[Install]
WantedBy=multi-user.target
'''
        deadline=datetime.fromtimestamp(math.ceil(manifest['deadline']),timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
        pause=f'''[Unit]
Description=Drain only registered batches for {root.name}
After=network-online.target
[Service]
Type=oneshot
ExecStart={python} -u {script} --root {root} --pause-only
Restart=on-failure
RestartSec=20
UMask=0077
'''
        timer=f'''[Unit]
Description=GEO six-channel independent drain deadline
[Timer]
OnCalendar={deadline}
Persistent=true
AccuracySec=1s
Unit={unit}-deadline.service
[Install]
WantedBy=timers.target
'''
        for suffix,content in [('.service',service),('-deadline.service',pause),('-deadline.timer',timer)]:
            (Path('/etc/systemd/system')/(unit+suffix)).write_text(content)
        command('systemctl','daemon-reload')
        value={'test_id':root.name,'root':str(root),'service':unit+'.service',
               'deadline_timer':unit+'-deadline.timer','started_at':start,'deadline':manifest['deadline'],'duration_seconds':43200}
        atomic(pointer,value)
        command('systemctl','enable','--now',unit+'-deadline.timer')
        command('systemctl','enable','--now',unit+'.service')
        print(json.dumps(value))


if __name__=='__main__':main()
