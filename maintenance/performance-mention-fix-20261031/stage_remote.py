import hashlib,json,shutil,subprocess,tarfile
from pathlib import Path
work=Path('/opt/monitor/maintenance/performance-mention-fix-20261031');stage=work/'stage';stage.mkdir(parents=True,exist_ok=True)
with tarfile.open('/tmp/performance-mention-fix-20261031.tar.gz') as tar:
 assert all(not x.name.startswith('/') and '..' not in Path(x.name).parts for x in tar.getmembers());tar.extractall(stage)
manifest=json.loads((stage/'manifest.json').read_text())
for row in manifest['files']:
 live=Path(row['server']);source=stage/row['archive']
 assert hashlib.sha256(source.read_bytes()).hexdigest()==row['sha256']
 if row['before']:assert hashlib.sha256(live.read_bytes()).hexdigest()==row['before'],'Source changed: '+str(live)
 else:assert not live.exists(),'Unexpected new source exists: '+str(live)
 if live.exists():dest=work/'before'/row['archive'];dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(live,dest)
for source in Path('/opt/monitor/monitor_core').glob('*.py'):
 dest=stage/'backend/monitor_core'/source.name
 if not dest.exists():shutil.copy2(source,dest)
shutil.copy2('/opt/monitor/monitor_core/performance_data_202610.json',stage/'backend/monitor_core/performance_data_202610.json')
container_stage=str(stage).replace('/opt/monitor','/app',1)
cmd=['docker','exec','-w',container_stage+'/backend','-e','PYTHONPATH='+container_stage+'/backend','-e','MONITOR_PERFORMANCE_DB='+str(work/'test.sqlite').replace('/opt/monitor','/app',1),'monitor-dashboard-api','python','-B','-m','unittest','discover','-s',container_stage+'/tests','-p','test_*.py']
subprocess.run(cmd,check=True,timeout=45)
main=json.loads(subprocess.check_output(['docker','inspect','monitor-dashboard'],text=True))[0]
assert main['Config']['Image']=='monitor-dashboard:performance-entry-20261031'
(work/'container-before.json').write_text(json.dumps(main))
(stage/'Dockerfile').write_text('FROM '+main['Image']+'\nCOPY app/ /dashboard/app/\nWORKDIR /dashboard\nRUN npm run build\n')
subprocess.run(['docker','build','-t','monitor-dashboard:performance-mention-fix-20261031',str(stage)],check=True,timeout=360)
print('STAGE_READY',flush=True)
