import hashlib,json,shutil,subprocess,tarfile
from pathlib import Path
work=Path('/opt/monitor/maintenance/performance-chart-20261031');stage=work/'stage';stage.mkdir(parents=True,exist_ok=True)
with tarfile.open('/tmp/performance-chart-20261031.tar.gz') as tar:
 assert all(not f.name.startswith('/') and '..' not in Path(f.name).parts for f in tar.getmembers());tar.extractall(stage)
manifest=json.loads((stage/'manifest.json').read_text())
for row in manifest['files']:
 live=Path(row['server'])
 if row['before']:assert hashlib.sha256(live.read_bytes()).hexdigest()==row['before'],'Production source changed '+str(live)
 else:assert not live.exists(),'Unexpected source '+str(live)
 assert hashlib.sha256((stage/row['archive']).read_bytes()).hexdigest()==row['sha256']
 if live.exists():dest=work/'before'/row['archive'];dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(live,dest)
main=json.loads(subprocess.check_output(['docker','inspect','monitor-dashboard'],text=True))[0]
assert main['Config']['Image']=='monitor-dashboard:performance-weights-20261031'
(work/'container-before.json').write_text(json.dumps(main))
(stage/'Dockerfile').write_text('FROM '+main['Image']+'\nCOPY app/ /dashboard/app/\nCOPY render_check.mjs /dashboard/render_check.mjs\nWORKDIR /dashboard\nRUN npm run build\n')
subprocess.run(['docker','build','-t','monitor-dashboard:performance-chart-20261031',str(stage)],check=True,timeout=360)
subprocess.run(['docker','run','--rm','--network','host','--entrypoint','node','monitor-dashboard:performance-chart-20261031','/dashboard/render_check.mjs'],check=True,timeout=90)
print('CHART_STAGE_READY')
