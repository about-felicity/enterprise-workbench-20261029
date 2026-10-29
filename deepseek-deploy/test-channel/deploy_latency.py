import hashlib,json,shutil,subprocess,sys,time
from pathlib import Path
ROOT=Path('/opt/monitor/geo-capture/maintenance/20261017-input-latency');BASE=Path('/opt/monitor/geo-capture')
sys.path.insert(0,str(BASE))
def run(*args):return subprocess.check_output(args,stderr=subprocess.STDOUT,timeout=45,text=True).strip()
units=['geo-native@geo-panel-deepseek-app-20261017-094524.service','geo-native@geo-panel-deepseek2-20261017-134730-bf1a1e9e.service']
before={u:run('systemctl','show',u,'-p','MainPID','--value') for u in units}
baseline={i['server']:i['sha256'] for i in json.loads((BASE/'maintenance/20261015-unified/current-manifest.json').read_text())['files']}
names=['scrcpy_stream.py','deepseek_android_login.py','fleet_status.py','deepseek_login.html']
for name in names:
 target=BASE/name;assert hashlib.sha256(target.read_bytes()).hexdigest()==baseline[str(target)],name
 backup=ROOT/'backup'/name;backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,backup)
root=BASE/'manual-login/deepseek_test';request=json.loads((root/'request.json').read_text());assert request['model']=='deepseek_test'
assert len(request['id'])==32 and all(c in '0123456789abcdef' for c in request['id'])
run('systemctl','stop','geo-deepseek-manual-login-'+request['id'][:12]+'.service')
state=json.loads((root/'state.json').read_text());state.update(status='failed',message='低延迟投屏已更新，请重开页面',updated_at=time.time());(root/'state.json').write_text(json.dumps(state,ensure_ascii=False))
for name in names:shutil.copy2(ROOT/'workspace'/name,BASE/name)
run('systemctl','restart','geo-monitor-status.service')
from manual_login import start
start(BASE,'/home/user/redroid-deepseek-test','manual-test',0,model='deepseek_test')
after={u:run('systemctl','show',u,'-p','MainPID','--value') for u in units};assert before==after
(ROOT/'release.json').write_text(json.dumps({'at':time.time(),'collector_pids_before':before,'collector_pids_after':after,'test_account_preserved':True,'status':'published'},indent=2))
print('published; only sandbox projection restarted; production collectors unchanged')
