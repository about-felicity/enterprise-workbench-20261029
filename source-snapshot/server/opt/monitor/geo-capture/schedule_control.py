"""Validated global daily schedule, independent of active collector jobs."""
from datetime import datetime,timedelta
import hashlib,json,re
from zoneinfo import ZoneInfo
from control_panel import atomic,read,Conflict
ZONE=ZoneInfo('Asia/Shanghai')

def validate(value):
    if type(value.get('enabled')) is not bool:raise ValueError('请选择是否启用每日定时')
    if not isinstance(value.get('time'),str) or not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',value['time']):raise ValueError('每天开始时间须为有效的 HH:MM')
    if type(value.get('revision')) is not int:raise ValueError('请刷新后保存定时设置')
    return {k:value[k] for k in ('enabled','time','revision')}

def view(base,now=None):
    p=read(base/'daily_plan.json');now=now or datetime.now(ZONE)
    result={k:p[k] for k in ('enabled','time','timezone','start_date','card_order') if k in p}
    result.update(revision=p.get('schedule_revision',0),next_run=None)
    if p.get('enabled'):
        day=max(now.astimezone(ZONE).date(),datetime.strptime(p['start_date'],'%Y-%m-%d').date())
        candidate=datetime.combine(day,datetime.strptime(p.get('time','05:00'),'%H:%M').time(),ZONE)
        if candidate<=now:candidate+=timedelta(days=1)
        result['next_run']=candidate.isoformat()
    return result

def save(control,value,key):
    value=validate(value)
    if not re.fullmatch(r'[a-f0-9]{32}',key or ''):raise ValueError('操作标识无效，请刷新后重试')
    digest=hashlib.sha256(json.dumps(value,sort_keys=True).encode()).hexdigest()
    with control.lock,control.connect() as db:
        found=db.execute('select input_hash,result from commands where id=?',(key,)).fetchone()
        if found:
            if found['input_hash']!=digest:raise Conflict('操作标识已用于不同设置')
            return json.loads(found['result'])
        old=read(control.base/'daily_plan.json')
        replay=old.get('schedule_action')==key and old.get('schedule_hash')==digest
        if not replay and value['revision']!=old.get('schedule_revision',0):raise Conflict('定时设置已变化，请刷新后重试')
        new=old if replay else {**old,'enabled':value['enabled'],'time':value['time'],'timezone':'Asia/Shanghai',
            'schedule_revision':value['revision']+1,'schedule_action':key,'schedule_hash':digest}
        atomic(control.base/'daily_plan.json',new)
        try:control.system.configure_daily_schedule(new['time'],new['enabled'])
        except Exception:
            atomic(control.base/'daily_plan.json',old)
            try:control.system.configure_daily_schedule(old.get('time','05:00'),old.get('enabled',True))
            except Exception:pass
            raise RuntimeError('定时器更新未完成，原计划已保留，请重试')
        result={'ok':True,'message':'每日定时已保存，下次定时起生效；当前采集继续运行','schedule':view(control.base)}
        control._record(db,key,'schedule','schedule',digest,result,None)
        return result
