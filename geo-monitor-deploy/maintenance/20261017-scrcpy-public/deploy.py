import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import urllib.request

ROOT=Path('/opt/monitor/geo-capture/maintenance/20261017-scrcpy-public')
STAGE=ROOT/'workspace';BASE=Path('/opt/monitor/geo-capture')
IMAGE='monitor-dashboard:scrcpy-public-20261017';PREVIEW='monitor-dashboard-scrcpy-preview'
def run(*args):return subprocess.check_output(args,text=True,timeout=100).strip()
def units():
 names=run('systemctl','list-units','--all','--plain','--no-legend','geo-native*','geo-web*').splitlines()
 return {l.split()[0]:run('systemctl','show',l.split()[0],'-p','MainPID','--value') for l in names if l and l.split()[0].startswith(('geo-native@','geo-web@'))}
def ready(port):
 for _ in range(30):
  try:
   with urllib.request.urlopen(f'http://127.0.0.1:{port}/',timeout=5) as r:
    if r.status==200:return
  except Exception:pass
  time.sleep(1)
 raise RuntimeError('Frontend readiness timeout')

mode=sys.argv[1]
if mode=='backend':
 assert not (ROOT/'release.json').exists()
 mapping={}
 for n in ['scrcpy_stream.py','deepseek_android_login.py','deepseek_auth_monitor.py','manual_login.py','fleet_status.py','control_panel.py','daily_tasks.py','panel.html','deepseek_login.html']:
  mapping['geo-monitor-deploy/'+n]=BASE/n
 mapping['deepseek-deploy/device.py']=Path('/home/user/redroid-deepseek/code/device.py')
 mapping['deepseek-deploy/account2/device.py']=Path('/home/user/redroid-deepseek-account2/code/device.py')
 # One shared policy is explicitly deployed to both independent runtimes.
 data={'at':time.time(),'status':'preparing','collectors_before':units(),'backup':str(ROOT/'backup')}
 (ROOT/'release.json').write_text(json.dumps(data,indent=2))
 baseline=json.loads((ROOT.parent/'20261015-unified/current-manifest.json').read_text())['files']
 hashes={i['server']:i['sha256'] for i in baseline}
 for target in mapping.values():
  if str(target) in hashes:assert hashlib.sha256(target.read_bytes()).hexdigest()==hashes[str(target)],'Source changed before deployment: '+str(target)
 def copy(src,target):
  target=Path(target);target.parent.mkdir(parents=True,exist_ok=True)
  if target.exists():
   stat=target.stat();backup=ROOT/'backup'/str(target).lstrip('/');backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,backup)
  else:stat=None
  shutil.copy2(STAGE/src,target)
  if stat:os.chown(target,stat.st_uid,stat.st_gid);target.chmod(stat.st_mode&0o777)
  else:target.chmod(0o644)
 for src,target in mapping.items():copy(src,target)
 for runtime in ['redroid-deepseek','redroid-deepseek-account2']:copy('deepseek-deploy/auth_policy.py',Path('/home/user')/runtime/'code/auth_policy.py')
 for unit in ['geo-deepseek-auth-check.service','geo-deepseek-auth-check.timer']:copy('geo-monitor-deploy/systemd/'+unit,Path('/etc/systemd/system')/unit)
 run('systemctl','daemon-reload')
 # Initialize authoritative status before new actor code reads the gate.
 run('/opt/monitor/geo-capture/venv/bin/python','-B',str(BASE/'deepseek_auth_monitor.py'))
 run('systemctl','restart','geo-monitor-status.service','geo-daily-control.service')
 run('systemctl','enable','--now','geo-deepseek-auth-check.timer')
 after=units();assert data['collectors_before']==after,'Collector lifecycle changed; investigate'
 data.update(status='backend_published',collectors_after=after);(ROOT/'release.json').write_text(json.dumps(data,indent=2))
 print(json.dumps({'status':data['status'],'collector_pids_unchanged':True}))
elif mode=='preview':
 data=json.loads((ROOT/'release.json').read_text());assert data['status']=='backend_published'
 old=run('docker','inspect','monitor-dashboard','--format','{{.Image}}');rollback='monitor-dashboard:before-scrcpy-'+str(int(time.time()))
 run('docker','tag',old,rollback);data.update(original_image=old,rollback=rollback);(ROOT/'release.json').write_text(json.dumps(data,indent=2))
 (ROOT/'Dockerfile').write_text(f'FROM {rollback}\nCOPY workspace/geo-monitor-deploy/dashboard-integration/app/api/geo-capture/ /dashboard/app/api/geo-capture/\nCOPY workspace/geo-monitor-deploy/dashboard-integration/tests/capture-gateway.test.mjs /dashboard/tests/capture-gateway.test.mjs\nWORKDIR /dashboard\nRUN node --experimental-strip-types --test tests/capture-gateway.test.mjs tests/creation-gateway.test.mjs\nRUN NEXT_TELEMETRY_DISABLED=1 NODE_OPTIONS=--max-old-space-size=1536 npm run build\n')
 with (ROOT/'build.log').open('w') as log:subprocess.run(['docker','build','-t',IMAGE,str(ROOT)],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=600)
 run('docker','run','-d','--name',PREVIEW,'--network','host','--memory=512m',IMAGE,'npm','run','start','--','-H','127.0.0.1','-p','3001');ready(3001)
 data['status']='preview';(ROOT/'release.json').write_text(json.dumps(data,indent=2));print(json.dumps({'status':'preview'}))
elif mode=='publish':
 data=json.loads((ROOT/'release.json').read_text());assert data['status']=='preview'
 assert json.loads((ROOT/'qa-fixture.json').read_text())['passed']
 assert json.loads((ROOT/'qa-preview.json').read_text())['passed']
 assert run('docker','inspect','monitor-dashboard','--format','{{.Image}}')==data['original_image']
 command=['docker','compose','-p','local-server','-f','/opt/monitor/deploy/local-server/docker-compose.yml','up','-d','--no-deps','--no-build','--force-recreate','dashboard']
 run('docker','tag',IMAGE,'monitor-dashboard:local')
 try:run(*command);ready(3000)
 except Exception:run('docker','tag',data['rollback'],'monitor-dashboard:local');run(*command);raise
 src=STAGE/'geo-monitor-deploy/dashboard-integration/app/api/geo-capture/[...path]/route.ts'
 dest=Path('/opt/monitor/yuanbao_monitor/dashboard/app/api/geo-capture/[...path]/route.ts');shutil.copy2(src,dest)
 shutil.copy2(STAGE/'geo-monitor-deploy/dashboard-integration/tests/capture-gateway.test.mjs','/opt/monitor/yuanbao_monitor/dashboard/tests/capture-gateway.test.mjs')
 shutil.copy2(STAGE/'geo-monitor-deploy/dashboard-integration/app/CaptureControl.tsx','/opt/monitor/yuanbao_monitor/dashboard/app/CaptureControl.tsx')
 data.update(status='published',published_at=time.time());(ROOT/'release.json').write_text(json.dumps(data,indent=2));print(json.dumps({'status':'published'}))
