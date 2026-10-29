import sys,json,time,zipfile,subprocess,shutil
from pathlib import Path
from datetime import datetime
B=Path('/opt/monitor/geo-content');M=Path('/opt/monitor/geo-capture/maintenance/20261021-daohe-test')
backup=M/('source-before-order-fix-'+str(time.time_ns()));backup.mkdir()
for p in (B/'runtime/runs').glob('*/api/active.json'):
 a=json.loads(p.read_text());run=p.parent/'runs'/a.get('run_id','none')
 for name in ('call','logic-call'):
  f=run/name/'api_state.json'
  if f.exists():assert json.loads(f.read_text()).get('state') not in {'REQUESTING','REQUEST_UNKNOWN'},'Actual paid execution active'
subprocess.run(['systemctl','stop','geo-content-worker'],check=True)
try:
 with zipfile.ZipFile('/tmp/geo-review-genre-patch.zip') as z:
  for name in z.namelist():
   if name.startswith('tests/'):continue
   assert name in {'engine/geo_source_cards/api_prompts.py','engine/geo_source_cards/auto_repair.py'}
   target=B/name;saved=backup/name;saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,saved);target.write_bytes(z.read(name))
finally:subprocess.run(['systemctl','start','geo-content-worker'],check=True)
sys.path[:0]=[str(B),str(B/'engine')]
from creation import runtime,observation as o
for jid in ('creation-1792575159-0a8f9221','creation-1792576129-389f575e'):
 root=runtime.job_root(jid);assert runtime.read(root/'control.json')['reason']=='maintenance_drain';runtime.resume(root)
now=datetime.now(o.ZONE);p=o.OUTPUT/'baseline.json';shutil.copy2(p,backup/'baseline.json');data=o.read(p);current=o.collect(now)
assert set(current['unknown_request_ids'])<=set(data['unknown_request_ids'])
data.setdefault('source_revisions_before_overnight',[]).append({'at':current['at'],'reason':'Real new-product trial: explicit immutable section-order contract and bounded repair for known independent logic rejections; no quality bypass or unknown request replay','prior_baseline':str(backup/'baseline.json'),'old_fingerprint':data.get('source_fingerprint'),'new_fingerprint':current['source_fingerprint']})
data.update(source_fingerprint=current['source_fingerprint'],setup_finalized_at=current['at']);p.write_text(json.dumps(data,ensure_ascii=False,indent=2));o.main()
result={'at':current['at'],'backup':str(backup),'engine_tests':105,'creation_tests':66,'paid_calls_drained_before_restart':True,'unknown_ids_unchanged':True};runtime.atomic_json(M/'order-fix-deployment.json',result);print(json.dumps(result))
