import os,tarfile,subprocess,shutil
from pathlib import Path
stage=Path('/opt/monitor/geo-content/maintenance/upload-reliability-20261028/stage')
stage.mkdir(parents=True,exist_ok=True)
shutil.copytree('/opt/monitor/geo-content/creation',stage/'creation',dirs_exist_ok=True,ignore=shutil.ignore_patterns('__pycache__'))
with tarfile.open('/tmp/upload-reliability-candidate.tar.gz') as tar:
 for member in tar.getmembers():
  assert member.isfile() and not member.name.startswith('/') and '..' not in Path(member.name).parts
  tar.extract(member,stage,filter='data')
env={**os.environ,'PYTHONPATH':str(stage)+':/opt/monitor/geo-content/engine','PYTHONDONTWRITEBYTECODE':'1'}
cmd=['/home/user/geo-editorial/venv/bin/python','-B','-m','unittest','creation.test_upload_reliability','creation.test_product_images','creation.test_knowledge_library']
r=subprocess.run(cmd,cwd=stage,env=env,capture_output=True,text=True,timeout=150)
(stage.parent/'tests.log').write_text(r.stdout+r.stderr);print(r.stdout);print(r.stderr);raise SystemExit(r.returncode)
