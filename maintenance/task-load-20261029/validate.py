import os,json,shutil,tarfile,subprocess,sys,time,hashlib
from pathlib import Path
base=Path('/opt/monitor/geo-content/maintenance/task-load-20261029');base.mkdir(parents=True,exist_ok=True)
root=Path('/opt/monitor/geo-content/creation');stage=base/'stage';shutil.copytree(root,stage/'creation',dirs_exist_ok=True)
with tarfile.open('/tmp/task-load-20261029.tar.gz') as t:
 expected=json.load(t.extractfile('expected.json'))
 for n in expected:(stage/'creation'/n).write_bytes(t.extractfile(n).read())
for n,h in expected.items():assert hashlib.sha256((root/n).read_bytes()).hexdigest()==h,n
env={**os.environ,'PYTHONPATH':str(stage)+':/opt/monitor/geo-content/engine'}
r=subprocess.run(['/home/user/geo-editorial/venv/bin/python','-B','-m','unittest','creation.test_studio','creation.test_upload_reliability','creation.test_download_service'],env=env,capture_output=True,text=True,timeout=180)
print(r.stdout+r.stderr,flush=True);assert r.returncode==0
sys.path[:0]=[str(stage),'/opt/monitor/geo-content/engine'];from creation import runtime
measure={}
for name,kw in [('full',{}),('tasks',{'task_list':True})]:
 t=time.monotonic();v=runtime.status(**kw)
 measure[name]={'seconds':round(time.monotonic()-t,3),'bytes':len(json.dumps(v,ensure_ascii=False,separators=(',',':')).encode())}
 if name=='full':full=v
 else:light=v
keys=('plan_id','date','status','articles','writing_jobs','writing_complete','supplement','allowed_actions')
rows=lambda v:sorted([{k:t.get(k) for k in keys} for t in v['studio']['daily_tasks']],key=lambda t:(t['plan_id'],t['date']))
assert rows(full)==rows(light),'Task snapshot mismatch'
assert [(p['product_id'],p['product']['name']) for p in full['studio']['products']]==[(p['product_id'],p['product']['name']) for p in light['studio']['products']]
assert not light['jobs'] and not light['legacy_articles']
assert measure['tasks']['seconds']<measure['full']['seconds']
assert measure['tasks']['bytes']<measure['full']['bytes']/2
result={'performance':measure,'task_rows':len(rows(light)),'same_states_and_counts':True}
print(json.dumps(result,ensure_ascii=False),flush=True)
print('COMPONENT_BYTES',json.dumps({k:len(json.dumps(v,ensure_ascii=False).encode()) for k,v in light['studio'].items()}))
(base/'validation.json').write_text(json.dumps(result,indent=2))
