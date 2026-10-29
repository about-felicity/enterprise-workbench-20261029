import json,shutil,subprocess,time
from pathlib import Path
import requests
B=Path('/opt/monitor/geo-capture');R=B/'maintenance/20261016-deepseek-session'
backup=R/'fast-backup';backup.mkdir(exist_ok=False)
for source,name in [('/tmp/login-fast-fleet.py','fleet_status.py'),('/tmp/login-fast.html','deepseek_login.html')]:
 shutil.copy2(B/name,backup/name);temp=B/(name+'.fast-new');shutil.copy2(source,temp);temp.chmod(0o644);temp.replace(B/name)
subprocess.run(['systemctl','restart','geo-monitor-status.service'],check=True)
s=requests.Session();s.trust_env=False
for attempt in range(15):
 try:
  start=time.perf_counter();response=s.get('http://127.0.0.1:3000/api/geo-capture/login/ui',timeout=5)
  if response.status_code==200:break
 except requests.RequestException:pass
 time.sleep(.3)
else:raise RuntimeError('Login page did not become ready')
page_ms=(time.perf_counter()-start)*1000
start=time.perf_counter();state=s.get('http://127.0.0.1:3000/api/geo-capture/login/state',timeout=5);state.raise_for_status()
assert len(state.json()['csrf'])==64
state_ms=(time.perf_counter()-start)*1000
start=time.perf_counter();frame=s.get('http://127.0.0.1:3000/api/geo-capture/login/frame',timeout=5)
report={'at':time.time(),'login_ui_ms':round(page_ms,1),'state_ms':round(state_ms,1),'frame_ms':round((time.perf_counter()-start)*1000,1),'frame_status':frame.status_code,'flow_status':state.json()['status'],'production_html_fast':"fetch('/api/panel'" not in response.text,'manual_login_service_restarted':False,'collectors_restarted':False}
(R/'fast-release.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
