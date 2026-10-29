import sys,json,time,subprocess,os
from pathlib import Path
sys.path.insert(0,'/opt/monitor/geo-capture')
from control_panel import Controller,atomic,read
from daily_tasks import today,database_counts
from browser_backend import command
base=Path('/opt/monitor/geo-capture');b=Path('/opt/monitor/geo-deepseek-browser-test');backup=b/('desktop-migration-'+str(int(time.time())));backup.mkdir(mode=0o700)
# Stop new browser submissions; retain complete original job and all receipt files.
x=command('get');j=x.get('job') or {};assert (j.get('inFlight') or {}).get('phase')!='send_intent','unknown send requires readback'
command('pause',{'batch':x['geoAssignment']['batch']});atomic(backup/'plugin-job.json',x)
c=Controller(base)
with c.lock,c.connect() as db:
 rows=[]
 for m in ['deepseek','deepseek2']:
  job=c.current(db,m);rows.append((m,job['service']));db.execute("update daily_tasks set desired='observing',status='observing',updated=? where model=? and day>=?",(time.time(),m,today()))
  if m=='deepseek2':cfg=json.loads(db.execute('select value from settings where model=?',(m,)).fetchone()[0])
p=read(base/'daily_plan.json');atomic(backup/'daily_plan.json',p);p['models']=[m for m in p['models'] if m not in ['deepseek','deepseek2']];p['desktop_collectors']=['deepseek2'];atomic(base/'daily_plan.json',p)
counts=database_counts(today()).get('deepseek2',{});schedule=[]
for round_i in range(1,cfg['rounds']+1):
 for qi,q in enumerate(cfg['questions']):
  if round_i>counts.get(q,0):schedule.append({'globalIndex':len(schedule),'prompt':q,'questionIndex':qi,'questionRound':round_i})
seed={'date':today(),'questions':cfg['questions'],'rounds':cfg['rounds'],'schedule':schedule,'already_processed':sum(counts.values()),'original_batch':x['geoAssignment']['batch']}
atomic(Path('/tmp/deepseek-desktop-task.json'),seed)
conf=read('/opt/monitor/runtime/lan_result_receiver.json');client={'enabled':True,'receiver_url':'http://192.168.31.106:'+str(conf['port']),'token':conf['token']}
atomic(Path('/tmp/deepseek-desktop-private-sync.json'),client)
import pwd
u=pwd.getpwnam('user')
for f in ['/tmp/deepseek-desktop-task.json','/tmp/deepseek-desktop-private-sync.json']:os.chown(f,u.pw_uid,u.pw_gid)
for m,service in rows:
 subprocess.run(['systemctl','stop',service],check=False,timeout=30)
for unit in ['geo-deepseek-browser-test.service','geo-deepseek-browser-test-receiver.service','geo-deepseek-auth-check.timer']:
 subprocess.run(['systemctl','disable','--now',unit],check=False,capture_output=True,timeout=40)
print(json.dumps({'server_automatic_deepseek_stopped':True,'existing_processed':sum(counts.values()),'remaining':len(schedule),'other_daily_models':p['models'],'backup':str(backup)}))
