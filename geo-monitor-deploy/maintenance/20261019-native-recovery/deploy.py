"""Scoped repair. Preserve original task databases, send intents and native bindings."""
import json,shutil,sqlite3,subprocess,time
from pathlib import Path
ROOT=Path('/opt/monitor/geo-capture/maintenance/20261019-native-recovery')
backup=ROOT/('backup-'+str(int(time.time())));backup.mkdir()
jobs={
 'doubao1':Path('/home/user/redroid-doubao/batches/geo-panel-doubao1-20261018-090003-c0f12e95'),
 'yuanbao':Path('/home/user/redroid-yuanbao/batches/geo-panel-yuanbao-20261018-090005-1655ce1c')}
for model,root in jobs.items():
    with sqlite3.connect('file:'+str(root/'tasks.sqlite')+'?mode=ro',uri=True) as src,sqlite3.connect(backup/(model+'.sqlite')) as dst:src.backup(dst)
    shutil.copy2(root/'bridge_health.json',backup/(model+'.health.before.json'))
    for pattern in ('*.binding.json','*.pre-send.json'):
        folder=backup/model;folder.mkdir(exist_ok=True)
        for p in root.glob(pattern):shutil.copy2(p,folder/p.name)
services=['geo-native@'+p.name+'.service' for p in jobs.values()]
mapping={
 'redroid-deploy/unattended_core.py':['/home/user/redroid-doubao/geo-batch-code/unattended_core.py'],
 'redroid-deploy/question_only_core.py':['/home/user/redroid-doubao/geo-batch-code/question_only_core.py'],
 'redroid-deploy/question_only_worker.py':['/home/user/redroid-doubao/geo-batch-code/question_only_worker.py'],
 'redroid-deploy/geo_batch_bridge.py':['/home/user/redroid-doubao/geo-batch-code/geo_batch_bridge.py'],
 'yuanbao-deploy/android_ui.py':['/home/user/redroid-yuanbao/android_ui.py'],
 'geo-monitor-deploy/runtime_reliability.py':['/opt/monitor/geo-capture/runtime_reliability.py','/home/user/redroid-doubao/geo-batch-code/runtime_reliability.py','/home/user/redroid-yuanbao/runtime_reliability.py']}
try:
    for service in services:subprocess.run(['systemctl','stop',service],check=True,timeout=40)
    for source,targets in mapping.items():
        for target in targets:
            p=Path(target);shutil.copy2(p,backup/(target.strip('/').replace('/','__')))
            shutil.copy2(ROOT/'candidate'/source,p)
finally:
    for service in services:subprocess.run(['systemctl','start','--no-block',service],check=True,timeout=20)
print(json.dumps({'backup':str(backup),'services':services}))
