"""Stage and verify the bounded recovery guard; no question or paid API calls."""
import hashlib,json,subprocess,sys,time,zipfile,shutil,ast
from pathlib import Path
D=Path('/opt/monitor/geo-capture/maintenance/20261023-yuanbao-unbound');S=D/'stage'
with zipfile.ZipFile('/tmp/yuanbao-refine.zip') as z:
 for name in z.namelist():
  assert name in ('yuanbao/unbound_history.py','yuanbao/tests/test_unbound_history.py')
  z.extract(name,S)
env=__import__('os').environ.copy()
env['PYTHONPATH']=str(S/'yuanbao')+':'+str(S/'doubao')+':/home/user/redroid-yuanbao/tools:/home/user/redroid-doubao/geo-batch-code'
cmd=['/home/user/redroid-doubao/worker-venv/bin/python','-B','-m','unittest','discover','-s',str(S/'yuanbao/tests'),'-v']
r=subprocess.run(cmd,env=env,capture_output=True,text=True)
(D/'yuanbao-tests-final.log').write_text(r.stdout+r.stderr)
print((r.stdout+r.stderr)[-1200:]);assert r.returncode==0
unit='geo-native@geo-panel-yuanbao-20261023-090004-d6b66215.service'
root=Path('/home/user/redroid-yuanbao/batches/geo-panel-yuanbao-20261023-090004-d6b66215')
assert not (root/'maintenance_pause.json').exists(),'Do not override a user pause'
manifest=json.loads((S/'manifest.json').read_text());rows={k:manifest[k] for k in ('yuanbao/unbound_history.py','yuanbao/tests/test_unbound_history.py')}
digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for key,row in rows.items():
 assert digest(Path(row['target']))==row['sha256'],'Unexpected production source change'
 ast.parse((S/key).read_text())
backup=D/('guard-before-'+str(time.time_ns()));backup.mkdir()
# Stop only the collector process. Its SIGTERM closes the reader; the App,
# original in-flight request, durable task and login are preserved.
subprocess.run(['systemctl','mask','--runtime',unit],check=True)
try:
 subprocess.run(['systemctl','stop',unit],check=True,timeout=45)
 for key,row in rows.items():
  target=Path(row['target']);saved=backup/key;saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,saved)
  tmp=target.with_name(target.name+'.guard23.tmp');shutil.copy2(S/key,tmp);tmp.chmod(0o644);tmp.replace(target)
  row['sha256']=digest(target)
finally:
 subprocess.run(['systemctl','unmask','--runtime',unit],check=True)
 subprocess.run(['systemctl','start',unit],check=True)
for key,row in rows.items():manifest[key]=row
(S/'manifest.json').write_text(json.dumps(manifest,indent=2))
out={'at':time.time(),'backup':str(backup),'files':{row['target']:row['sha256'] for row in rows.values()},'tests_exit':r.returncode,'app_stopped':False,'question_resent':False}
(D/'guard-deployment.json').write_text(json.dumps(out,indent=2));print(json.dumps(out))
