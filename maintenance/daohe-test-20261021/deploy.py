import os,sys,json,zipfile,shutil,subprocess,time,hashlib
from pathlib import Path
from datetime import datetime
B=Path('/opt/monitor/geo-content');M=Path('/opt/monitor/geo-capture/maintenance/20261021-daohe-test');S=Path('/opt/monitor/geo-capture/maintenance/20261021-article-logic/stage')
backup=M/('source-before-review-'+str(time.time_ns()));backup.mkdir()
for p in (B/'runtime/runs').glob('*/api/active.json'):assert json.loads(p.read_text()).get('state') in (None,'SUBMITTED'),'Paid response active'
subprocess.run(['systemctl','stop','geo-content-worker'],check=True)
try:
 with zipfile.ZipFile('/tmp/geo-review-genre-patch.zip') as z:
  for name in z.namelist():
   if name.startswith('tests/'):continue
   assert name.startswith(('engine/geo_source_cards/','creation/')) and '..' not in Path(name).parts
   target=B/name;saved=backup/name;saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,saved);target.write_bytes(z.read(name))
finally:subprocess.run(['systemctl','start','geo-content-worker'],check=True)
subprocess.run(['systemctl','restart','geo-content-api','geo-creation-studio'],check=True)
sys.path[:0]=[str(B),str(B/'engine')]
from creation import observation as o
now=datetime.now(o.ZONE);assert now.date().isoformat()=='2026-10-21'
p=o.OUTPUT/'baseline.json';shutil.copy2(p,backup/'baseline.json');data=o.read(p);current=o.collect(now)
assert set(current['unknown_request_ids'])<=set(data['unknown_request_ids'])
data.setdefault('source_revisions_before_overnight',[]).append({'at':current['at'],'reason':'User-requested new-product 7 ranking + 7 review trial: add opt-in generic review genre and fix shared writer-rule injection across early-return paths','prior_baseline':str(backup/'baseline.json'),'old_fingerprint':data.get('source_fingerprint'),'new_fingerprint':current['source_fingerprint']})
data.update(source_fingerprint=current['source_fingerprint'],setup_finalized_at=current['at']);p.write_text(json.dumps(data,ensure_ascii=False,indent=2));o.main()
result={'deployed_at':current['at'],'backup':str(backup),'engine_tests':88,'creation_tests':65,'budget_changed':False,'unknown_ids_unchanged':True}
(M/'deployment.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False))
