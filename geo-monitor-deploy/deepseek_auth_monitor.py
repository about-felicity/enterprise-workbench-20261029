"""Five-minute read-only checks; confirmed account blocks drain new questions."""
import fcntl
import json
from pathlib import Path
import secrets
import subprocess
import time

BASE=Path('/opt/monitor/geo-capture')
CHANNELS={'deepseek':'redroid-deepseek','deepseek2':'redroid-deepseek-account2'}
BAD={'login_required','risk_blocked','verification_required'}

def read(path):
 try:return json.loads(Path(path).read_text())
 except (FileNotFoundError,ValueError):return {}

def record(model,value,base=BASE):
 if model not in CHANNELS:raise ValueError('invalid channel')
 base=Path(base);root=base/'auth-monitor';root.mkdir(parents=True,exist_ok=True)
 with (root/'update.lock').open('a') as handle:
  fcntl.flock(handle,fcntl.LOCK_EX)
  old=read(root/(model+'.json'));now=time.time();value=dict(value)
  status=value.get('status','unknown')
  effective=status if status!='unknown' else old.get('status','unknown')
  changed=effective!=old.get('status')
  current={**old,**value,'model':model,'status':effective,'probe_status':status,'checked_at':now,'next_check_at':now+300}
  if status=='unknown' and old.get('status') in BAD:
   current['probe_message']=value.get('message','');current['message']=old.get('message','账号验证仍未通过')
  if changed:current.update(changed_at=now,incident_id=secrets.token_hex(12) if effective in BAD else '')
  if effective=='ready' and status=='ready':current['last_good_at']=now
  path=root/(model+'.json');tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(current,ensure_ascii=False));tmp.chmod(0o600);tmp.replace(path)
  return current

def check_all():
 from control_panel import Controller,atomic
 c=Controller(BASE);results=[]
 with (BASE/'auth-monitor.run.lock').open('a') as lock:
  fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
  for model,runtime in CHANNELS.items():
   from browser_backend import enabled as browser_enabled,probe as browser_probe
   from manual_login import state
   flow=state(BASE,model)
   if not browser_enabled(model,BASE) and flow.get('status') in {'opening','waiting_login','risk_blocked','verification_required','verifying'}:
    results.append({'model':model,'status':'manual_login_active'});continue
   try:
    if browser_enabled(model,BASE):value=browser_probe()
    else:
     result=subprocess.run(['/home/user/redroid-doubao/worker-venv/bin/python','-B','/home/user/'+runtime+'/code/device.py'],capture_output=True,text=True,timeout=45,check=True)
     value=json.loads(result.stdout.strip().splitlines()[-1])
   except Exception:value={'status':'unknown','message':'本次登录巡检未完成，稍后重试；不把连接异常当作掉登录'}
   current=record(model,value)
   with c.lock,c.connect() as db:
    job=c.current(db,model)
    revision=db.execute('select revision from settings where model=?',(model,)).fetchone()[0]
    if value['status']!='unknown':
     login={**value,'checked_at':current['checked_at'],'batch':job['batch'],'revision':revision}
     db.execute('insert or replace into logins values(?,?)',(model,json.dumps(login,ensure_ascii=False)))
    if value['status'] in BAD and c.system.state(job['service']) in {'active','activating'}:
     if not c.marker(job).exists():atomic(c.marker(job),{'source':'auth_monitor','action':'account_block','requested_at':time.time()})
    results.append({'model':model,'status':current['status'],'checked_at':current['checked_at']})
 print(json.dumps(results,ensure_ascii=False))

if __name__=='__main__':check_all()
