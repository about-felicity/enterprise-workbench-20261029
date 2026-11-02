import json,hashlib,shutil,subprocess,time,urllib.request,statistics
from pathlib import Path
w=Path('/opt/monitor/maintenance/memory-opt-20261102');assert (w/'tests-passed').exists()
m=json.loads((w/'stage/manifest.json').read_text())
for r in m['files']:
 p=Path(r['server']);assert hashlib.sha256(p.read_bytes()).hexdigest()==r['before']
 b=w/'before'/r['archive'];b.parent.mkdir(exist_ok=True);shutil.copy2(p,b)
for r in m['files']:shutil.copy2(w/'stage'/r['archive'],r['server'])
# Restart analysis only at the loop's idle sleep, after its request handling.
r=json.loads(subprocess.check_output(['docker','inspect','monitor-product-worker'],text=True))[0];pid=r['State']['Pid']
idle=False
for i in range(45):
 if 'nanosleep' in Path(f'/proc/{pid}/wchan').read_text():idle=True;break
 time.sleep(1)
if idle:subprocess.run(['docker','restart','monitor-product-worker'],check=True,timeout=60)
else:print('PRODUCT_WORKER_PENDING_SAFE_RESTART',flush=True)
subprocess.run(['docker','restart','monitor-dashboard-api'],check=True,timeout=60)
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
url='http://127.0.0.1:8765/api/performance?month=2026-10&as_of=2026-10-31'
for i in range(20):
 try:
  with op.open(url,timeout=90) as response:json.load(response)
  break
 except OSError:
  if i==19:raise
  time.sleep(1)
from concurrent.futures import ThreadPoolExecutor
def read(_):
 t=time.monotonic()
 with op.open(url,timeout=45) as r:
  b=r.read();assert r.status==200;assert isinstance(json.loads(b),dict)
 return time.monotonic()-t
with ThreadPoolExecutor(max_workers=12) as pool:times=list(pool.map(read,range(24)))
print('LIVE_24_REQUESTS',json.dumps({'errors':0,'median_seconds':statistics.median(times),'max_seconds':max(times),'concurrency':12}),flush=True)
for r in m['files']:assert hashlib.sha256(Path(r['server']).read_bytes()).hexdigest()==r['sha256']
(w/'release.json').write_text(json.dumps(m));print('DEPLOY_VERIFIED',flush=True)
print(subprocess.check_output(['docker','stats','--no-stream','--format','{{.Name}} {{.MemUsage}}','monitor-dashboard-api','monitor-product-worker'],text=True),flush=True)
