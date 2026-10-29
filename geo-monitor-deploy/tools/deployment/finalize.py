"""Install the final bridge only after the new search lanes drain safely."""

# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

base = Path('/opt/monitor/geo-capture')
configs = [json.loads((base / 'config' / (model + '.json')).read_text()) for model in ('wenxin_card', 'baidu_ai')]
for config in configs:
    root = base / 'batches' / config['batch']
    health = json.loads((root / 'bridge_health.json').read_text())
    if health['status'] != 'paused' or health.get('worker_pid'):
        raise SystemExit('Waiting for safe boundary: ' + config['model'])
temporary = base / 'capture_bridge.install'
shutil.copy2('/home/user/redroid-doubao/capture_bridge_geo_final.py', temporary)
temporary.chmod(0o644)
temporary.replace(base / 'capture_bridge.py')
for model in ('deepseek', 'wenxin-card', 'baidu-ai'):
    dropin = Path('/etc/systemd/system/geo-capture-' + model + '.service.d/receipt-relay.conf')
    dropin.parent.mkdir(exist_ok=True)
    dropin.write_text('[Unit]\nAfter=geo-monitor-status.service\nWants=geo-monitor-status.service\n')
subprocess.run(['systemctl', 'daemon-reload'], check=True)
manifest = json.loads((base / 'deployment.json').read_text())
manifest['bridge_sha256'] = hashlib.sha256((base / 'capture_bridge.py').read_bytes()).hexdigest()
manifest['receipt_relay'] = 'http://127.0.0.1:8803/api/receipts/{model}/{request_id}'
(base / 'deployment.json').write_text(json.dumps(manifest, indent=2))
for config in configs:
    (base / 'batches' / config['batch'] / 'pause.json').unlink()
    subprocess.run(['systemctl', 'start', 'geo-capture-' + config['model'].replace('_', '-') + '.service'], check=True)
print('Final bridge active; original batches resumed safely')
