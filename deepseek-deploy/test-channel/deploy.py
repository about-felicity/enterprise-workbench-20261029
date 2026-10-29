import hashlib,json,shutil,subprocess,sys,time,zipfile
from pathlib import Path
ROOT=Path('/opt/monitor/geo-capture/maintenance/20261017-deepseek-test');STAGE=ROOT/'workspace';BASE=Path('/opt/monitor/geo-capture')
def run(*args):return subprocess.check_output(args,stderr=subprocess.STDOUT,text=True,timeout=90).strip()
mode=sys.argv[1]
if mode=='backend':
 assert not (ROOT/'release.json').exists()
 ROOT.mkdir(parents=True,exist_ok=True)
 units=['geo-native@geo-panel-deepseek-app-20261017-094524.service','geo-native@geo-panel-deepseek2-20261017-134730-bf1a1e9e.service']
 before={u:run('systemctl','show',u,'-p','MainPID','--value') for u in units}
 baseline={i['server']:i['sha256'] for i in json.loads((BASE/'maintenance/20261015-unified/current-manifest.json').read_text())['files']}
 for n in ['scrcpy_stream.py','deepseek_android_login.py','manual_login.py','fleet_status.py','panel.html','deepseek_login.html']:
  target=BASE/n;assert hashlib.sha256(target.read_bytes()).hexdigest()==baseline[str(target)],n
  backup=ROOT/'backup'/n;backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,backup)
  shutil.copy2(STAGE/'geo-monitor-deploy'/n,target)
 run('systemctl','restart','geo-monitor-status.service')
 after={u:run('systemctl','show',u,'-p','MainPID','--value') for u in units};assert before==after
 old=run('docker','inspect','monitor-dashboard','--format','{{.Image}}');rollback='monitor-dashboard:before-test-channel-'+str(int(time.time()));run('docker','tag',old,rollback)
 (ROOT/'release.json').write_text(json.dumps({'status':'backend','collectors':before,'original_image':old,'rollback':rollback},indent=2))
 print('backend updated; collector PIDs unchanged')
elif mode=='build':
 data=json.loads((ROOT/'release.json').read_text());assert data['status']=='backend'
 (ROOT/'Dockerfile').write_text(f"FROM {data['rollback']}\nCOPY workspace/geo-monitor-deploy/dashboard-integration/app/api/geo-capture/ /dashboard/app/api/geo-capture/\nWORKDIR /dashboard\nRUN node --experimental-strip-types --test tests/capture-gateway.test.mjs tests/creation-gateway.test.mjs\nRUN NEXT_TELEMETRY_DISABLED=1 NODE_OPTIONS=--max-old-space-size=1536 npm run build\n")
 with (ROOT/'build.log').open('w') as log:subprocess.run(['docker','build','-t','monitor-dashboard:deepseek-test-20261017',str(ROOT)],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=600)
 data['status']='built';(ROOT/'release.json').write_text(json.dumps(data,indent=2));print('built')
elif mode=='publish':
 data=json.loads((ROOT/'release.json').read_text());assert data['status']=='built'
 assert run('docker','inspect','monitor-dashboard','--format','{{.Image}}')==data['original_image']
 command=['docker','compose','-p','local-server','-f','/opt/monitor/deploy/local-server/docker-compose.yml','up','-d','--no-deps','--no-build','--force-recreate','dashboard']
 run('docker','tag','monitor-dashboard:deepseek-test-20261017','monitor-dashboard:local')
 try:print(run(*command))
 except Exception:run('docker','tag',data['rollback'],'monitor-dashboard:local');run(*command);raise
 shutil.copy2(STAGE/'geo-monitor-deploy/dashboard-integration/app/api/geo-capture/[...path]/route.ts','/opt/monitor/yuanbao_monitor/dashboard/app/api/geo-capture/[...path]/route.ts')
 for u,pid in data['collectors'].items():assert run('systemctl','show',u,'-p','MainPID','--value')==pid
 data.update(status='published',at=time.time());(ROOT/'release.json').write_text(json.dumps(data,indent=2));print('published; collector PIDs unchanged')
