"""Wake the existing read-only recovery after its code fix, without restarting."""
import json
import os
from pathlib import Path
import time

root=Path('/opt/monitor/geo-capture/batches/geo-panel-deepseek-20261016-094039-dc64b7e1')
evidence=Path('/opt/monitor/geo-capture/maintenance/20261016-daily-observations/readback-wake.json')
assert not evidence.exists(),'One-off wake already applied'
health=json.loads((root/'bridge_health.json').read_text())
assert health['status']=='running_recovery' and not health['worker_pid']
path=root/'capture_retry.json';original=path.read_bytes();value=json.loads(original)
assert value['next_at']>time.time()+5
assert 'result["wire_question"] = question' in Path('/opt/monitor/geo-capture/venv/lib/python3.10/site-packages/web_collectors/collector.py').read_text()
stat=path.stat();updated={**value,'next_at':time.time(),'wake_reason':'fixed_original_readback_finalization'}
temp=path.with_suffix('.wake-staged');temp.write_text(json.dumps(updated,indent=2))
os.chown(temp,stat.st_uid,stat.st_gid);temp.chmod(stat.st_mode & 0o777)
assert path.read_bytes()==original
evidence.write_text(json.dumps({'at':time.time(),'before':value,'after':updated,
                                'collector_restarted':False,'tasks_reset':False},indent=2))
temp.replace(path)
print(json.dumps({'wake':True,'tasks_reset':False,'collector_restarted':False}))
