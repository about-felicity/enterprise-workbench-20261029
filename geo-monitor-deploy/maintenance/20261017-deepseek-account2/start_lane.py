"""Register and start the second lane once; preserve every existing lane and queue."""
from contextlib import closing
from datetime import datetime
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import time
import uuid
from zoneinfo import ZoneInfo

BASE=Path('/opt/monitor/geo-capture')
STAGE=Path('/tmp/deepseek-second-lane-candidate')
PROFILE=Path('/home/user/redroid-deepseek-account2')
def account(container):
 path=Path('/var/lib/docker/volumes')/(container+'-data')/'_data/data/com.deepseek.chat/databases/deepseek_chat.db'
 with closing(sqlite3.connect(path.as_uri()+'?mode=ro',uri=True)) as db:
  rows=db.execute('select id from app_user_info where length(id)>0 and length(token)>0').fetchall()
 assert len(rows)==1
 return rows[0][0]
assert account('deepseek-hpe14-account2')!=account('deepseek-hpe14-android13'), 'Separate rate clocks require different authenticated accounts'
dbpath=BASE/'panel/control.sqlite'
with closing(sqlite3.connect(dbpath)) as db:
 assert not db.execute("select 1 from settings where model='deepseek2'").fetchone(), 'Second lane already registered; inspect and resume, do not create another batch'
 primary=db.execute("select value from settings where model='deepseek'").fetchone()[0]
 day=datetime.now(ZoneInfo('Asia/Shanghai')).date().isoformat()
 saved=db.execute("select config from daily_tasks where model='deepseek' and day=?",(day,)).fetchone()
 settings=json.loads(saved[0] if saved else primary)
 assert len(settings['questions'])==21 and settings['rounds']==3
stamp=datetime.now(ZoneInfo('Asia/Shanghai')).strftime('%Y%m%d-%H%M%S')
batch='geo-panel-deepseek2-'+stamp+'-'+uuid.uuid4().hex[:8]
root=PROFILE/'batches'/batch
backup=BASE/'backups'/('deepseek-second-lane-'+str(int(time.time())))
backup.mkdir(mode=0o700)
files=['control_panel.py','daily_tasks.py','native_entry.py','capture_bridge.py','fleet_status.py','panel.html']
for name in files:
 compile((STAGE/name).read_text(),name,'exec') if name.endswith('.py') else None
 shutil.copy2(BASE/name,backup/name)
for name in ['fleet.json','daily_plan.json']:shutil.copy2(BASE/name,backup/name)
with closing(sqlite3.connect(dbpath)) as source,closing(sqlite3.connect(backup/'control.sqlite')) as target:
 source.backup(target)
subprocess.run(['systemctl','stop','geo-daily-control.service'],check=True)
started=False
try:
 for name in files:shutil.copy2(STAGE/name,BASE/name)
 code=PROFILE/'code';code.mkdir(mode=0o700,exist_ok=True)
 for source in (STAGE/'account2').glob('*.py'):shutil.copy2(source,code/source.name)
 root.mkdir(mode=0o700,parents=True,exist_ok=False)
 sys.path.insert(0,str(BASE))
 from control_panel import Controller,atomic,validate
 validate('deepseek2',settings)
 config={**settings,'model':'deepseek2','batch':batch,'backend':'android','device':'deepseek-hpe14-account2',
         'created_at':time.time(),'prompt_mode':'question_only','daily_revision':1,'daily_date':day,
         'daily_target_rounds':settings['rounds']}
 unit='geo-native@'+batch+'.service'
 health=root/'bridge_health.json'
 atomic(health,{'model':'deepseek2','batch':batch,'planned':len(settings['questions'])*settings['rounds'],
                'status':'not_started','captured':0,'geo_processed':0,'tasks':{'pending':63},'time':time.time()})
 atomic(BASE/'panel/jobs'/(batch+'.json'),config)
 with closing(sqlite3.connect(dbpath)) as db:
  db.execute('pragma synchronous=FULL')
  db.execute('insert into jobs values(?,?,?,?,?,?,0)',(batch,'deepseek2',unit,str(health),json.dumps(config,ensure_ascii=False),time.time()))
  db.execute('insert into settings values(?,?,1,?)',('deepseek2',json.dumps(settings,ensure_ascii=False),batch))
  db.execute('insert into daily_tasks values(?,?,?,?,?,?,?,?,?)',('deepseek2',day,json.dumps(settings,ensure_ascii=False),1,'running','queued',batch,time.time(),None))
  db.execute('insert into events(model,event,batch,created,message) values(?,?,?,?,?)',('deepseek2','authorized_second_lane',batch,time.time(),'第二个独立账号按另一账号当天保存配置开始采集'))
  db.commit()
 fleet=json.loads((BASE/'fleet.json').read_text())
 assert len(fleet['collectors'])==6
 fleet['collectors'].append({'name':'DeepSeek 2','service':unit,'health':str(health),'planned':63})
 if 'deepseek-hpe14-account2' not in fleet['containers']:fleet['containers'].append('deepseek-hpe14-account2')
 atomic(BASE/'fleet.json',fleet)
 plan=json.loads((BASE/'daily_plan.json').read_text())
 if 'deepseek2' not in plan['models']:plan['models'].append('deepseek2')
 plan['rounds']['deepseek2']=settings['rounds']
 atomic(BASE/'daily_plan.json',plan)
 control=Controller()
 with control.connect() as db:job=control.current(db,'deepseek2')
 control._login('deepseek2',job,False,1)
 with control.connect() as db:
  control._ensure_login(db,'deepseek2')
 control.system.enable_current(unit,None)
 control.system.start(unit);started=True
 metadata=json.loads((PROFILE/'device.json').read_text())
 metadata.update(scheduled=True,batch=batch,model='deepseek2')
 atomic(PROFILE/'device.json',metadata)
finally:
 subprocess.run(['systemctl','start','geo-daily-control.service'],check=True)
subprocess.run(['systemctl','restart','geo-monitor-status.service'],check=True)
print(json.dumps({'started':started,'batch':batch,'unit':unit,'health':str(health),'config':settings,
                  'backup':str(backup),'existing_collectors_restarted':False},ensure_ascii=False))
