import hashlib,json,os,shutil,subprocess,time,urllib.request
from pathlib import Path
base=Path('/opt/monitor/geo-content')
work=base/'maintenance'/('task-health-20261031-'+str(time.time_ns()))
for relative,row in FILES.items():
 assert hashlib.sha256((base/relative).read_bytes()).hexdigest()==row['before'],relative+' changed on server'
work.mkdir(parents=True)
stage=work/'stage'
shutil.copytree(base/'creation',stage/'creation',ignore=shutil.ignore_patterns('__pycache__'))
shutil.copytree(base/'engine/geo_source_cards',stage/'engine/geo_source_cards',ignore=shutil.ignore_patterns('__pycache__'))
for relative,row in FILES.items():(stage/relative).write_text(row['text'],encoding='utf8')
for name,value in TESTS.items():(stage/'creation'/name).write_text(value,encoding='utf8')
env=dict(os.environ,PYTHONPATH=str(stage)+':'+str(stage/'engine'))
command=['/home/user/geo-editorial/venv/bin/python','-B','-m','unittest','creation.test_topic_aliases','creation.test_shared_source_cache','creation.test_source_cache','creation.test_jsonl_records','creation.test_response_framing','creation.test_client','creation.test_studio','creation.test_upload_reliability','creation.test_download_service']
result=subprocess.run(command,cwd=stage,env=env,text=True,capture_output=True,timeout=120)
(work/'tests.txt').write_text(result.stdout+result.stderr)
print(result.stdout+result.stderr,flush=True)
assert result.returncode==0,'Tests failed: no production changes'
for relative,row in FILES.items():
 assert hashlib.sha256((base/relative).read_bytes()).hexdigest()==row['before']
 backup=work/'before'/relative;backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(base/relative,backup)
try:
 for relative in FILES:
  dest=base/relative;temp=dest.with_suffix('.task-health.tmp');shutil.copy2(stage/relative,temp);temp.chmod(0o644);os.replace(temp,dest)
 for unit in RESTART_UNITS:
  subprocess.run(['systemctl','restart',unit],check=True,timeout=30)
 opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
 for attempt in range(10):
  try:
   with opener.open('http://127.0.0.1:8804/api/status',timeout=25) as r:value=json.load(r)
   assert value['ok'];break
  except Exception:
   if attempt==9:raise
   time.sleep(1)
except Exception:
 for relative in FILES:shutil.copy2(work/'before'/relative,base/relative)
 for unit in RESTART_UNITS:subprocess.run(['systemctl','restart',unit],check=True,timeout=30)
 raise
release={'backup':str(work/'before'),'files':[{'source':row['source'],'server':str(base/relative),'sha256':hashlib.sha256((base/relative).read_bytes()).hexdigest()} for relative,row in FILES.items()]}
(work/'release.json').write_text(json.dumps(release,ensure_ascii=False,indent=2))
print('RELEASE',json.dumps(release,ensure_ascii=False),flush=True)
