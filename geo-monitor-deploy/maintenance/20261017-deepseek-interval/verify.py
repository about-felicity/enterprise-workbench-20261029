import json,sys,hashlib
from pathlib import Path
sys.path.insert(0,'/opt/monitor/geo-capture')
from control_panel import Controller,read
from daily_tasks import today
c=Controller();base=c.base
out={'day':today(),'models':[]}
for m in c.all()['models']:
    d=m['daily'];current=m['current']
    x={k:m[k] for k in ('id','revision')}
    x.update(interval=d['config']['interval'],default_interval=m['settings']['interval'],
             rounds=d['config']['rounds'],questions=len(d['config']['questions']),
             completed=d['completed'],remaining=d['remaining'],desired=d['desired'],
             daily_status=d['status'],current=current,
             auth=m.get('login_monitor',{}).get('status'))
    if m['id'] in ('deepseek','deepseek2'):
        x['rate']=read(base/(m['id']+'_last_send.json'))
        with c.connect() as db:
            job=c.current(db,m['id']);x['health']=read(job['health'])
    else:x.pop('current')
    out['models'].append(x)
path=base/'maintenance/20261017-deepseek-interval/verification.json'
path.write_text(json.dumps(out,ensure_ascii=False,indent=2))
for m in out['models']:
    if m['id'] in ('deepseek','deepseek2'):
        print(json.dumps(m,ensure_ascii=False))
    else:print(json.dumps(m,ensure_ascii=False))
