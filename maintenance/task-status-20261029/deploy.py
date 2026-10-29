import json,hashlib,shutil,subprocess,tarfile,os,time,urllib.request
from pathlib import Path
base=Path('/opt/monitor/geo-content/maintenance/task-status-20261029');base.mkdir(parents=True,exist_ok=True);root=Path('/opt/monitor/geo-content/creation');stage=base/'stage';shutil.copytree(root,stage/'creation',dirs_exist_ok=True)
with tarfile.open('/tmp/task-status-20261029.tar.gz') as t:
 expected=json.load(t.extractfile('expected.json'))
 for n in expected:(stage/'creation'/n).write_bytes(t.extractfile(n).read())
env={**os.environ,'PYTHONPATH':str(stage)+':/opt/monitor/geo-content/engine'}
r=subprocess.run(['/home/user/geo-editorial/venv/bin/python','-B','-m','unittest','creation.test_studio','creation.test_upload_reliability','creation.test_knowledge_library'],env=env,capture_output=True,text=True,timeout=120);print(r.stdout+r.stderr,flush=True);assert r.returncode==0
for n,h in expected.items():assert hashlib.sha256((root/n).read_bytes()).hexdigest()==h,n
backup=base/'before';backup.mkdir(exist_ok=False)
for n in expected:shutil.copy2(root/n,backup/n)
workers=subprocess.check_output(['systemctl','show','geo-content-worker','geo-creation-studio','-p','MainPID']).decode()
try:
 subprocess.run(['systemctl','stop','geo-content-api'],check=True)
 for n in expected:
  p=root/n;tmp=p.with_suffix('.status.tmp');shutil.copy2(stage/'creation'/n,tmp);tmp.chmod(0o644);os.replace(tmp,p)
 subprocess.run(['systemctl','start','geo-content-api'],check=True)
 op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
 for _ in range(15):
  try:
   state=json.load(op.open('http://127.0.0.1:3000/api/geo-creation/panel',timeout=12));assert all('supplement' in t for t in state['studio']['daily_tasks']);break
  except Exception:time.sleep(1)
 else:raise RuntimeError('State endpoint did not recover')
except Exception:
 for n in expected:shutil.copy2(backup/n,root/n)
 subprocess.run(['systemctl','restart','geo-content-api']);raise
assert workers==subprocess.check_output(['systemctl','show','geo-content-worker','geo-creation-studio','-p','MainPID']).decode()
release={'files':[{'source':'geo-monitor-deploy/creation/'+n,'server':str(root/n),'sha256':hashlib.sha256((root/n).read_bytes()).hexdigest()} for n in expected],'workers_unchanged':True,'task_rows':len(state['studio']['daily_tasks']),'supplementing':[{k:t.get(k) for k in ['name','date','status','supplement']} for t in state['studio']['daily_tasks'] if t.get('supplement')]}
(base/'release.json').write_text(json.dumps(release,ensure_ascii=False,indent=2));print(json.dumps(release,ensure_ascii=False))
