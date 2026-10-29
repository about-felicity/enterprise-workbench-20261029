import os,shutil,sqlite3,subprocess,sys
from pathlib import Path
sys.path.insert(0,'/tmp')
from wenxin_retry import candidates
D=Path('/opt/monitor/geo-capture/maintenance/20261027-wenxin-retry');D.mkdir(parents=True,exist_ok=True)
for item in candidates():
 for runtime in item['runtimes']:
  if not (runtime/'tasks.sqlite').exists():continue
  backup=D/'before'/runtime.as_posix().lstrip('/');backup.mkdir(parents=True,exist_ok=True)
  if not (backup/'tasks.sqlite').exists():
   with sqlite3.connect(runtime/'tasks.sqlite') as db:
    with sqlite3.connect(backup/'tasks.sqlite') as out:db.backup(out)
  for name in ('search_recovery.json','verification_probe_latest.json'):
   if (runtime/name).exists():shutil.copy2(runtime/name,backup/name)
 for block in item['blocks']:
  target=D/'before'/block.as_posix().lstrip('/');target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(block,target)
for source,target in [('wenxin_retry.py','/opt/monitor/geo-capture/wenxin_retry.py'),('wenxin-readiness-probe.py','/opt/monitor/geo-capture/wenxin_readiness_probe.py'),('geo-wenxin-retry.service','/etc/systemd/system/geo-wenxin-retry.service'),('geo-wenxin-retry.timer','/etc/systemd/system/geo-wenxin-retry.timer')]:
 p=Path(target);assert not p.exists(),target
 shutil.copy2(Path('/tmp')/source,p);p.chmod(0o644)
subprocess.run(['systemctl','daemon-reload'],check=True)
subprocess.run(['systemctl','enable','--now','geo-wenxin-retry.timer'],check=True)
subprocess.run(['systemctl','start','--no-block','geo-wenxin-retry.service'],check=True)
print('Deployed bounded retry service and started first check')
