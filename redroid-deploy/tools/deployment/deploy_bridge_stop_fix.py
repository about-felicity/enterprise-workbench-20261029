
# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import subprocess,shutil,os,time,json
from pathlib import Path
os.umask(0o077)
base=Path('/home/user/redroid-doubao')
assert subprocess.run(['systemctl','is-active','redroid-geo-products-account2.service'],capture_output=True,text=True).stdout.strip() in ('inactive','failed')
backup=base/'account2'/('bridge-stop-fix-'+str(int(time.time())))
backup.mkdir(mode=0o700)
for src,dest in [('geo_batch_bridge.new.py',base/'geo-batch-code/geo_batch_bridge.py'),('test_geo_batch_bridge.new.py',base/'geo-batch-code/test_geo_batch_bridge.py'),('redroid-geo-products-account2.new.service',Path('/etc/systemd/system/redroid-geo-products-account2.service'))]:
    shutil.copy2(dest,backup/dest.name)
    shutil.copyfile(base/src,dest)
subprocess.run(['systemctl','daemon-reload'],check=True)
subprocess.run([str(base/'worker-venv/bin/python'),'-m','unittest','test_geo_batch_bridge','test_unattended'],cwd=base/'geo-batch-code',check=True)
health=base/'batches/geo-products-21x5-account2-relogin-20261013/bridge_health.json'
shutil.copy2(health,backup/'bridge_health-stale.json')
env=dict(os.environ,DOUBAO_BATCH='geo-products-21x5-account2-relogin-20261013')
subprocess.run([str(base/'worker-venv/bin/python'),str(base/'geo-batch-code/geo_batch_bridge.py'),'--mark-stopped'],env=env,check=True)
print('Stop-state fix deployed and stale snapshot marked stopped. Backup:',backup)
