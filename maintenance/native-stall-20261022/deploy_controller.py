import hashlib,json,shutil,subprocess,time
from pathlib import Path
D=Path('/opt/monitor/geo-capture/maintenance/20261022-native-stall');B=Path('/opt/monitor/geo-capture')
manifest=json.loads(Path('/tmp/stall22-controller-manifest.json').read_text())
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert json.loads((D/'controller-test-results.json').read_text())['exit_code']==0
backup=D/('controller-before-'+str(time.time_ns()));backup.mkdir()
for name,row in manifest.items():
 p=B/name;source=D/'controller-stage'/name
 assert digest(p)==row['before'] and digest(source)==row['sha256'],name
 shutil.copy2(p,backup/name)
for name in manifest:
 p=B/name;temp=p.with_name(p.name+'.stall22.tmp');shutil.copy2(D/'controller-stage'/name,temp);temp.chmod(0o644);temp.replace(p)
regression=D/'controller-regression';regression.mkdir(exist_ok=True)
for name in ('test_daily_tasks.py','test_runtime_reliability.py'):shutil.copy2(D/'controller-stage/tests'/name,regression/name)
subprocess.run(['systemctl','restart','geo-daily-control'],check=True,timeout=30)
out={'at':time.time(),'backup':str(backup),'files':{str(B/name):digest(B/name) for name in manifest},'tests':43}
(D/'controller-deployment.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
