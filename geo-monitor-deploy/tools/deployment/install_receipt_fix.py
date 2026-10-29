
# Stable runtime imports after tool/test classification.
import sys as _geo_sys
from pathlib import Path as _GeoPath
_GEO_TOOL_ROOT = _GeoPath(__file__).resolve().parents[2]
_geo_sys.path.insert(0, str(_GEO_TOOL_ROOT))
from pathlib import Path
import shutil
import subprocess
import zipfile

base = Path('/opt/monitor/geo-capture')
package = Path('/home/user/redroid-doubao/geo-monitor-receipt-fix')
with zipfile.ZipFile('/home/user/redroid-doubao/geo-monitor-receipt-fix.zip') as archive:
    assert archive.testzip() is None
    archive.extractall(package)
for name in ('capture_bridge.py', 'fleet_status.py'):
    target = base / name
    backup = base / 'backups/1792026782' / (name + '.before-receipt-fix')
    if not backup.exists():
        shutil.copy2(target, backup)
    temporary = target.with_suffix('.install')
    shutil.copy2(package / name, temporary)
    temporary.chmod(0o644)
    temporary.replace(target)
target = next((base / 'venv/lib').glob('python*/site-packages/geo_source_cards/cli.py'))
temporary = target.with_suffix('.install')
shutil.copy2(package / 'cli.py', temporary)
temporary.chmod(0o644)
temporary.replace(target)
subprocess.run(['systemctl', 'restart', 'geo-monitor-status.service'], check=True)
for model in ('wenxin-card', 'baidu-ai'):
    subprocess.run(['systemctl', 'start', 'geo-capture-' + model + '.service'], check=True)
print('Receipt relay installed; existing captures retained; pause markers still in place')
