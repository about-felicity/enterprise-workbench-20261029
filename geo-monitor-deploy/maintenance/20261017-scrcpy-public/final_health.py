import hashlib,json,subprocess,sys,time,zipfile
from pathlib import Path
sys.path.insert(0,'/opt/monitor/geo-capture')
from control_panel import Controller
from manual_login import state
ROOT=Path('/opt/monitor/geo-capture/maintenance/20261017-scrcpy-public')
release=json.loads((ROOT/'release.json').read_text())
models=Controller(Path('/opt/monitor/geo-capture')).all()['models']
result={'at':time.time(),'release_status':release['status'],'models':[],'collector_pids':{},'manual_flows':{}}
for m in models:
    current=m['current'] if 'current' in m else m.get('job',{})
    result['models'].append({'model':m['id'],'current':{k:current.get(k) for k in ('batch','state','planned','captured','processed','pending_delivery','heartbeat_age','progress')},'login_monitor':{k:m.get('login_monitor',{}).get(k) for k in ('status','checked_at','next_check_at','probe_status')}})
for unit,pid in release['collectors_before'].items():
    actual=subprocess.check_output(['systemctl','show',unit,'-p','MainPID','--value'],text=True).strip()
    result['collector_pids'][unit]=actual
    if pid!='0':assert actual==pid,(unit,pid,actual)
for model in ('deepseek','deepseek2'):
    result['manual_flows'][model]=state('/opt/monitor/geo-capture',model).get('status')
result['timer']=subprocess.check_output(['systemctl','show','geo-deepseek-auth-check.timer','-p','ActiveState','-p','LastTriggerUSec','-p','NextElapseUSecMonotonic'],text=True)
result['scrcpy_sha256']=hashlib.sha256(Path('/opt/monitor/geo-capture/vendor/scrcpy-server-v5.0').read_bytes()).hexdigest()
result['preview']=json.loads(subprocess.check_output(['docker','inspect','monitor-dashboard-scrcpy-preview'],text=True))[0]
assert result['preview']['Name']=='/monitor-dashboard-scrcpy-preview' and result['preview']['Mounts']==[]
result['preview']={k:result['preview'][k] for k in ('Id','Name','Image','Mounts')}
(ROOT/'final-health.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps(result,ensure_ascii=False))
with zipfile.ZipFile('/tmp/geo-scrcpy-public-evidence.zip','w',zipfile.ZIP_DEFLATED) as z:
    for name in ['release.json','qa-fixture.json','qa-preview.json','qa-production.json','qa-public.json','final-health.json','fixture-desktop.png','fixture-mobile.png','public-healthy-desktop.png','public-healthy-mobile.png']:
        p=ROOT/name
        if p.is_file():z.write(p,name)
    z.write('/opt/monitor/geo-capture/maintenance/20261015-unified/current-source-mapping.json','source-mapping.json')
