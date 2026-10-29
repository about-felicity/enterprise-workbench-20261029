"""Install only the explicitly reviewed new observation modules and timer."""
from pathlib import Path
import shutil
import subprocess
import zipfile

CONTENT = Path('/opt/monitor/geo-content')
MAPPING = {
    'observation.py': CONTENT / 'creation/observation.py',
    'test_observation.py': CONTENT / 'creation/test_observation.py',
    'geo-project-observe.service': Path('/etc/systemd/system/geo-project-observe.service'),
    'geo-project-observe.timer': Path('/etc/systemd/system/geo-project-observe.timer'),
}
with zipfile.ZipFile('/tmp/geo-observation-support.zip') as z:
    assert set(z.namelist()) == set(MAPPING)
    backup = CONTENT / 'observations/install-backup-20261021'
    backup.mkdir(parents=True, exist_ok=True)
    for name, target in MAPPING.items():
        if target.exists():
            saved = backup / name
            if not saved.exists():
                shutil.copy2(target, saved)
        target.write_bytes(z.read(name))
        target.chmod(0o644)
subprocess.run(['/usr/bin/systemd-analyze', 'verify', '/etc/systemd/system/geo-project-observe.service', '/etc/systemd/system/geo-project-observe.timer'], check=True)
subprocess.run(['/home/user/geo-editorial/venv/bin/python', '-B', '-m', 'unittest', 'creation.test_observation', 'creation.test_repair_followup', 'creation.test_studio', 'creation.test_workflow', 'creation.test_worker_recovery', 'creation.test_download_service'], cwd=CONTENT, check=True)
subprocess.run(['/usr/bin/systemctl', 'daemon-reload'], check=True)
subprocess.run(['/usr/bin/systemctl', 'enable', '--now', 'geo-project-observe.timer'], check=True)
subprocess.run(['/usr/bin/systemctl', 'start', 'geo-project-observe.service'], check=True)
subprocess.run(['/usr/bin/systemctl', 'show', 'geo-project-observe.timer', '--property=ActiveState,NextElapseUSecRealtime'], check=True)
