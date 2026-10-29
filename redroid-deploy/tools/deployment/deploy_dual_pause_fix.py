"""Back up stopped services/queues, deploy and validate before recovery."""

# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import subprocess,sqlite3,json,time,os,shutil
from pathlib import Path
os.umask(0o077)
base=Path('/home/user/redroid-doubao')
services=('redroid-geo-products.service','redroid-geo-products-account2.service')
for service in services:
 assert subprocess.run(['systemctl','is-active',service],capture_output=True,text=True).stdout.strip() in ('inactive','failed')
backup=base/('dual-pause-fix-'+str(int(time.time())));backup.mkdir(mode=0o700)
for batch in ('geo-products-21x5-account1-20261014','geo-products-21x5-account2-relogin-20261013'):
 root=base/'batches'/batch
 with sqlite3.connect(root/'tasks.sqlite') as src,sqlite3.connect(backup/(batch+'.sqlite')) as dest:src.backup(dest)
 shutil.copy2(root/'bridge_health.json',backup/(batch+'-health.json'))
for file in ('unattended_core.py','unattended_worker.py','geo_batch_bridge.py','test_unattended.py','test_geo_batch_bridge.py'):
 dest=base/'geo-batch-code'/file
 shutil.copy2(dest,backup/file);shutil.copyfile(base/('pause-fix-'+file),dest)
shutil.copy2(base/'runtime_preflight.py',backup/'runtime_preflight.py')
shutil.copyfile(base/'pause-fix-runtime_preflight.py',base/'runtime_preflight.py')
for service in services:
 target=Path('/etc/systemd/system')/service
 shutil.copy2(target,backup/service);shutil.copyfile(base/('pause-fix-'+service),target)
subprocess.run(['systemctl','daemon-reload'],check=True)
subprocess.run([str(base/'worker-venv/bin/python'),'-m','unittest','test_unattended','test_geo_batch_bridge'],cwd=base/'geo-batch-code',check=True)
for container in ('doubao-hpe14-13-test','doubao-hpe14-account2'):
 subprocess.run([str(base/'worker-venv/bin/python'),str(base/'runtime_preflight.py'),'--container',container],check=True)
print('Dual pause fix validated; services remain stopped for guarded reconciliation. Backup:',backup,flush=True)
