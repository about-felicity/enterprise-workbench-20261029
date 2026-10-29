"""Deploy tested source while preserving all tasks, budgets and unknown calls."""
import hashlib,json,shutil,subprocess,time
from pathlib import Path
D=Path('/opt/monitor/geo-capture/maintenance/20261022-article-quality');S=D/'stage';B=Path('/opt/monitor/geo-content')
assert all(r['exit_code']==0 for r in json.loads((D/'test-results.json').read_text())['results'])
manifest=json.loads(Path('/tmp/article-deployment-manifest.json').read_text())
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
roots=B/'runtime/runs'
for p in roots.glob('*/api/active.json'):
 control=p.parents[1]/'control.json';paused=json.loads(control.read_text()).get('paused') if control.exists() else False
 if not paused:assert json.loads(p.read_text()).get('state') in (None,'SUBMITTED'),'Wait for active paid request: '+str(p)
 active=json.loads(p.read_text())
 if active.get('state') in {'REQUESTING','RESPONDED'}:
  for call in (p.parent/'runs'/active['run_id']).rglob('api_state.json'):
   value=json.loads(call.read_text())
   assert not (value.get('state')=='REQUESTING' and not (call.parent/'response.json').exists()
               and time.time()-value.get('started_epoch',time.time())<360),'Wait for in-flight call: '+str(call)
backup=D/('source-before-'+str(time.time_ns()));backup.mkdir()
targets={name:(D/'regression'/name if name.startswith('tests/') else B/name) for name in manifest['files']}
for name,target in targets.items():
 expected=manifest['before'].get(name)
 if expected is not None:assert target.is_file() and digest(target)==expected,('production source changed',name)
 elif not name.startswith('tests/'):assert not target.exists(),('unexpected new target',name)
 assert digest(S/name)==manifest['files'][name],name
 if target.exists():
  saved=backup/name;saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,saved)
subprocess.run(['systemctl','stop','geo-content-worker'],check=True,timeout=45)
try:
 for name,target in targets.items():
  target.parent.mkdir(parents=True,exist_ok=True);temp=target.with_name(target.name+'.unattended22.tmp')
  shutil.copy2(S/name,temp);temp.chmod(0o644);temp.replace(target)
finally:subprocess.run(['systemctl','start','geo-content-worker'],check=True)
subprocess.run(['systemctl','restart','geo-content-api','geo-creation-studio'],check=True,timeout=30)
out={'at':time.time(),'backup':str(backup),'source_files':{str(target):digest(target) for target in targets.values()},
     'engine_tests':196,'creation_tests':78,'budget_changed':False,'task_control_changed':False}
(D/'deployment.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps({'at':out['at'],'backup':out['backup'],'files':len(targets),'budget_changed':False}))
drain=D/'deployment-drain.json'
if drain.exists():
 record=json.loads(drain.read_text())
 if not record.get('restored'):
  for row in record['paused']:
   p=roots/row['job']/'control.json';current=json.loads(p.read_text())
   if current.get('reason')=='source_deploy22' and current.get('revision')==row['pause_revision']:
    temp=p.with_name(p.name+'.drain-restore.tmp');temp.write_text(json.dumps(row['before'],ensure_ascii=False,indent=2));temp.replace(p)
  record.update(restored=True,restored_at=time.time());drain.write_text(json.dumps(record,ensure_ascii=False,indent=2))
