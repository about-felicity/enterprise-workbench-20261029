import os,json,shutil,tarfile,subprocess,hashlib,sqlite3
from pathlib import Path
base=Path('/opt/monitor/geo-content/maintenance/api-http-recovery-20261029');base.mkdir(parents=True,exist_ok=True)
root=Path('/opt/monitor/geo-content/creation');stage=base/'stage';shutil.copytree(root,stage/'creation',dirs_exist_ok=True)
with tarfile.open('/tmp/api-http-recovery-20261029.tar.gz') as t:
 expected=json.load(t.extractfile('expected.json'))
 for n in [*expected,'test_http_recovery.py']:(stage/'creation'/n).write_bytes(t.extractfile(n).read())
for n,h in expected.items():assert hashlib.sha256((root/n).read_bytes()).hexdigest()==h,n
env={**os.environ,'PYTHONPATH':str(stage)+':/opt/monitor/geo-content/engine'}
r=subprocess.run(['/home/user/geo-editorial/venv/bin/python','-B','-m','unittest','creation.test_http_recovery','creation.test_studio','creation.test_upload_reliability','creation.test_download_service'],env=env,capture_output=True,text=True,timeout=150)
print(r.stdout+r.stderr,flush=True);assert r.returncode==0
with sqlite3.connect('file:/home/user/geo-editorial/runtime-api/api/costs.sqlite?mode=ro',uri=True) as db:
 row=db.execute('select coalesce(sum(coalesce(c.charged,c.reserved)),0),count(*) from costs c join studio_cost_scopes s on s.id=c.id where s.scope=? and s.task_day=?',('plan-3224f5a2caac465a988083ae15ab0865','2026-10-29')).fetchone()
 print('TASK_BUDGET',json.dumps({'cap_cny':2,'charged_plus_reserved':row[0],'calls':row[1],'remaining_cny':max(0,2-row[0])}))
(base/'validated.json').write_text(json.dumps({'tests_passed':True,'hashes':{n:hashlib.sha256((stage/'creation'/n).read_bytes()).hexdigest() for n in expected}}))

# Executed after the isolated validation in validate.py.
import sys,time,urllib.request
backup=base/'before';backup.mkdir(exist_ok=False)
for n in expected:shutil.copy2(root/n,backup/n)
workers=subprocess.check_output(['systemctl','show','geo-content-worker','geo-creation-studio','-p','MainPID'])
try:
 subprocess.run(['systemctl','stop','geo-content-api'],check=True)
 for n in expected:
  dest=root/n;temp=dest.with_suffix('.http-recovery.tmp');shutil.copy2(stage/'creation'/n,temp);temp.chmod(0o644);os.replace(temp,dest)
 subprocess.run(['systemctl','start','geo-content-api'],check=True)
 op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
 for attempt in range(15):
  try:
   with op.open('http://127.0.0.1:3000/api/geo-creation/status',timeout=15) as res:panel=json.load(res)
   task=next(t for t in panel['studio']['daily_tasks'] if t['plan_id']=='plan-3224f5a2caac465a988083ae15ab0865' and t['date']=='2026-10-29')
   assert task['api_recovery']['count']==4 and task['api_recovery']['retry_available'];break
  except Exception:
   if attempt==14:raise
   time.sleep(1)
 assert workers==subprocess.check_output(['systemctl','show','geo-content-worker','geo-creation-studio','-p','MainPID'])
except Exception:
 for n in expected:shutil.copy2(backup/n,root/n)
 subprocess.run(['systemctl','restart','geo-content-api'],check=True);raise
release={'files':[{'source':'geo-monitor-deploy/creation/'+n,'server':str(root/n),'sha256':hashlib.sha256((root/n).read_bytes()).hexdigest()} for n in expected],'workers_unchanged':True}
(base/'release.json').write_text(json.dumps(release,indent=2));print('DEPLOYED',json.dumps(release),flush=True)
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime,recovery
targets=['creation-1793252901-ec370f70','creation-1793252898-0afc24a2','creation-1793252896-76293dac','creation-1793252890-7d974528']
all_jobs=[p.parent for p in (runtime.BASE/'runs').glob('*/job.json') if (j:=runtime.read(p)).get('studio_plan_id')=='plan-3224f5a2caac465a988083ae15ab0865' and j.get('date')=='2026-10-29']
receipts={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for job in all_jobs for p in (job/'approved').glob('*/*/*/receipt.json')}
(base/'approved-before.json').write_text(json.dumps(receipts,indent=2));assert len(receipts)==16
assert runtime.balance()['is_available'],'API balance unavailable; recovery not started'
results=[]
for identity in targets:
 job=runtime.job_root(identity);definition=runtime.read(job/'job.json')
 assert definition['studio_plan_id']=='plan-3224f5a2caac465a988083ae15ab0865' and definition['date']=='2026-10-29'
 assert definition['budget_limits']['task_budget_cny']==2
 failure=recovery.http_failure(job);assert failure and failure['retry_available']
 result=runtime.resume(job,check_balance=False,allow_http_recovery=True)
 results.append({'job':identity,**result,'original_reservations':failure['calls']})
 (base/'recovered.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
 print('RECOVERED',json.dumps(results[-1],ensure_ascii=False),flush=True)
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in receipts.items())
print('ORIGINAL_16_ARTICLES_PRESERVED',flush=True)
