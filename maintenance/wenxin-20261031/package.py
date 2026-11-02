import hashlib,json,tarfile
from pathlib import Path
root=Path(__file__).resolve().parents[2];here=Path(__file__).parent
files=[('geo-monitor-deploy/capture_bridge.py','capture_bridge.py'),('geo-monitor-deploy/tests/test_web_worker_timeout.py','tests/test_web_worker_timeout.py'),('geo-monitor-deploy/tests/test_capture_bridge.py','tests/test_capture_bridge.py')]
(here/'manifest.json').write_text(json.dumps({'before':hashlib.sha256((here/'before/capture_bridge.py').read_bytes()).hexdigest(),'sha256':hashlib.sha256((root/files[0][0]).read_bytes()).hexdigest()},indent=2),encoding='utf8')
with tarfile.open(here/'release.tar.gz','w:gz') as tar:
 for source,dest in files:tar.add(root/source,arcname=dest)
 tar.add(here/'manifest.json',arcname='manifest.json')
print('Web worker watchdog packaged')
