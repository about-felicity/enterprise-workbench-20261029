"""Remove only this verified preview and unused build cache; preserve all data/evidence."""
import json
from pathlib import Path
import shutil
import subprocess
import time
base=Path('/opt/monitor/geo-capture');out=base/'maintenance/20261015-unified'
assert json.loads((out/'creation-public-qa.json').read_text())['passed']
release=json.loads((base/'creation_frontend.json').read_text());assert release['status']=='published'
proof=json.loads(subprocess.check_output(['docker','inspect','monitor-dashboard-creation-preview'],text=True))[0]
assert proof['Config']['Image']=='monitor-dashboard:creation-20261015'
assert not proof['Mounts'],'Preview must have no persistent mounts'
before=shutil.disk_usage('/').free
subprocess.run(['docker','stop','--time','20','monitor-dashboard-creation-preview'],check=True,capture_output=True)
subprocess.run(['docker','rm','monitor-dashboard-creation-preview'],check=True,capture_output=True)
pruned=subprocess.check_output(['docker','builder','prune','--force'],text=True,timeout=180)
after=shutil.disk_usage('/').free
value={'at':time.time(),'preview_removed':'monitor-dashboard-creation-preview','preview_had_no_mounts':True,
       'build_cache_prune_summary':pruned.splitlines()[-1:] ,'disk_free_before':before,'disk_free_after':after,
       'disk_free_change':after-before,'retained':'All images/rollback tags, Android volumes, DB, job journals, outboxes, receipts, failed evidence, logins, APKs and Word outputs'}
(out/'server-cleanup.json').write_text(json.dumps(value,ensure_ascii=False,indent=2))
# Make the creation services visible through the existing GEO target, without restarting them.
drop=Path('/etc/systemd/system/geo-monitor.target.d');drop.mkdir(exist_ok=True)
(drop/'creation.conf').write_text('[Unit]\nWants=geo-content-api.service geo-content-worker.service\nAfter=geo-content-api.service geo-content-worker.service\n')
subprocess.run(['systemctl','daemon-reload'],check=True)
print(json.dumps(value,ensure_ascii=False))
