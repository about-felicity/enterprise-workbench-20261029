import ast,hashlib,json,subprocess,shutil,time
from pathlib import Path
D=Path('/opt/monitor/geo-capture/maintenance/20261022-native-stall');S=D/'stage';mapping=json.loads((S/'manifest.json').read_text())
services=['geo-native@geo-panel-doubao1-20261022-090003-0fe844d7.service','geo-native@geo-panel-yuanbao-20261022-090005-705819fb.service']
for service in services:assert subprocess.check_output(['systemctl','show',service,'-p','ActiveState','--value'],text=True).strip() in ('inactive','failed')
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
backup=D/('source-before-'+str(time.time_ns()));backup.mkdir()
for name,row in mapping.items():
 target=Path(row['target']);source=S/name
 assert digest(source)==row['sha256']
 if source.suffix=='.py':ast.parse(source.read_text())
 else:json.loads(source.read_text())
 if row['before']:assert target.is_file() and digest(target)==row['before'],('Source changed since diagnosis',name)
 elif '/tests/' not in str(target):assert not target.exists(),('Unexpected new target',target)
 if target.exists():
  saved=backup/name;saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,saved)
for name,row in mapping.items():
 if row['before']==row['sha256']:continue
 target=Path(row['target']);target.parent.mkdir(parents=True,exist_ok=True)
 temporary=target.with_name(target.name+'.stall22.tmp');shutil.copy2(S/name,temporary);temporary.chmod(0o644);temporary.replace(target)
out={'at':time.time(),'backup':str(backup),'files':{r['target']:digest(Path(r['target'])) for r in mapping.values()},
     'tests':{'doubao':38,'yuanbao':38},'queue_modified':False,'login_modified':False,'new_question_during_deployment':False}
(D/'deployment.json').write_text(json.dumps(out,indent=2));print(json.dumps({'at':out['at'],'files':len(mapping),'backup':str(backup)}))
subprocess.run(['systemctl','unmask','--runtime',*services],check=True)
subprocess.run(['systemctl','daemon-reload'],check=True)
subprocess.run(['systemctl','start',*services],check=True)
