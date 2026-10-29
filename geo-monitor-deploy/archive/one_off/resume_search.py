
# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import json
from pathlib import Path
import subprocess

base = Path('/opt/monitor/geo-capture')
for model in ('wenxin_card', 'baidu_ai'):
    config = json.loads((base / 'config' / (model + '.json')).read_text())
    root = base / 'batches' / config['batch']
    health = json.loads((root / 'bridge_health.json').read_text())
    assert health['status'] == 'paused' and not health['tasks'].get('capturing')
    assert not health['tasks'].get('needs_attention') and health['errors'] == []
    (root / 'pause.json').unlink()
    service = 'geo-capture-' + model.replace('_', '-') + '.service'
    subprocess.run(['systemctl', 'start', service], check=True)
print('Resumed original search batches; no queue states reset')
