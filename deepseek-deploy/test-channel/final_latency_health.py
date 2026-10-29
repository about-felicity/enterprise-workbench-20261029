import json,sys,time,subprocess,zipfile
from pathlib import Path
BASE=Path('/opt/monitor/geo-capture');ROOT=BASE/'maintenance/20261017-input-latency'
sys.path.insert(0,str(BASE));from control_panel import Controller
result={'at':time.time(),'models':[]}
for m in Controller(BASE).all()['models']:
 current=m['current'];monitor=m.get('login_monitor',{})
 result['models'].append({'model':m['id'],'batch':current.get('batch'),'state':current.get('state'),'captured':current.get('captured'),'processed':current.get('processed'),'planned':current.get('planned'),'pending_delivery':current.get('pending_delivery'),'auth_status':monitor.get('status')})
result['worker_services']={}
for unit in ['geo-native@geo-panel-deepseek-app-20261017-094524.service','geo-native@geo-panel-deepseek2-20261017-134730-bf1a1e9e.service']:
 result['worker_services'][unit]=subprocess.check_output(['systemctl','show',unit,'-p','MainPID','-p','ExecMainStatus','-p','ActiveState'],text=True)
(ROOT/'final-health.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
with zipfile.ZipFile('/tmp/geo-input-latency-evidence.zip','w',zipfile.ZIP_DEFLATED) as z:
 for name in ['before.json','before-lan.json','after-lan.json','after-public.json','decoder-lan.json','canvas-lan.json','ui-public-comparison.json','qa-fixture.json','release.json','final-health.json','fixture-mobile.png','fixture-desktop.png']:
  p=ROOT/name
  if p.exists():z.write(p,name)
