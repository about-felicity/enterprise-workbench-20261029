
# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
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
