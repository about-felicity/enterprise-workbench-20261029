import os,json,hashlib,shutil,subprocess,time,pwd
from pathlib import Path
from creation import parallel,studio
base=Path('/opt/monitor/geo-content');candidate=Path('/tmp/creation-go-20261026');backup=base/'maintenance/creation-go-20261026';(backup/'before').mkdir(parents=True,exist_ok=True)
baseline={'materials.py': '85809fd6ad9c4e58d1303a471b3b998dbb3aff141053081c0b1dfc221d002264', 'client.py': '9bd62afc07b3bd528a5d049261011f4ed78da69feaf0868ed830a5da1350b0ba', 'studio.py': 'c5312bd6beff37704f42b9e9f3726165819c2996feb1c36d4e6c4f8695ffa6d4', 'panel.html': 'a93b59c08602a6525330e32970c75015f39db9c250c4a1bd857e6a807992d4d2', 'wizard_sections.html': '49f7d1936fd6497d5b751164f2afaafa27e1d268cff4336ec9b9d49b3f6a0ea7'}
for name,digest in baseline.items():assert hashlib.sha256((base/'creation'/name).read_bytes()).hexdigest()==digest,'production changed '+name
assert not studio.plans(),'plans changed; reassess capture'
assert not [p.parent.name for p in (parallel.BASE/'runs').glob('*/job.json') if parallel.eligible(p.parent)],'active writing needs drain'
ps=subprocess.check_output(['ps','-eo','args'],text=True)
assert not any('geo_source_cards.cli' in l and '/geo-content/studio/' in l for l in ps.splitlines()),'active capture needs drain'
items=[]
for name in ['materials.py', 'client.py', 'studio.py', 'panel.html', 'wizard_sections.html', 'go_transport.py', 'test_go_transport.py', 'test_materials.py']:items.append((candidate/'creation'/name,base/'creation'/name,'geo-monitor-deploy/creation/'+name))
for name in ['go.mod','main.go','main_test.go']:items.append((candidate/'creation-go'/name,base/'creation-go'/name,'geo-monitor-deploy/creation-go/'+name))
binary=base/'bin/creation-runner';items.append((candidate/'creation-go/creation-runner',binary,None))
drops={Path('/etc/systemd/system/geo-content-worker.service.d/zz-go.conf'):'[Service]\nExecStart=\nExecStart=/opt/monitor/geo-content/bin/creation-runner serve\nEnvironment=GEO_CREATION_CONCURRENCY=10\nKillMode=mixed\nTimeoutStopSec=1800\n',Path('/etc/systemd/system/geo-creation-studio.service.d/dynamic.conf'):'[Service]\nEnvironment=GEO_CREATION_CAPTURE_LIMIT=10\nEnvironment=GEO_CREATION_CAPTURE_MIN_MB=1200\nMemoryHigh=4G\nMemoryMax=5G\n'}
for target in drops:assert not target.exists(),'unexpected existing dropin'
changed=[]
subprocess.run(['systemctl','stop','geo-content-worker'],check=True,timeout=45)
subprocess.run(['systemctl','stop','geo-creation-studio'],check=True,timeout=45)
try:
 for source,target,mapping in items:
  saved=backup/'before'/target.relative_to('/')
  if target.exists():saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,saved)
  changed.append((target,saved))
  target.parent.mkdir(parents=True,exist_ok=True);temp=target.with_name(target.name+'.go-tmp');shutil.copy2(source,temp);os.replace(temp,target)
 binary.chmod(0o755);binary.parent.chmod(0o755)
 owner=pwd.getpwnam('user');pool=base/'search-pool'
 for folder in [pool,pool/'slots']:
  folder.mkdir(parents=True,exist_ok=True);os.chown(folder,owner.pw_uid,owner.pw_gid);folder.chmod(0o700)
 for target,value in drops.items():target.parent.mkdir(parents=True,exist_ok=True);target.write_text(value)
 subprocess.run(['systemctl','daemon-reload'],check=True)
 subprocess.run(['systemctl','restart','geo-content-api','geo-content-worker','geo-creation-studio'],check=True,timeout=45)
 time.sleep(3)
 for service in ['geo-content-api','geo-content-worker','geo-creation-studio']:assert subprocess.check_output(['systemctl','is-active',service],text=True).strip()=='active',service
 health=json.loads((parallel.BASE/'worker_health.json').read_text());assert health['mode']=='go_dynamic' and health['max_parallel_jobs']==10 and not health['active_jobs']
 pid=int(subprocess.check_output(['systemctl','show','geo-content-worker','--property=MainPID','--value'],text=True));assert Path('/proc/'+str(pid)+'/exe').resolve()==binary
 assert (parallel.BASE/'model.sock').is_socket()
 result={'files':[{'source':mapping,'server':str(target),'sha256':hashlib.sha256(target.read_bytes()).hexdigest()} for _,target,mapping in items if mapping],'binary':{'server':str(binary),'sha256':hashlib.sha256(binary.read_bytes()).hexdigest()},'worker':health,'backup':str(backup),'checks':{'python':83,'go_race':True,'native_serve_drain':True,'paid_requests':0},'deepseek_capture_changed':False}
 for target,mapping in [(list(drops)[0],'geo-monitor-deploy/systemd/geo-content-worker-go.conf'),(list(drops)[1],'geo-monitor-deploy/systemd/geo-creation-studio-dynamic.conf')]:result['files'].append({'source':mapping,'server':str(target),'sha256':hashlib.sha256(target.read_bytes()).hexdigest()})
 (backup/'release.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))
except BaseException:
 subprocess.run(['systemctl','stop','geo-content-worker','geo-creation-studio'],timeout=45)
 for target,saved in changed:
  if saved.exists():shutil.copy2(saved,target)
  else:target.unlink(missing_ok=True)
 for target in drops:target.unlink(missing_ok=True)
 subprocess.run(['systemctl','daemon-reload']);subprocess.run(['systemctl','restart','geo-content-api','geo-content-worker','geo-creation-studio'])
 raise
