import sys,time
sys.path.insert(0,'/home/user/redroid-doubao/geo-batch-code')
from unattended_worker import atomic_json
from pathlib import Path
import json
p=Path('/home/user/redroid-doubao/batches/geo-products-21x5-account2-20261013/bridge_health.json')
d=json.loads(p.read_text())
d.update(time=time.time(),status='blocked_native_send',worker_exit=None,
         detail='Service stopped after two distinct native messages failed to receive server IDs or answers. Original tasks and native IDs retained; no automatic resubmission.')
atomic_json(p,d)
