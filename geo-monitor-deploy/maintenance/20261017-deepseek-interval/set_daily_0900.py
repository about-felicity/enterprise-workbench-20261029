"""One-time user schedule update through the panel's durable save API."""
import hashlib,json,shutil,sys,time,uuid
from pathlib import Path
sys.path.insert(0,'/opt/monitor/geo-capture')
from control_panel import Controller,read,atomic
from schedule_control import save,view
c=Controller();base=c.base
root=base/'maintenance'/('20261017-daily-0900-'+str(int(time.time())))
root.mkdir()
shutil.copy2(base/'daily_plan.json',root/'daily_plan.before.json')
timer=Path('/etc/systemd/system/geo-daily-dispatch.timer.d/30-schedule.conf')
shutil.copy2(timer,root/'timer.before.conf')
creator=Path('/opt/monitor/geo-content/materials/settings.json')
before=creator.read_bytes()
assert json.loads(before)['time']=='01:00'
with c.connect() as db:
    configs=[tuple(r) for r in db.execute('select model,value,revision,current_batch from settings order by model')]
p=read(base/'daily_plan.json')
result=save(c,{'enabled':True,'time':'09:00','revision':p.get('schedule_revision',0)},uuid.uuid4().hex)
assert view(base)['time']=='09:00'
assert creator.read_bytes()==before
assert '09:00:00 Asia/Shanghai' in timer.read_text()
with c.connect() as db:
    assert configs==[tuple(r) for r in db.execute('select model,value,revision,current_batch from settings order by model')]
atomic(root/'verified.json',{'at':time.time(),'result':result,'creation_time':'01:00',
    'creation_config_unchanged':True,'model_settings_and_current_batches_unchanged':True})
print(json.dumps({'backup':str(root),'schedule':result['schedule'],'creation_time':'01:00'},ensure_ascii=False))
