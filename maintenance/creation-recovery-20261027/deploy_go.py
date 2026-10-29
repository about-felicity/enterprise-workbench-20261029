import hashlib,shutil,os,json
from pathlib import Path
base=Path('/opt/monitor/geo-content');backup=base/'maintenance/recovery-20261027/code-before'
assert hashlib.sha256((base/'creation-go/main.go').read_bytes()).hexdigest()=='2557368c2074be4987dcd51d6a2dfee096833799df88ab11cb23ae13c47aab4a'
rows=[]
for src,dst in [('main.go','creation-go/main.go'),('main_test.go','creation-go/main_test.go'),('creation-runner','bin/creation-runner')]:
 p=base/dst;candidate=Path('/tmp/creation-recovery-go')/src
 shutil.copy2(p,backup/(src+'.pre-cadence'))
 tmp=p.with_suffix('.deploy-tmp');shutil.copyfile(candidate,tmp);os.chmod(tmp,p.stat().st_mode);os.chown(tmp,p.stat().st_uid,p.stat().st_gid);os.replace(tmp,p)
 rows.append({'server':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
# The running writer server keeps its open executable; subsequent capture launches
# load the new binary without interrupting paid model calls or browser sessions.
print(json.dumps({'files':rows,'capture_start_interval_seconds':60,'existing_processes_interrupted':False}))
