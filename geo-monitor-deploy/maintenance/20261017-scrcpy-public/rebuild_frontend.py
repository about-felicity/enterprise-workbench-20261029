import json
from pathlib import Path
import shutil
import subprocess
import time
ROOT=Path('/opt/monitor/geo-capture/maintenance/20261017-scrcpy-public')
data=json.loads((ROOT/'release.json').read_text())
assert data['status']=='published'
old=subprocess.check_output(['docker','inspect','monitor-dashboard','--format','{{.Image}}'],text=True).strip()
rollback='monitor-dashboard:before-scrcpy-navigation-'+str(int(time.time()))
subprocess.run(['docker','tag',old,rollback],check=True)
shutil.copy2('/opt/monitor/yuanbao_monitor/dashboard/app/CaptureControl.tsx',ROOT/'backup/CaptureControl.tsx')
dockerfile=(ROOT/'Dockerfile').read_text().replace('WORKDIR /dashboard','COPY workspace/geo-monitor-deploy/dashboard-integration/app/CaptureControl.tsx /dashboard/app/CaptureControl.tsx\nWORKDIR /dashboard')
(ROOT/'Dockerfile').write_text(dockerfile)
with (ROOT/'build-navigation.log').open('w') as log:subprocess.run(['docker','build','-t','monitor-dashboard:scrcpy-public-20261017',str(ROOT)],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=600)
subprocess.run(['docker','rm','-f','monitor-dashboard-scrcpy-preview'],check=True,capture_output=True)
subprocess.run(['docker','run','-d','--name','monitor-dashboard-scrcpy-preview','--network','host','--memory=512m','monitor-dashboard:scrcpy-public-20261017','npm','run','start','--','-H','127.0.0.1','-p','3001'],check=True,capture_output=True)
data.update(status='preview',original_image=old,rollback=rollback)
(ROOT/'release.json').write_text(json.dumps(data,indent=2))
print(json.dumps({'status':'preview','second_account_navigation_fixed':True}))
