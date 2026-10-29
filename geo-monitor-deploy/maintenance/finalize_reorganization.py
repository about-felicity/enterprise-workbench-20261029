"""Archive only the explicit staging files created during this maintenance run."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

STATE = Path('/opt/monitor/geo-capture/maintenance/20261015-reorganize')
HOME = Path('/home/user/redroid-doubao')
EXPORT = HOME / 'reorganization-20261015'
names = [
    'service_reorganization.py', 'service_reorganization_finish.py',
    'capture_bridge_exit_order_20261015.py',
    'verify_reorganization.py', 'verify_reorganization_final.py',
    'verify_reorganization_outcomes.py',
    'check_vps_geo_reorganization.py', 'check_vps_geo_reorganization_fixed.py',
    'validation-tests-reorganize.zip',
]

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    for unit in ['geo-project-restart-20261015.service',
                 'geo-project-restart-finish-20261015.service']:
        active = subprocess.run(['systemctl', 'is-active', unit],
                                capture_output=True, text=True).stdout.strip()
        assert active not in {'active', 'activating', 'deactivating'}, (unit, active)
    archive = STATE / 'tools' / 'staging-archive'
    archive.mkdir(parents=True, exist_ok=True)
    manifest = []
    for name in names:
        source = HOME / name
        assert source.parent.resolve() == HOME.resolve()
        if not source.exists():
            continue
        assert source.is_file() and not source.is_symlink()
        target = archive / name
        digest = sha(source)
        if target.exists():
            assert sha(target) == digest, name
        else:
            shutil.copy2(source, target)
        assert sha(target) == digest
        source.unlink()
        manifest.append({'source': str(source), 'archive': str(target), 'sha256': digest})
    for name in ['restart_geo_vps_services_20261015.py',
                 'retire_geo_superseded_units_20261015.py']:
        source = Path('/tmp') / name
        if not source.exists():
            continue
        assert source.is_file() and not source.is_symlink()
        target = archive / name
        digest = sha(source)
        if target.exists():
            assert sha(target) == digest
        else:
            shutil.copy2(source, target)
        assert sha(target) == digest
        source.unlink()
        manifest.append({'source': str(source), 'archive': str(target), 'sha256': digest})
    data = json.dumps({'archived_staging_files': manifest,
                       'production_modules_and_queues_untouched': True}, indent=2)
    target = STATE / 'staging-archive.json'
    if manifest or not target.exists():
        target.write_text(data, encoding='utf8')
    shutil.copy2(target, EXPORT / target.name)
    (EXPORT / target.name).chmod(0o644)
    print(json.dumps({'archived': len(manifest), 'production_untouched': True}))

if __name__ == '__main__':
    main()
