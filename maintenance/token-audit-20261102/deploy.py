from pathlib import Path
import hashlib,json,tarfile,shutil,subprocess,time,importlib.util,datetime,zoneinfo
w=Path('/opt/monitor/maintenance/token-audit-20261102');stage=w/'stage';stage.mkdir(parents=True,exist_ok=True)
with tarfile.open('/tmp/token-audit-20261102.tar.gz') as tar:
 assert all(not p.name.startswith('/') and '..' not in Path(p.name).parts for p in tar.getmembers());tar.extractall(stage)
m=json.loads((stage/'manifest.json').read_text())
for r in m['files']:
 p=Path(r['server']);assert (hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None)==r['before'],str(p)
 if p.suffix=='.py':compile((stage/r['archive']).read_text(),str(p),'exec')
spec=importlib.util.spec_from_file_location('window',stage/'pricing_window.py');mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
z=zoneinfo.ZoneInfo('Asia/Shanghai')
for value,expected in [('2026-11-02T08:59:59',None),('2026-11-02T09:00:00',12),('2026-11-02T11:59:59',12),('2026-11-02T12:00:00',None),('2026-11-02T14:00:00',18),('2026-11-02T18:00:00',None),('2026-11-01T10:00:00',None)]:
 t=datetime.datetime.fromisoformat(value).replace(tzinfo=z).timestamp();r=mod.resume_at(t);assert (datetime.datetime.fromtimestamp(r,z).hour if r else None)==expected
print('7_BOUNDARY_TESTS_PASS',flush=True)
base=Path('/opt/monitor/geo-content/runtime');drain=base/'worker_drain.json';previous=drain.read_bytes() if drain.exists() else None
assert not previous or not json.loads(previous).get('enabled'),'Existing drain; do not override'
drain.write_text(json.dumps({'enabled':True,'reason':'install approved offpeak scheduling'}))
try:
 for i in range(300):
  health=json.loads((base/'worker_health.json').read_text())
  if health.get('status')=='draining' and not health.get('active_jobs'):break
  if i%30==0:print('WAITING_FOR_INFLIGHT',len(health.get('active_jobs',[])),flush=True)
  time.sleep(1)
 else:raise RuntimeError('Drain timeout; source unchanged')
 for r in m['files']:
  p=Path(r['server']);assert (hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None)==r['before']
  if p.exists():backup=w/'before'/r['archive'];backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,backup)
 for r in m['files']:shutil.copy2(stage/r['archive'],r['server'])
 subprocess.run(['systemctl','restart','geo-content-worker.service','geo-content-api.service','geo-creation-studio.service'],check=True,timeout=90)
 for r in m['files']:assert hashlib.sha256(Path(r['server']).read_bytes()).hexdigest()==r['sha256']
 (w/'release.json').write_text(json.dumps(m));print('DEPLOYED',flush=True)
finally:
 if previous is None:drain.unlink(missing_ok=True)
 else:drain.write_bytes(previous)
# Aggregate only token counters, never API headers or prompt bodies.
from collections import defaultdict
counts=defaultdict(lambda:dict(calls=0,input=0,output=0))
p=Path('/opt/monitor/runtime/remote_product_ai_worker.log')
if p.exists():
 for line in p.open():
  if line[:10] not in ['2026-11-01','2026-11-02'] or '{' not in line:continue
  try:r=json.loads(line[line.index('{'):])
  except ValueError:continue
  if 'input_tokens' in r:
   g=counts[line[:10]];g['calls']+=1;g['input']+=r.get('input_tokens',0);g['output']+=r.get('output_tokens',0)
print('GEO_LOG_USAGE',json.dumps(counts),flush=True)
