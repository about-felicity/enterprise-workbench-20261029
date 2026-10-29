"""Idempotent daily GEO dispatch. Timer time is Asia/Shanghai, no chat agent needed."""
from contextlib import closing
from datetime import datetime
import fcntl
import hashlib
import json
from pathlib import Path
import sqlite3
import time
from zoneinfo import ZoneInfo

from control_panel import Controller, Conflict, BUSY, atomic, read

BASE=Path('/opt/monitor/geo-capture')


def operation_id(day,model):
    return hashlib.sha256(('geo-daily:'+day+':'+model).encode()).hexdigest()[:32]


def due(plan,now):
    local=now.astimezone(ZoneInfo('Asia/Shanghai'))
    hour,minute=map(int,plan.get('time','05:00').split(':'))
    return bool(plan.get('enabled') and local.date().isoformat()>=plan['start_date'] and (local.hour,local.minute)>=(hour,minute))


class DailyController(Controller):
    """Allow a NEW day after sealing an inactive prior-day queue, never reset it."""
    rollover_batch=None

    def _ensure_known(self,job,*,allow_readback=False):
        if job['batch']!=self.rollover_batch:return super()._ensure_known(job,allow_readback=allow_readback)
        if self.system.state(job['service']) in BUSY:raise Conflict('Previous collector is still active')
        old_day=datetime.fromtimestamp(job['created'],ZoneInfo('Asia/Shanghai')).date().isoformat()
        today=datetime.now(ZoneInfo('Asia/Shanghai')).date().isoformat()
        if old_day>=today:return super()._ensure_known(job,allow_readback=allow_readback)
        root=self.base/'daily'/today/'prior-day-archives'/job['batch']
        root.mkdir(parents=True,exist_ok=True)
        task_db=self.batch_root(job)/('tasks.sqlite' if job['service'].startswith('geo-native@') else 'collector/tasks.sqlite')
        backup=root/'tasks.sqlite'
        if task_db.exists() and not backup.exists():
            with closing(sqlite3.connect(task_db.as_uri()+'?mode=ro',uri=True)) as source,closing(sqlite3.connect(backup)) as target:
                source.backup(target)
        if not (root/'sealed.json').exists():
            atomic(root/'sealed.json',{'at':time.time(),'reason':'user_authorized_new_daily_batch',
                                     'job':job,'health':read(job['health']),'original_tasks_reset':False})


def dispatch_one(control,base,day,model):
    path=base/'daily'/day/(model+'.json')
    previous=read(path)
    item=next(m for m in control.all()['models'] if m['id']==model)
    current=item['current']
    if model=='wenxin_card' and not previous.get('batch'):
        dependency=read(base/'daily'/day/'baidu_ai.json')
        baidu=next(m for m in control.all()['models'] if m['id']=='baidu_ai')['current']
        planned=int(baidu.get('planned') or 0)
        if not (dependency.get('batch')==baidu['batch'] and dependency.get('batch')
                and baidu['state']=='complete' and planned>0
                and int(baidu.get('captured') or 0)>=planned
                and int(baidu.get('processed') or 0)>=planned
                and not baidu.get('pending_delivery') and not baidu.get('needs_review')):
            return {'day':day,'model':model,'state':'waiting_for_baidu','last_attempt':time.time()}
    if previous.get('batch'):
        if current['batch']!=previous['batch']:
            return {**previous,'state':'superseded_by_operator'}
        if current['service_state'] in BUSY:return {**previous,'state':'running','processed':current['processed']}
        if current['state'] in {'complete','complete_with_unavailable'}:return {**previous,'state':'complete','processed':current['processed']}
        if current['stop_requested'] or current['state'] in {'paused','stopped'}:
            return {**previous,'state':'operator_paused_or_stopped'}
        if current['state'] in {'waiting_login','waiting_verification'}:
            login=item['login_status']
            if login.get('checked_at',0)<=previous.get('last_attempt',0) or login.get('status') not in {'ready','locally_logged_in'}:
                return {**previous,'state':current['state']}
        # Starting the SAME registered service is idempotent; the durable
        # worker resumes its original queue and never creates another batch.
        with control.connect() as db:service=control.current(db,model)['service']
        control.system.start(service)
        return {**previous,'state':'recovering_same_batch','last_attempt':time.time()}
    if current['service_state'] in BUSY:
        return {'day':day,'model':model,'state':'previous_batch_running','last_attempt':time.time()}
    if previous.get('state')=='waiting_login':
        login=item['login_status']
        if login.get('checked_at',0)<=previous.get('last_attempt',0) or login.get('status')!='ready':return previous
    if model=='deepseek':
        with control.connect() as db:job=control.current(db,model)
        control._login(model,job,False,item['revision'])
        item=next(m for m in control.all()['models'] if m['id']==model)
        if item['login_status'].get('status')!='ready':
            return {'day':day,'model':model,'state':'waiting_login' if item['login_status'].get('status')=='login_required' else 'retry_pending','last_attempt':time.time()}
    key=operation_id(day,model)
    payload=previous.get('payload') or {'revision':item['revision']}
    with control.connect() as db:
        command=db.execute('select id from commands where id=?',(key,)).fetchone()
    if not command:payload={'revision':item['revision']}
    intent={'day':day,'model':model,'id':key,'payload':payload,'state':'creating','last_attempt':time.time()}
    atomic(path,intent)
    control.rollover_batch=current['batch']
    try:result=control.action(model,'new',payload,key)
    finally:control.rollover_batch=None
    return {**intent,'batch':result['batch'],'state':'running' if result['ok'] else 'start_unconfirmed','result':result}


def main(base=BASE,*,now=None,control=None):
    plan=read(base/'daily_plan.json')
    now=now or datetime.now(ZoneInfo('Asia/Shanghai'))
    if not due(plan,now):return {'state':'not_due'}
    day=now.astimezone(ZoneInfo('Asia/Shanghai')).date().isoformat()
    if plan.get('daily_control_enabled'):
        from daily_tasks import DailyTasks
        control=control or DailyController(base)
        tasks=DailyTasks(control)
        with control.lock,control.connect() as db:
            for model in plan['models']:tasks.ensure_scheduled(db,model,day)
        return {'day':day,'state':'daily_tasks_registered'}
    root=base/'daily'/day;root.mkdir(parents=True,exist_ok=True)
    control=control or DailyController(base)
    results=[]
    with (base/'daily/dispatch.lock').open('a') as lock:
        try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:return {'state':'already_dispatching'}
        models=list(plan['models'])
        if 'baidu_ai' in models and 'wenxin_card' in models:
            models.remove('wenxin_card');models.insert(models.index('baidu_ai')+1,'wenxin_card')
        for model in models:
            path=root/(model+'.json')
            try:result=dispatch_one(control,base,day,model)
            except Exception as error:
                result={**read(path),'day':day,'model':model,'state':'retry_pending','error_code':type(error).__name__,'last_attempt':time.time()}
            atomic(path,result);results.append(result)
        atomic(root/'status.json',{'at':time.time(),'day':day,'models':results})
    print(json.dumps({'day':day,'models':[{k:r[k] for k in ('model','state') if k in r} for r in results]}))
    return {'day':day,'models':results}


if __name__=='__main__':main()
