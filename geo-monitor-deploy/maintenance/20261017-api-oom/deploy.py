import datetime
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

root = Path('/opt/monitor')
backup = root / 'geo-capture/maintenance/20261017-api-oom/before'
backup.mkdir(parents=True, exist_ok=False)
targets = {
    '/tmp/geo_oom_dashboard_1017.py': root / 'doubao_dashboard_server.py',
    '/tmp/geo_oom_doubao_plugin_1017.py': root / 'model_plugins/doubao/plugin.py',
    '/tmp/geo_oom_source_activity_index_1017.py': root / 'monitor_core/source_activity_index.py',
}
# Optimistic check: never overwrite a dashboard changed since inspection.
assert hashlib.sha256((root / 'doubao_dashboard_server.py').read_bytes()).hexdigest() == 'bc7040e7f756877959965916b8c552e9cdf8ea7194f1035b4b468cc3df51b5b7'
for source, target in targets.items():
    compile(Path(source).read_text(), str(target), 'exec')
    if target.exists():
        saved = backup / target.relative_to(root)
        saved.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target, saved)
for source, target in targets.items():
    temporary = target.with_name(target.name + '.oom-stage')
    shutil.copy2(source, temporary)
    temporary.chmod(0o644)
    temporary.replace(target)
subprocess.run(['docker', 'restart', 'monitor-dashboard-api'], check=True, timeout=60)
print(json.dumps({'deployed_at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'files': len(targets)}))
