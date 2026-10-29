import json
from pathlib import Path
import shutil
import subprocess
import sys
import time
import urllib.request
import zipfile

ROOT=Path('/opt/monitor/geo-capture/maintenance/20261017-uniform-cards')
SOURCE=Path('/opt/monitor/yuanbao_monitor/dashboard/app')
IMAGE='monitor-dashboard:uniform-cards-20261017'
PREVIEW='monitor-dashboard-uniform-preview'
def run(*args):return subprocess.check_output(args,text=True,timeout=90).strip()
def ready(port):
 for _ in range(40):
  try:
   with urllib.request.urlopen(f'http://127.0.0.1:{port}/',timeout=5) as r:
    if r.status==200:return
  except Exception:pass
  time.sleep(1)
 raise RuntimeError('Frontend readiness timeout')
def snapshot():
 rows=json.loads(run('docker','ps','--no-trunc','--format','{{json .}}').replace('\n',',').join(['[',']']))
 return {r['Names']:run('docker','inspect','--format','{{.State.StartedAt}}',r['Names']) for r in rows if r['Names'] not in {'monitor-dashboard',PREVIEW}}
ROOT.mkdir(parents=True,exist_ok=True)
mode=sys.argv[1]
if mode=='preview':
 assert not (ROOT/'release.json').exists()
 zipfile.ZipFile('/tmp/geo-uniform-cards-source.zip').extractall(ROOT/'stage')
 old=run('docker','inspect','monitor-dashboard','--format','{{.Image}}')
 rollback='monitor-dashboard:before-responsive-'+str(int(time.time()))
 run('docker','tag',old,rollback)
 (ROOT/'backup').mkdir()
 for name in ['Dashboard.tsx','globals.css']:shutil.copy2(SOURCE/name,ROOT/'backup'/name)
 data={'original_image':old,'rollback':rollback,'image':IMAGE,'before_containers':snapshot(),'at':time.time(),'status':'building'}
 (ROOT/'release.json').write_text(json.dumps(data,indent=2))
 (ROOT/'Dockerfile').write_text(f'FROM {rollback}\nCOPY stage/Dashboard.tsx /dashboard/app/Dashboard.tsx\nCOPY stage/globals.css /dashboard/app/globals.css\nWORKDIR /dashboard\nRUN NEXT_TELEMETRY_DISABLED=1 NODE_OPTIONS=--max-old-space-size=1536 npm run build\n')
 with (ROOT/'build.log').open('w') as log:subprocess.run(['docker','build','-t',IMAGE,str(ROOT)],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=600)
 run('docker','run','-d','--name',PREVIEW,'--network','host','--memory=512m',IMAGE,'npm','run','start','--','-H','127.0.0.1','-p','3001')
 ready(3001);data['status']='preview';(ROOT/'release.json').write_text(json.dumps(data,indent=2));print(json.dumps({'status':'preview','image':IMAGE}))
elif mode=='publish':
 data=json.loads((ROOT/'release.json').read_text());assert data['status']=='preview'
 assert json.loads((ROOT/'qa-preview.json').read_text())['passed']
 assert run('docker','inspect','monitor-dashboard','--format','{{.Image}}')==data['original_image']
 compose=['docker','compose','-p','local-server','-f','/opt/monitor/deploy/local-server/docker-compose.yml','up','-d','--no-deps','--no-build','--force-recreate','dashboard']
 run('docker','tag',IMAGE,'monitor-dashboard:local')
 try:run(*compose);ready(3000)
 except Exception:
  run('docker','tag',data['rollback'],'monitor-dashboard:local');run(*compose);raise
 for name in ['Dashboard.tsx','globals.css']:shutil.copy2(ROOT/'stage'/name,SOURCE/name)
 data.update(status='published',published_at=time.time(),after_containers=snapshot())
 assert data['before_containers']==data['after_containers'],'Unrelated container changed; investigate'
 (ROOT/'release.json').write_text(json.dumps(data,indent=2));print(json.dumps({'status':'published','unrelated_containers_unchanged':True}))
