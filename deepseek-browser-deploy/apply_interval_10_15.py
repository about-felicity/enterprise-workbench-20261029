import json,sys,time,shutil,sqlite3,subprocess,uuid,os
from pathlib import Path
os.umask(0o077)
base=Path('/opt/monitor/geo-capture');root=Path('/opt/monitor/geo-deepseek-browser-test');sys.path.insert(0,str(base))
from browser_backend import command,read
before=command('get');job=before.get('job') or {};assert job.get('state') in ('running','paused');run_id=job['id'];cursor=job['cursor'];phase=(job.get('inFlight') or {}).get('phase')
assert phase!='send_intent','Unknown send intent: preserve current browser until reconciled'
backup=root/('interval-10-15-backup-'+str(int(time.time())));backup.mkdir();(backup/'plugin-before.json').write_text(json.dumps(before,ensure_ascii=False))
files=[('/tmp/ds-interval-browser.py',root/'browser_test.py'),('/tmp/ds-interval-background.js',root/'project/extension/background.js'),('/tmp/ds-interval-popup.js',root/'project/extension/popup.js'),('/tmp/ds-interval-popup.html',root/'project/extension/popup.html'),('/tmp/ds-interval-controller.py',base/'control_panel.py')]
for src,dst in files:shutil.copy2(dst,backup/dst.name)
with sqlite3.connect(base/'panel/control.sqlite') as conn,sqlite3.connect(backup/'control.sqlite') as dest:conn.backup(dest)
command('pause',{'batch':before['geoAssignment']['batch']})
for src,dst in files:shutil.copyfile(src,dst)
from control_panel import Controller
from daily_tasks import today
c=Controller(base);settings_results={}
for model in ['deepseek','deepseek2']:
 with c.connect() as db:
  row=db.execute('select value,revision from settings where model=?',(model,)).fetchone();cfg=json.loads(row['value']);cfg['interval']=600;cfg['revision']=row['revision']
 settings_results[model]=c.action(model,'settings',cfg,uuid.uuid4().hex)['revision']
with c.lock,c.connect() as db:
 for model in ['deepseek','deepseek2']:
  for row in db.execute('select day,config from daily_tasks where model=? and day>=?',(model,today())).fetchall():
   cfg=json.loads(row['config']);cfg['interval']=600;db.execute('update daily_tasks set config=? where model=? and day=?',(json.dumps(cfg,ensure_ascii=False),model,row['day']))
 # Only active browser batch metadata; no result or conversation changes.
 row=c.current(db,'deepseek2');cfg=json.loads(row['config']);cfg['interval']=600;db.execute('update jobs set config=? where batch=?',(json.dumps(cfg,ensure_ascii=False),row['batch']))
 batch_root=Path(row['health']).parent
 for name in ['config.json']:
  path=batch_root/name
  if path.exists():
   shutil.copy2(path,backup/('batch-'+name));v=json.loads(path.read_text());v['interval']=600;path.write_text(json.dumps(v,ensure_ascii=False,indent=2))
restart_at=time.time();subprocess.run(['systemctl','restart','geo-deepseek-browser-test.service'],check=True,timeout=45)
for _ in range(25):
 state=read(root/'state.json')
 if state.get('updated_at',0)>restart_at and state.get('auth')=='ready':break
 time.sleep(2)
after=command('get');assert after['job']['id']==run_id and after['job']['cursor']>=cursor
assert after['nextAllowedSendAt']==before['nextAllowedSendAt'],'Existing send permit must be preserved'
assert after['settings']['intervalMinSeconds']==600 and after['settings']['intervalMaxSeconds']==900
assert read(root/'state.json').get('auth')=='ready','Browser needs verification; remain paused'
if job['state']=='running':command('resume',{'batch':before['geoAssignment']['batch']})
for service in ['geo-monitor-status.service','geo-daily-control.service']:
 subprocess.run(['systemctl','restart',service],check=True,timeout=30)
result={'interval_seconds':[600,900],'run_id_preserved':True,'cursor_before':cursor,'cursor_after':after['job']['cursor'],'existing_permit_preserved':True,'auth':'ready','resumed':job['state']=='running','backup':str(backup),'settings_revisions':settings_results,'at':time.time()}
(backup/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False))
