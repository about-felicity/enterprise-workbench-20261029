import json,hashlib,subprocess,tarfile
from pathlib import Path
work=Path('/opt/monitor/geo-capture/maintenance/wenxin-20261031');stage=work/'stage';stage.mkdir(parents=True,exist_ok=True)
with tarfile.open('/tmp/wenxin-20261031.tar.gz') as tar:
 assert all(not p.name.startswith('/') and '..' not in Path(p.name).parts for p in tar.getmembers());tar.extractall(stage)
manifest=json.loads((stage/'manifest.json').read_text())
assert hashlib.sha256(Path('/opt/monitor/geo-capture/capture_bridge.py').read_bytes()).hexdigest()==manifest['before']
cmd=['/opt/monitor/geo-capture/venv/bin/python','-B','-m','unittest','discover','-s',str(stage/'tests'),'-p','test_*.py']
import os
env={**os.environ,'PYTHONPATH':str(stage)+':/opt/monitor/geo-capture'}
subprocess.run(cmd,cwd=stage,env=env,check=True,timeout=60)
print('WATCHDOG_TESTS_PASSED')
