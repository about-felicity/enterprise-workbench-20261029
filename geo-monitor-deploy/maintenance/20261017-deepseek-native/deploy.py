"""Scoped DeepSeek App migration; archive legacy web history without replaying it."""
from contextlib import closing
from datetime import datetime
import json,os,shutil,sqlite3,subprocess,time,zipfile
from pathlib import Path
from zoneinfo import ZoneInfo

BASE=Path('/opt/monitor/geo-capture');NATIVE=Path('/home/user/redroid-deepseek')
def atomic(path,value):
 path.parent.mkdir(parents=True,exist_ok=True);tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(value,ensure_ascii=False));tmp.chmod(0o600);tmp.replace(path)
def main():
 backup=BASE/'backups'/('deepseek-android-'+str(int(time.time())));backup.mkdir(parents=True,mode=0o700)
 files={
  **{'geo-monitor-deploy/'+name:BASE/name for name in ['control_panel.py','native_entry.py','daily_tasks.py','daily_dispatch.py','capture_bridge.py','manual_login.py','deepseek_android_login.py','deepseek_login.html','panel.html']},
  'geo-monitor-deploy/creation/materials.py':Path('/opt/monitor/geo-content/creation/materials.py')}
 for source,dest in files.items():
  if dest.exists():target=backup/source;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(dest,target)
 with closing(sqlite3.connect(BASE/'panel/control.sqlite')) as db,closing(sqlite3.connect(backup/'control.sqlite')) as target:db.backup(target)
 shutil.copy2(BASE/'fleet.json',backup/'fleet.json')
 # Never stop a collector to deploy its control layer. Main native services are untouched.
 subprocess.run(['systemctl','stop','geo-daily-control.service'],check=True)
 try:
  for source,dest in files.items():shutil.copy2(Path('/tmp/deepseek-native-stage')/source,dest)
  with closing(sqlite3.connect(BASE/'panel/control.sqlite')) as db:
   db.row_factory=sqlite3.Row
   settings=db.execute("select * from settings where model='deepseek'").fetchone()
   old=db.execute('select * from jobs where batch=?',(settings['current_batch'],)).fetchone()
   if not old['service'].startswith('geo-native@'):
    active=subprocess.run(['systemctl','is-active',old['service']],capture_output=True,text=True).stdout.strip()
    if active in {'active','activating','deactivating'}:raise RuntimeError('Legacy DeepSeek collector still busy; migration requires safe idle')
    day=datetime.now(ZoneInfo('Asia/Shanghai')).date().isoformat();daily=db.execute("select * from daily_tasks where day=? and model='deepseek'",(day,)).fetchone()
    config=json.loads(daily['config'] if daily else settings['value'])
    if config['interval']<600:raise ValueError('DeepSeek interval below user ten-minute contract')
    batch='geo-panel-deepseek-app-'+datetime.now(ZoneInfo('Asia/Shanghai')).strftime('%Y%m%d-%H%M%S')
    config.update(model='deepseek',batch=batch,prompt_mode='question_only',backend='android',device='deepseek-hpe14-android13',created_at=time.time())
    if daily:config.update(daily_revision=daily['revision'],daily_date=day,daily_target_rounds=config['rounds'])
    root=NATIVE/'batches'/batch;root.mkdir(parents=True,mode=0o700)
    health=root/'bridge_health.json';atomic(health,{'batch':batch,'model':'deepseek','status':'waiting_login','planned':len(config['questions'])*config['rounds'],'captured':0,'geo_processed':0,'tasks':{'pending':len(config['questions'])*config['rounds']},'time':time.time(),'backend':'android'})
    atomic(BASE/'panel/jobs'/(batch+'.json'),config)
    service='geo-native@'+batch+'.service'
    with db:
     db.execute('insert into jobs values(?,?,?,?,?,?,0)',(batch,'deepseek',service,str(health),json.dumps(config,ensure_ascii=False),time.time()))
     db.execute('update settings set current_batch=? where model=?',(batch,'deepseek'))
     db.execute('update jobs set stop_requested=1 where batch=?',(old['batch'],))
     db.execute("delete from logins where model='deepseek'")
     db.execute("insert into events(model,event,batch,created,message) values('deepseek','android_migration',?,?,?)",(batch,time.time(),'切换官方安卓App；原网页历史及未完成记录保留，没有重发'))
     if daily:db.execute("update daily_tasks set batch=?,status=case when desired='paused' then 'paused' else 'waiting_login' end,error=null,updated=? where day=? and model='deepseek'",(batch,time.time(),day))
    atomic(Path(old['health']).parent/'pause.json',{'requested_at':time.time(),'source':'android_migration','action':'superseded_by_android','new_batch':batch})
    fleet=json.loads((BASE/'fleet.json').read_text());lane=next(v for v in fleet['collectors'] if v['name']=='DeepSeek');lane.update(service=service,health=str(health),planned=len(config['questions'])*config['rounds'])
    if 'deepseek-hpe14-android13' not in fleet['containers']:fleet['containers'].append('deepseek-hpe14-android13')
    atomic(BASE/'fleet.json',fleet)
    wants=Path('/etc/systemd/system/geo-monitor.target.wants');(wants/old['service']).unlink(missing_ok=True)
    if not (wants/service).exists():(wants/service).symlink_to('/etc/systemd/system/geo-native@.service')
   atomic(BASE/'deepseek_backend.json',{'backend':'android','package':'com.deepseek.chat','container':'deepseek-hpe14-android13','serial':'127.0.0.1:5560','version_code':281,'migrated_at':time.time()})
  subprocess.run(['systemctl','daemon-reload'],check=True)
  subprocess.run(['systemctl','restart','geo-monitor-status.service'],check=True)
  # Material daemon may only be restarted when no subprocess is collecting.
  material=json.loads(Path('/opt/monitor/geo-content/materials/health.json').read_text())
  if not material.get('active_channels'):subprocess.run(['systemctl','restart','geo-creation-materials.service'],check=True)
  else:print('Material daemon code staged; active private question preserved until safe restart')
 finally:subprocess.run(['systemctl','start','geo-daily-control.service'],check=True)
 print(json.dumps({'backup':str(backup),'backend':'android','login_required':True}))

if __name__=='__main__':main()
