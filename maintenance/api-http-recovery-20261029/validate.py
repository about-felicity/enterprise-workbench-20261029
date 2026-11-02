import os,json,shutil,tarfile,subprocess,hashlib,sqlite3
from pathlib import Path
base=Path('/opt/monitor/geo-content/maintenance/api-http-recovery-20261029');base.mkdir(parents=True,exist_ok=True)
root=Path('/opt/monitor/geo-content/creation');stage=base/'stage';shutil.copytree(root,stage/'creation',dirs_exist_ok=True)
with tarfile.open('/tmp/api-http-recovery-20261029.tar.gz') as t:
 expected=json.load(t.extractfile('expected.json'))
 for n in [*expected,'test_http_recovery.py']:(stage/'creation'/n).write_bytes(t.extractfile(n).read())
for n,h in expected.items():assert hashlib.sha256((root/n).read_bytes()).hexdigest()==h,n
env={**os.environ,'PYTHONPATH':str(stage)+':/opt/monitor/geo-content/engine'}
r=subprocess.run(['/home/user/geo-editorial/venv/bin/python','-B','-m','unittest','creation.test_http_recovery','creation.test_studio','creation.test_upload_reliability','creation.test_download_service'],env=env,capture_output=True,text=True,timeout=150)
print(r.stdout+r.stderr,flush=True);assert r.returncode==0
with sqlite3.connect('file:/home/user/geo-editorial/runtime-api/api/costs.sqlite?mode=ro',uri=True) as db:
 row=db.execute('select coalesce(sum(coalesce(c.charged,c.reserved)),0),count(*) from costs c join studio_cost_scopes s on s.id=c.id where s.scope=? and s.task_day=?',('plan-3224f5a2caac465a988083ae15ab0865','2026-10-29')).fetchone()
 print('TASK_BUDGET',json.dumps({'cap_cny':2,'charged_plus_reserved':row[0],'calls':row[1],'remaining_cny':max(0,2-row[0])}))
(base/'validated.json').write_text(json.dumps({'tests_passed':True,'hashes':{n:hashlib.sha256((stage/'creation'/n).read_bytes()).hexdigest() for n in expected}}))
