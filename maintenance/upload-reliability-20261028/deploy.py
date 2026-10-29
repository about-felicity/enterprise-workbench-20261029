import os,json,hashlib,shutil,subprocess,time,urllib.request
from pathlib import Path
base=Path('/opt/monitor/geo-content/maintenance/upload-reliability-20261028');stage=base/'stage';root=Path('/opt/monitor/geo-content/creation')
expected=json.loads(Path('/tmp/upload-reliability-baseline.json').read_text('utf-8-sig'))
(base/'baseline.json').write_text(json.dumps(expected,ensure_ascii=False,indent=2))
files=['runtime.py','product_images.py','knowledge_library.py','service.py','panel.html','library.js','uploads.js','test_upload_reliability.py','test_knowledge_library.py','test_product_images.py']
def run(*args):return subprocess.check_output(args,text=True,timeout=120).strip()
def health():
 for _ in range(30):
  try:
   with urllib.request.urlopen('http://127.0.0.1:3000/api/geo-creation/uploads',timeout=3) as r:
    result=json.load(r)
    if r.status==200 and result.get('csrf'):return
  except Exception:time.sleep(1)
 raise RuntimeError('New uploads endpoint not healthy')
assert (base/'tests.log').read_text().rstrip().endswith('OK')
for name in files:
 if name in expected['hashes']:assert hashlib.sha256((root/name).read_bytes()).hexdigest()==expected['hashes'][name],name
 if name.endswith('.py'):compile((stage/'creation'/name).read_text(),name,'exec')
dashboard=Path('/opt/monitor/yuanbao_monitor/dashboard');route=dashboard/'app/api/geo-creation/[...path]/route.ts'
assert hashlib.sha256(route.read_bytes()).hexdigest()==expected['gateway_sha']
old_image=json.loads((base/'dashboard-before.json').read_text())['image']
image_ref=run('docker','inspect','monitor-dashboard','--format','{{.Config.Image}}')
assert image_ref=='monitor-dashboard:responsive-20261026',image_ref
workers=run('systemctl','show','geo-content-worker','geo-creation-studio','-p','Id','-p','MainPID','-p','ActiveEnterTimestampMonotonic')
backup=base/'code-before';backup.mkdir(exist_ok=True)
for name in files:
 if (root/name).exists() and not (backup/name).exists():shutil.copy2(root/name,backup/name)
if not (backup/'route.ts').exists():shutil.copy2(route,backup/'route.ts')
compose=['docker','compose','-p','local-server','-f','/opt/monitor/deploy/local-server/docker-compose.yml','up','-d','--no-deps','--no-build','--force-recreate','dashboard']
try:
 # Only the HTTP API is restarted; paid workers and capture processes stay running.
 run('systemctl','stop','geo-content-api')
 for name in files:
  temp=root/(name+'.installing');shutil.copyfile(stage/'creation'/name,temp);temp.chmod(0o644);os.replace(temp,root/name)
 shutil.copy2(stage/'route.ts',route)
 run('systemctl','start','geo-content-api')
 run('docker','tag','monitor-dashboard:upload-reliability-20261028',image_ref);run(*compose);health()
except Exception:
 for name in files:
  if (backup/name).exists():shutil.copy2(backup/name,root/name)
 shutil.copy2(backup/'route.ts',route);run('systemctl','restart','geo-content-api')
 run('docker','tag',old_image,image_ref);run(*compose);raise
assert workers==run('systemctl','show','geo-content-worker','geo-creation-studio','-p','Id','-p','MainPID','-p','ActiveEnterTimestampMonotonic')
shutil.copy2(stage/'creation-gateway.test.mjs',dashboard/'tests/creation-gateway.test.mjs')
release={'at':time.time(),'workers_unchanged':True,'files':[{'source':'geo-monitor-deploy/creation/'+n,'server':str(root/n),'sha256':hashlib.sha256((root/n).read_bytes()).hexdigest()} for n in files]}
release['files'] += [{'source':'geo-monitor-deploy/dashboard-integration/'+str(p.relative_to(dashboard)),'server':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in [route,dashboard/'tests/creation-gateway.test.mjs']]
(base/'release.json').write_text(json.dumps(release,indent=2));print(json.dumps(release))
