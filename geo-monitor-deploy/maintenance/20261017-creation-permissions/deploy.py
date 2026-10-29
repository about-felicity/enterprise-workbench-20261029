import json,os,pwd,shutil,sqlite3,subprocess,sys,time
from pathlib import Path
B=Path('/opt/monitor/geo-content');R=B/'maintenance/20261017-creation-permissions'
sys.path[:0]=[str(R/'stage'),str(B/'engine')]
from creation import materials
def read(p):return json.loads(Path(p).read_text())
def jobs():
 with sqlite3.connect('file:/opt/monitor/geo-capture/panel/control.sqlite?mode=ro',uri=True) as db:names=[r[0] for r in db.execute('select service from jobs join settings on current_batch=batch')]
 names+=['geo-content-worker.service']
 return {n:subprocess.check_output(['systemctl','show',n,'--property=MainPID,ActiveEnterTimestampMonotonic'],text=True) for n in names}
assert not (R/'release.json').exists(),'Inspect existing release before repeating'
assert not read(B/'materials/health.json').get('active_channels'),'Wait for private worker safe boundary'
before=jobs();shutil.copy2(B/'creation/materials.py',R/'materials.before.py')
original={'mode':oct(B.stat().st_mode&0o777),'gid':B.stat().st_gid}
shutil.copy2(R/'stage/creation/materials.py',B/'creation/materials.py')
owner=pwd.getpwnam('user')
for model in materials.CHANNELS:
 directory=materials.ROOT/'days/2026-10-17'/model/'collector';materials.collector_directory(directory,owner)
 command=['/usr/sbin/runuser','-u','user','--','python3','-c','from pathlib import Path;import sys;p=Path(sys.argv[1])/".permission-check";p.write_text("ok");assert p.read_text()=="ok";p.unlink()',str(directory)]
 subprocess.run(command,check=True)
subprocess.run(['systemctl','restart','geo-creation-materials.service'],check=True)
time.sleep(1)
health=read(B/'materials/health.json');after=jobs();assert before==after
result={'at':time.time(),'before_parent':original,'after_parent_mode':oct(B.stat().st_mode&0o777),'actual_user_writes_verified':True,'main_collectors_and_creation_worker_unchanged':True,'health':health,'before':before,'after':after}
(R/'release.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps({k:v for k,v in result.items() if k not in {'before','after'}},ensure_ascii=False))
