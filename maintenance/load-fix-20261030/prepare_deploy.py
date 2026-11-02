"""Build a guarded deployment script; this command does not contact the server."""
import json
from pathlib import Path
root=Path(__file__).resolve().parents[2]
dest=Path(__file__).resolve().parent
service=(root/'geo-monitor-deploy/creation/service.py').read_text('utf8')
previous=service.replace('from .status_cache import StatusCache\n','').replace('task_status_cache=StatusCache()\n','').replace("task_status_cache.get(lambda:runtime.status(task_list=True))","runtime.status(task_list=True)")
previous=previous.replace("            try:\n                result=runtime.action(action,payload,self.headers.get('X-Action-Id',''))\n            finally:\n                # Even a failed action may have saved part of its durable state.\n                task_status_cache.invalidate()", "            result=runtime.action(action,payload,self.headers.get('X-Action-Id',''))")
files={name:(root/'geo-monitor-deploy/creation'/name).read_text('utf8') for name in ['service.py','status_cache.py','test_status_cache.py']}
script='EXPECTED='+repr(previous)+'\nFILES='+repr(files)+'\n'+r'''
import hashlib,json,os,shutil,subprocess,time,urllib.request
from pathlib import Path
base=Path('/opt/monitor/geo-content')
live=base/'creation'
assert (live/'service.py').read_text('utf8')==EXPECTED, 'Production service differs: stop and review before deployment'
work=Path('/opt/monitor/geo-content/maintenance')/('load-fix-'+str(time.time_ns()))
work.mkdir(parents=True)
stage=work/'stage'
shutil.copytree(live,stage/'creation',ignore=shutil.ignore_patterns('__pycache__'))
for name,body in FILES.items():(stage/'creation'/name).write_text(body,encoding='utf8')
env=dict(os.environ,PYTHONPATH=str(stage)+':'+str(base/'engine'))
result=subprocess.run(['/home/user/geo-editorial/venv/bin/python','-B','-m','unittest','creation.test_status_cache','creation.test_studio','creation.test_upload_reliability','creation.test_download_service'],cwd=stage,env=env,capture_output=True,text=True,timeout=120)
(work/'tests.txt').write_text(result.stdout+result.stderr)
print(result.stdout+result.stderr,flush=True)
assert result.returncode==0, 'Regression failed: live files untouched'
backup=work/'before';backup.mkdir()
existed={name:(live/name).exists() for name in FILES if not name.startswith('test_')}
for name,exists in existed.items():
 if exists:shutil.copy2(live/name,backup/name)
try:
 for name in existed:
  temp=live/(name+'.load-fix.tmp');temp.write_text(FILES[name],encoding='utf8');os.replace(temp,live/name)
 subprocess.run(['systemctl','restart','geo-content-api.service'],check=True,timeout=30)
 opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
 for attempt in range(10):
  try:
   with opener.open('http://127.0.0.1:8804/api/status',timeout=15) as response:status=json.load(response)
   assert status['ok'] and 'studio' in status
   break
  except Exception:
   if attempt==9:raise
   time.sleep(1)
except Exception:
 for name,exists in existed.items():
  if exists:shutil.copy2(backup/name,live/name)
  else:(live/name).unlink(missing_ok=True)
 subprocess.run(['systemctl','restart','geo-content-api.service'],check=True,timeout=30)
 raise
report={'backup':str(backup),'files':[{'source':'geo-monitor-deploy/creation/'+name,'server':str(live/name),'sha256':hashlib.sha256((live/name).read_bytes()).hexdigest()} for name in existed],'plans':len(status['studio']['plans'])}
(work/'release.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False),flush=True)
'''
(dest/'deploy.py').write_text(script,encoding='utf8')
print('Prepared guarded deployment script; not executed')
