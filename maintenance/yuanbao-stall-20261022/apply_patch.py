"""Apply tested stage to stopped, runtime-masked current Yuanbao service."""
import ast,hashlib,json,shutil,subprocess,time
from pathlib import Path
stage=Path('/tmp/yuanbao-stall22-stage')
base=Path('/home/user/redroid-yuanbao')
report=Path('/opt/monitor/geo-capture/maintenance/20261022-yuanbao-stall')
backup=report/'backup';backup.mkdir(parents=True,exist_ok=True)
service='geo-native@geo-panel-yuanbao-20261022-090005-705819fb.service'
assert subprocess.check_output(['systemctl','show',service,'-p','ActiveState','--value'],text=True).strip()!='active'
files={n:base/n for n in ('native_models.js','native_client.py','native_core.py','history_refresh.py')}
files.update({'tests/'+p.name:base/'tests'/p.name for p in (stage/'tests').glob('*.py')})
files['question_only_worker.py']=Path('/home/user/redroid-doubao/geo-batch-code/question_only_worker.py')
old_expected={'native_client.py':'26540d71f38fb0decc340a75114593d0c2252a41ad402d34123940a6e40bdca2',
 'native_core.py':'cdb702c45571830ff2699f4e173c0ea0c80e761113d3b7b0521d95142b42fa5e',
 'native_models.js':'3522e55b0c4e2dcfa09228e9ebe9f991628e1a3750eb366494336ab5787761b8',
 'history_refresh.py':'865e3877a9d813d23fd2619469f3d740d97354f4c3d2124cf33fcdf172604639'}
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
previous=json.loads((report/'deployment.json').read_text()).get('files',{}) if (report/'deployment.json').exists() else {}
for name,expected in old_expected.items():assert digest(files[name]) in {expected,previous.get(str(files[name]))},(name,'changed since diagnosis')
for name,target in files.items():
 source=stage/name
 if name.endswith('.py'):ast.parse(source.read_text())
 saved=backup/name;saved.parent.mkdir(parents=True,exist_ok=True)
 if target.exists() and not saved.exists():shutil.copy2(target,saved)
for name,target in files.items():
 temp=target.with_name(target.name+'.repair22.tmp');shutil.copy2(stage/name,temp);temp.chmod(0o600);temp.replace(target)
out={'at':time.time(),'files':{str(target):digest(target) for target in files.values()},'service':service}
(report/'deployment.json').write_text(json.dumps(out,indent=2))
print(json.dumps(out))
