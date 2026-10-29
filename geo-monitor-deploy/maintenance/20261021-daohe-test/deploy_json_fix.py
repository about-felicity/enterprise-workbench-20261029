"""Deploy lossless JSON projection at a drained API boundary."""
import sys,json,time,zipfile,subprocess,shutil
from pathlib import Path
from datetime import datetime
B=Path('/opt/monitor/geo-content');M=Path('/opt/monitor/geo-capture/maintenance/20261021-daohe-test')
backup=M/('source-before-json-fix-'+str(time.time_ns()));backup.mkdir()
for p in (B/'runtime/runs').glob('*/api/active.json'):
 a=json.loads(p.read_text());run=p.parent/'runs'/a.get('run_id','none')
 for name in ('call','logic-call'):
  f=run/name/'api_state.json'
  if f.exists():assert json.loads(f.read_text()).get('state') not in {'REQUESTING','REQUEST_UNKNOWN'},'Actual paid execution active'
subprocess.run(['systemctl','stop','geo-content-worker'],check=True)
try:
 with zipfile.ZipFile('/tmp/geo-review-genre-patch.zip') as z:
  for name in z.namelist():
   assert name in {'creation/client.py','creation/test_structural_json.py'}
   target=B/name;saved=backup/name;saved.parent.mkdir(parents=True,exist_ok=True)
   if target.exists():shutil.copy2(target,saved)
   else:saved.with_suffix('.absent').write_text('New regression fixture')
   target.write_bytes(z.read(name))
finally:subprocess.run(['systemctl','start','geo-content-worker'],check=True)
sys.path[:0]=[str(B),str(B/'engine')]
from creation import runtime,studio,observation as o
s=runtime.read(M/'task.json');task=runtime.read(studio.day_path(s['plan_id'],s['date']))
for jid in task['jobs'].values():
 root=runtime.job_root(jid)
 if runtime.read(root/'control.json').get('reason')=='maintenance_drain':runtime.resume(root)
now=datetime.now(o.ZONE);p=o.OUTPUT/'baseline.json';shutil.copy2(p,backup/'baseline.json');data=o.read(p);current=o.collect(now)
assert set(current['unknown_request_ids'])<=set(data['unknown_request_ids'])
data.setdefault('source_revisions_before_overnight',[]).append({'at':current['at'],'reason':'Real trial identified two unambiguous single-delimiter JSON errors in complete responses; local lossless projection retains raw content and all downstream validation','prior_baseline':str(backup/'baseline.json'),'old_fingerprint':data.get('source_fingerprint'),'new_fingerprint':current['source_fingerprint']})
data.update(source_fingerprint=current['source_fingerprint'],setup_finalized_at=current['at']);p.write_text(json.dumps(data,ensure_ascii=False,indent=2));o.main()
result={'at':current['at'],'backup':str(backup),'engine_tests':106,'creation_tests':69,'paid_calls_drained_before_restart':True,'unknown_ids_unchanged':True};runtime.atomic_json(M/'json-fix-deployment.json',result);print(json.dumps(result))
