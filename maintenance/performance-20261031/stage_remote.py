import hashlib,json,os,shutil,subprocess,tarfile,time
from pathlib import Path
work=Path('/opt/monitor/maintenance/performance-20261031');stage=work/'stage'
assert not stage.exists(),'Inspect existing stage before overwriting'
stage.mkdir(parents=True)
with tarfile.open('/tmp/performance-20261031-release.tar.gz') as tar:
 for member in tar.getmembers():
  target=(stage/member.name).resolve()
  assert stage.resolve() in target.parents and (member.isfile() or member.isdir()) and not member.issym() and not member.islnk()
 tar.extractall(stage)
manifest=json.loads((stage/'manifest.json').read_text())
for row in manifest['files']:
 live=Path(row['server'])
 if row['before']:assert hashlib.sha256(live.read_bytes()).hexdigest()==row['before'],'Production changed: '+str(live)
 else:assert not live.exists(),'New module already exists: '+str(live)
 assert hashlib.sha256((stage/row['archive']).read_bytes()).hexdigest()==row['sha256']
for path in Path('/opt/monitor/monitor_core').rglob('*'):
 if path.is_file() and '__pycache__' not in path.parts:
  dest=stage/'backend/monitor_core'/path.relative_to('/opt/monitor/monitor_core')
  if not dest.exists():dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,dest)
container_stage='/app/maintenance/performance-20261031/stage'
test=subprocess.run(['docker','exec','-w',container_stage+'/backend','-e','PYTHONPATH='+container_stage+'/backend:/app','monitor-dashboard-api','python','-B',container_stage+'/tests/test_assessment.py'],capture_output=True,text=True,timeout=90)
(work/'backend-tests.txt').write_text(test.stdout+test.stderr);print(test.stdout+test.stderr,flush=True)
assert test.returncode==0,'Backend tests failed'
for path in (stage/'backend').rglob('*.py'):compile(path.read_text('utf8'),str(path),'exec')
x=json.loads(subprocess.check_output(['docker','inspect','monitor-dashboard'],text=True))[0]
assert not x['Mounts'] and x['HostConfig']['NetworkMode']=='host'
(work/'container-before.json').write_text(json.dumps(x));(work/'container-before.json').chmod(0o600)
image='monitor-dashboard:performance-20261031'
(stage/'Dockerfile').write_text('FROM '+x['Image']+'\nCOPY app/ /dashboard/app/\nWORKDIR /dashboard\nRUN npm run build\n')
subprocess.run(['docker','build','-t',image,str(stage)],check=True,timeout=480)
print('STAGED',json.dumps({'image':image,'stage':str(stage),'files':len(manifest['files'])}),flush=True)
