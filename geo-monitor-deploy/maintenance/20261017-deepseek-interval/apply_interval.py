"""One-time reviewed interval rollout. Never clears queues or replays tasks."""
import json, random, shutil, sqlite3, subprocess, sys, time, uuid
from pathlib import Path

BASE=Path('/opt/monitor/geo-capture')
ROOT=BASE/'maintenance/20261017-deepseek-interval'
sys.path.insert(0,str(BASE))
from control_panel import Controller, atomic, read, BUSY
from daily_tasks import DailyTasks,today

def service(action,name):
    subprocess.run(['systemctl',action,name],check=True,timeout=25)

c=Controller(); day=today(); backup=ROOT/('backup-'+str(int(time.time())))
backup.mkdir()
with c.connect() as db,sqlite3.connect(backup/'control.sqlite') as dest:db.backup(dest)
before={}
with c.connect() as db:
    for model in ('deepseek','deepseek2'):
        job=c.current(db,model);row=DailyTasks(c).row(db,model,day)
        before[model]={'job':job,'daily':row,'marker':read(c.marker(job)),
                       'rate':read(BASE/(model+'_last_send.json'))}
atomic(backup/'before.json',before)
service('stop','geo-daily-control.service')
try:
    # Workers drain themselves at their durable question / receipt boundary.
    for model,old in before.items():
        job=old['job']
        if c.system.state(job['service']) in BUSY and not c.marker(job).exists():
            atomic(c.marker(job),{'requested_at':time.time(),'source':'daily_tasks','action':'apply','day':day})
    deadline=time.time()+40
    while any(c.system.state(x['job']['service']) in BUSY for x in before.values()):
        if time.time()>deadline:raise RuntimeError('Worker still draining; no files or queues changed')
        time.sleep(1)
    mapping={
        'deepseek-deploy/policy.py':['/home/user/redroid-deepseek/code/policy.py','/home/user/redroid-deepseek-account2/code/policy.py'],
        'geo-monitor-deploy/control_panel.py':[str(BASE/'control_panel.py')],
        'geo-monitor-deploy/panel.html':[str(BASE/'panel.html')],
    }
    for source,targets in mapping.items():
        for target in targets:
            p=Path(target);shutil.copy2(p,backup/(str(p).strip('/').replace('/','__')))
            shutil.copy2(ROOT/'candidate'/source,p)
    # Preserve send identity and any longer existing safety deadline.
    for model in before:
        path=BASE/(model+'_last_send.json');rate=read(path)
        if rate:
            last=max(rate.get('time',0),rate.get('last_prompt_epoch',0))
            delay=random.SystemRandom().randint(1200,1800)
            rate.update(next_send_epoch=max(rate.get('next_send_epoch',0),last+delay),
                        interval_seconds=max(rate.get('next_send_epoch',0),last+delay)-last)
            atomic(path,rate)
    # Reload Controller metadata for newly validated user settings.
    import importlib,control_panel
    importlib.reload(control_panel)
    c=control_panel.Controller();tasks=DailyTasks(c);results={}
    for model in before:
        with c.connect() as db:
            settings=db.execute('select * from settings where model=?',(model,)).fetchone()
            config=json.loads(settings['value']);config['interval']=1200
            revision=settings['revision']
        result=c.action(model,'settings',{**config,'revision':revision},uuid.uuid4().hex)
        with c.connect() as db:
            row=tasks.row(db,model,day)
            if row:
                cfg=json.loads(row['config']);cfg['interval']=1200
                result=tasks.request(db,model,day,cfg,result['revision'],row['desired'],apply=row['desired']!='observing')
            results[model]=result
    atomic(ROOT/'applied.json',{'at':time.time(),'day':day,'backup':str(backup),'results':results})
    service('restart','geo-monitor-status.service')
finally:
    service('start','geo-daily-control.service')
print(json.dumps({'applied':True,'backup':str(backup),'models':list(before)},ensure_ascii=False))
