import hashlib,json,os,shutil,subprocess,tarfile,time,urllib.request
from pathlib import Path
base=Path('/opt/monitor/geo-content/maintenance/task-load-20261029')
root=Path('/opt/monitor/geo-content/creation');stage=base/'stage/creation'
validated=json.loads((base/'validation.json').read_text());assert validated['same_states_and_counts']
assert validated['performance']['tasks']['bytes']<150000
with tarfile.open('/tmp/task-load-20261029.tar.gz') as t:
 expected=json.load(t.extractfile('expected.json'))
 for n in expected:
  assert (stage/n).read_bytes()==t.extractfile(n).read(),n
  assert hashlib.sha256((root/n).read_bytes()).hexdigest()==expected[n],n
backup=base/'before';backup.mkdir(exist_ok=False)
for n in expected:shutil.copy2(root/n,backup/n)
workers=subprocess.check_output(['systemctl','show','geo-content-worker','geo-creation-studio','-p','MainPID'])
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
try:
 subprocess.run(['systemctl','stop','geo-content-api'],check=True)
 for n in expected:
  dest=root/n;temp=dest.with_suffix('.task-load.tmp');shutil.copy2(stage/n,temp);temp.chmod(0o644);os.replace(temp,dest)
 subprocess.run(['systemctl','start','geo-content-api'],check=True)
 for attempt in range(15):
  try:
   started=time.monotonic()
   with op.open('http://127.0.0.1:3000/api/geo-creation/status',timeout=15) as r:body=r.read()
   state=json.loads(body);assert state['csrf'] and state['studio']['plans'] and not state['jobs']
   elapsed=time.monotonic()-started;break
  except Exception:
   if attempt==14:raise
   time.sleep(1)
 with op.open('http://127.0.0.1:3000/api/geo-creation/ui',timeout=15) as r:html=r.read().decode()
 assert "request(taskOnly?'status':'panel')" in html and 'ensureEditorData' in html
 assert workers==subprocess.check_output(['systemctl','show','geo-content-worker','geo-creation-studio','-p','MainPID'])
except Exception:
 for n in expected:shutil.copy2(backup/n,root/n)
 subprocess.run(['systemctl','restart','geo-content-api'],check=True)
 raise
result={'files':[{'source':'geo-monitor-deploy/creation/'+n,'server':str(root/n),'sha256':hashlib.sha256((root/n).read_bytes()).hexdigest()} for n in expected],
 'workers_unchanged':True,'gateway_seconds':round(elapsed,3),'response_bytes':len(body),'task_rows':len(state['studio']['daily_tasks']),'performance':validated['performance']}
(base/'release.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False))
