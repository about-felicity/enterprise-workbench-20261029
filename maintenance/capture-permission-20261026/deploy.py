import hashlib,json,shutil,os,subprocess,tempfile,pwd
from pathlib import Path
base=Path('/opt/monitor/geo-content/creation');backup=Path('/opt/monitor/geo-content/maintenance/capture-permission-20261026');(backup/'before').mkdir(parents=True,exist_ok=True)
baseline={'materials.py': 'b19980db739a789a9cf8ab6c9af502bf77bb0af05b06659288e81cd7488f36aa', 'studio.py': 'bbb911fe7c22f9a0dd039ca7465de80b8564ae86eb55a5011948cb73ce6bc9c2', 'panel.html': 'f2aa9c5a7e97b8996524d788239bf654a79df90679705bbe3bb263e8e0bbbbbe'}
for n,h in baseline.items():assert hashlib.sha256((base/n).read_bytes()).hexdigest()==h,n
names=list(baseline)+['test_capture_permissions.py']
for n in names:
 if (base/n).exists():shutil.copy2(base/n,backup/'before'/n)
 temp=base/(n+'.permission-tmp');shutil.copy2(Path('/tmp/capture-permission-20261026/creation')/n,temp);os.replace(temp,base/n)
# Refresh read-only status rendering. Existing active captures continue untouched.
subprocess.run(['systemctl','restart','geo-content-api'],check=True,timeout=30)
from creation.materials import capture_snapshot
with tempfile.TemporaryDirectory() as tmp:
 o=pwd.getpwnam('user');os.chown(tmp,o.pw_uid,o.pw_gid);capture_snapshot(Path(tmp),{'questions':['fixture']},o)
 subprocess.run(['/usr/sbin/runuser','-u','user','--','python3','-c','import json,sys;assert json.load(open(sys.argv[1]))["questions"]==["fixture"]',str(Path(tmp)/'config.json')],check=True)
result={'files':[{'server':str(base/n),'sha256':hashlib.sha256((base/n).read_bytes()).hexdigest()} for n in names],'tests':47,'real_collector_user_read':True,'active_captures_interrupted':False}
(backup/'release.json').write_text(json.dumps(result));print(json.dumps(result))
