import json
from pathlib import Path
import shutil
import subprocess
import time

root=Path('/opt/monitor/geo-capture/maintenance/20261017-yuanbao-text-audit')
state=json.loads((root/'reanalysis-status.json').read_text())
assert state['status'].startswith('waiting_') and time.time()-state['time']<40,'Only reload between paid model requests'
shutil.copy2(root/'reanalysis-status.json',root/'reanalysis-phase1.json')
for source,target in [('/tmp/geo-native-text-v2-candidate-1017.py','/opt/monitor/monitor_core/native_text.py'),('/tmp/geo-yuanbao-saver-v2-1017.py','/opt/monitor/save_doubao_refs.py')]:
 path=Path(target);shutil.copy2(path,root/(path.name+'.before-v2'))
 compile(Path(source).read_text(),target,'exec');shutil.copy2(source,target)
code="""import os,pathlib,signal,json
matches=[]
for p in pathlib.Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:a=(p/'cmdline').read_bytes().split(b'\\0')
 except OSError:continue
 if len(a)>=3 and a[0].endswith(b'python') and a[1]==b'/app/geo-capture/maintenance/20261017-yuanbao-text-audit/reanalyse.py':matches.append(int(p.name))
assert len(matches)==1,matches
os.kill(matches[0],signal.SIGINT)
print(json.dumps({'interrupted_idle_repair_pid':matches[0]}))
"""
subprocess.run(['docker','exec','monitor-dashboard-api','python','-c',code],check=True)
for _ in range(30):
 status=json.loads(subprocess.check_output(['docker','inspect','monitor-product-worker']))[0]['State']['Status']
 if status=='running':break
 time.sleep(.5)
else:raise RuntimeError('Expected ordinary enrichment to resume after repair interruption')
subprocess.run(['docker','stop','monitor-product-worker'],check=True,timeout=45)
subprocess.run(['docker','exec','monitor-dashboard-api','python','/app/geo-capture/maintenance/20261017-yuanbao-text-audit/finish_format.py'],check=True)
print('Format v2 loaded; ordinary workers remain intact; resume bounded reviewer next')
