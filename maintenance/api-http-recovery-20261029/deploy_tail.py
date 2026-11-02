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
