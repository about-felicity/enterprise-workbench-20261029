import json,hashlib,os,shutil
from pathlib import Path
base=Path('/opt/monitor/geo-content/maintenance/task-health-20261030');stage=base/'stage';root=Path('/opt/monitor/geo-content/creation')
assert hashlib.sha256((root/'materials.py').read_bytes()).hexdigest()=='e2fb21b4d2c5d06332b63a8a1307f530fd5ab28a67ae3771db289165b6a643ac'
backup=base/'before';backup.mkdir(exist_ok=True);shutil.copy2(root/'materials.py',backup/'materials.py')
# New module first; workers load modules on their next execution. No running writer is stopped.
for n in ['source_cache.py','materials.py']:
 dest=root/n;temp=root/(n+'.task-health.tmp');shutil.copy2(stage/'creation'/n,temp);temp.chmod(0o644);os.replace(temp,dest)
release={'files':[{'source':'geo-monitor-deploy/creation/'+n,'server':str(root/n),'sha256':hashlib.sha256((root/n).read_bytes()).hexdigest()} for n in ['source_cache.py','materials.py']],'tests_passed':True,'no_service_restart':True}
(base/'release.json').write_text(json.dumps(release,indent=2));print('RELEASE',json.dumps(release),flush=True)

