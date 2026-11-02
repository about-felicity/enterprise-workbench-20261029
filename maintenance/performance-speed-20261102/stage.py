import hashlib,json,shutil,subprocess,tarfile
from pathlib import Path
work=Path('/opt/monitor/maintenance/performance-speed-20261102');stage=work/'stage';stage.mkdir(parents=True,exist_ok=True)
with tarfile.open('/tmp/performance-speed-20261102.tar.gz') as t:
 assert all(not x.name.startswith('/') and '..' not in Path(x.name).parts for x in t.getmembers());t.extractall(stage)
manifest=json.loads((stage/'manifest.json').read_text())
for row in manifest['files']:
 live=Path(row['server']);assert (hashlib.sha256(live.read_bytes()).hexdigest() if live.exists() else None)==row['before'],str(live)
 assert hashlib.sha256((stage/row['archive']).read_bytes()).hexdigest()==row['sha256']
for p in Path('/opt/monitor/monitor_core').iterdir():
 if p.is_file() and not (stage/'monitor_core'/p.name).exists():shutil.copy2(p,stage/'monitor_core'/p.name)
code=r'''
import json,time
from monitor_core import database,analytics,performance_geo_cache as cache
from doubao_dashboard_server import ENTERPRISE_MONITOR_QUESTIONS
args=dict(day_from='2026-10-01',day_to='2026-10-31',exclude_questions=ENTERPRISE_MONITOR_QUESTIONS)
t=time.monotonic();full=database.load_owned_product_runs(**args);expected=analytics.daily_owned_product_recommendations(full,['deepseek','doubao','wenxin','yuanbao'],day_limit=3660);print('BASELINE_SECONDS',time.monotonic()-t,flush=True)
compact=database.load_owned_product_runs(**args,compact=True)
for model,runs in compact.items():
 originals={r['run_id']:r for r in full[model]}
 for r in runs:
  old=originals[r['run_id']]
  assert all(old[k]==v for k,v in r.items()),r['run_id']
print('BYTES',len(json.dumps(full,default=str)),len(json.dumps(compact,default=str)),flush=True)
t=time.monotonic();actual=cache.load_rows('2026-10-01','2026-10-31',ENTERPRISE_MONITOR_QUESTIONS);print('COLD_SECONDS',time.monotonic()-t,flush=True)
assert actual==expected,'MATRIX_MISMATCH'
t=time.monotonic();assert cache.load_rows('2026-10-01','2026-10-31',ENTERPRISE_MONITOR_QUESTIONS)==expected;print('WARM_SECONDS',time.monotonic()-t,flush=True)
# Simulate a revised day and verify only that day is loaded.
original_versions=database.owned_product_day_versions;original_load=database.load_owned_product_runs
versions=original_versions('2026-10-01','2026-10-31');versions['2026-10-15']=['test-revision'];calls=[]
database.owned_product_day_versions=lambda *a:versions
def tracked(**kw):
 calls.append(kw);return original_load(**kw)
database.load_owned_product_runs=tracked
assert cache.load_rows('2026-10-01','2026-10-31',ENTERPRISE_MONITOR_QUESTIONS)==expected
assert len(calls)==1 and calls[0]['day_from']==calls[0]['day_to']=='2026-10-15'
print('EXACT_EQUIVALENCE_AND_INVALIDATION_PASS',flush=True)
'''
p=str(stage).replace('/opt/monitor','/app',1)
subprocess.run(['docker','exec','-w',p,'-e','PYTHONPATH='+p+':/app','monitor-dashboard-api','python','-B','-c',code],check=True,timeout=180)
print('STAGE_PASS',flush=True)

