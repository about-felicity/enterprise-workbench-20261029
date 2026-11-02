import json,hashlib,os,subprocess,tarfile,shutil,difflib
from pathlib import Path
base=Path('/opt/monitor/geo-content/maintenance/task-health-20261030');stage=base/'stage';root=Path('/opt/monitor/geo-content/creation')
shutil.copytree(root,stage/'creation',dirs_exist_ok=True)
names=['materials.py','source_cache.py','test_source_cache.py']
with tarfile.open('/tmp/task-health-20261030.tar.gz') as t:
 for n in names:(stage/'creation'/n).write_bytes(t.extractfile(n).read())
assert hashlib.sha256((root/'materials.py').read_bytes()).hexdigest()=='e2fb21b4d2c5d06332b63a8a1307f530fd5ab28a67ae3771db289165b6a643ac'
assert not (root/'source_cache.py').exists()
print('DIFF',''.join(difflib.unified_diff((root/'materials.py').read_text().splitlines(True),(stage/'creation/materials.py').read_text().splitlines(True))),flush=True)
env={**os.environ,'PYTHONPATH':str(stage)+':/opt/monitor/geo-content/engine'}
r=subprocess.run(['/home/user/geo-editorial/venv/bin/python','-B','-m','unittest','creation.test_source_cache','creation.test_studio','creation.test_upload_reliability','creation.test_download_service'],env=env,capture_output=True,text=True,timeout=150)
print(r.stdout+r.stderr,flush=True);assert r.returncode==0

