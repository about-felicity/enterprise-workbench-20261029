"""Stage the scoped patch without touching the running queue or login."""
import sys,shlex,json,hashlib
from pathlib import Path
sys.path.insert(0,str(Path('redroid-deploy').resolve()))
from remote import connect
files={}
for name in ('native_models.js','native_client.py','native_core.py','history_refresh.py'):
 files['yuanbao-deploy/'+name]=name
for name in ('test_native_core.py','test_history_refresh.py','test_native_client_recovery.py','test_binding_recovery.py'):
 files['yuanbao-deploy/tests/'+name]='tests/'+name
files['redroid-deploy/question_only_worker.py']='question_only_worker.py'
client,password=connect()
try:
 command='mkdir -p /tmp/yuanbao-stall22-stage/tests'
 _,out,err=client.exec_command(command);assert out.channel.recv_exit_status()==0,err.read().decode()
 with client.open_sftp() as sftp:
  for local,relative in files.items():sftp.put(local,'/tmp/yuanbao-stall22-stage/'+relative)
 print(json.dumps({'staged':len(files),'sha':{r:hashlib.sha256(Path(p).read_bytes()).hexdigest() for p,r in files.items()}}))
finally:client.close()
