import hashlib,json,shutil,subprocess,time,urllib.request
from pathlib import Path
work=Path('/opt/monitor/maintenance/performance-speed-20261102');stage=work/'stage';manifest=json.loads((stage/'manifest.json').read_text())
for row in manifest['files']:
 live=Path(row['server']);assert (hashlib.sha256(live.read_bytes()).hexdigest() if live.exists() else None)==row['before'],str(live)
 if live.exists():
  backup=work/'before'/row['archive'];backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(live,backup)
try:
 for row in manifest['files']:shutil.copy2(stage/row['archive'],row['server'])
 subprocess.run(['docker','restart','monitor-dashboard-api'],check=True,timeout=60)
 op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
 for i in range(30):
  try:
   with op.open('http://127.0.0.1:8765/api/performance?month=2026-11',timeout=60) as r:assert r.status==200
   break
  except OSError:
   if i==29:raise
   time.sleep(1)
 # Warm the new per-day cache directly in the live server through a unique HTTP cache key.
 for month,day in [('2026-10','2026-10-31'),('2026-11','2026-11-02')]:
  t=time.monotonic()
  with op.open('http://127.0.0.1:8765/api/performance?month='+month+'&as_of='+day,timeout=90) as r:
   body=json.load(r);assert isinstance(body,dict)
  print('LIVE',month,round(time.monotonic()-t,3),flush=True)
 for row in manifest['files']:assert hashlib.sha256(Path(row['server']).read_bytes()).hexdigest()==row['sha256']
 (work/'release.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
 print('DEPLOY_VERIFIED',flush=True)
except Exception:
 for row in manifest['files']:
  if row['before']:shutil.copy2(work/'before'/row['archive'],row['server'])
 subprocess.run(['docker','restart','monitor-dashboard-api'],check=True,timeout=60)
 raise
