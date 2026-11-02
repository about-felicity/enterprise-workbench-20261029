import json,tarfile,shutil,subprocess,hashlib
from pathlib import Path
w=Path('/opt/monitor/maintenance/memory-opt-20261102');stage=w/'stage';stage.mkdir(parents=True,exist_ok=True)
with tarfile.open('/tmp/memory-opt-20261102.tar.gz') as t:t.extractall(stage)
m=json.loads((stage/'manifest.json').read_text())
for r in m['files']:
 assert hashlib.sha256(Path(r['server']).read_bytes()).hexdigest()==r['before']
for p in Path('/opt/monitor/monitor_core').iterdir():
 if p.is_file():
  dest=stage/'monitor_core'/p.name;dest.parent.mkdir(exist_ok=True)
  shutil.copy2(stage/p.name if (stage/p.name).exists() else p,dest)
code=r'''
import importlib.util,json,hashlib,time,gc
from monitor_core import database,product_analysis as new,performance_geo_cache as cache
spec=importlib.util.spec_from_file_location('old_analysis','/app/monitor_core/product_analysis.py');old=importlib.util.module_from_spec(spec)
import sys
sys.modules['old_analysis']=old;spec.loader.exec_module(old)
def fingerprint(k):return hashlib.sha256(json.dumps([sorted(k.exact.items()),k.catalog],sort_keys=True,ensure_ascii=False).encode()).hexdigest()
t=time.monotonic();before=old.build_knowledge(database.verified_product_runs());digest=fingerprint(before);counts=(len(before.exact),len(before.catalog));del before;gc.collect()
after=new.build_knowledge(database.verified_product_runs());assert fingerprint(after)==digest;print('KNOWLEDGE_EXACT_MATCH',counts,round(time.monotonic()-t,2),flush=True)
from monitor_core.analytics import daily_owned_product_recommendations
runs=database.load_owned_product_runs(day_from='2026-10-01',day_to='2026-10-31',compact=True)
expected=daily_owned_product_recommendations(runs,['deepseek','doubao','wenxin','yuanbao'],day_limit=3660);del runs;gc.collect()
actual=cache.load_rows('2026-10-01','2026-10-31');assert actual==expected
from concurrent.futures import ThreadPoolExecutor
t=time.monotonic()
with ThreadPoolExecutor(max_workers=12) as pool:
 results=list(pool.map(lambda _:cache.load_rows('2026-10-01','2026-10-31'),range(24)))
assert all(x==expected for x in results)
print('PERFORMANCE_MATCH_24_READS_12_CONCURRENT',round(time.monotonic()-t,3),flush=True)
'''
p=str(stage).replace('/opt/monitor','/app',1)
subprocess.run(['docker','exec','-w',p,'-e','PYTHONPATH='+p+':/app','monitor-dashboard-api','python','-B','-c',code],check=True,timeout=240)
(w/'tests-passed').write_text('exact knowledge, exact month, 24 concurrent reads')
print('TESTS_PASSED',flush=True)
