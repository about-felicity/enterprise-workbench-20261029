"""Resume the unchanged queue after an idle CDP read timed out before send."""
import json
from pathlib import Path
import requests
import time
import uuid

http = requests.Session()
http.trust_env = False
base = 'http://127.0.0.1:8803'
data = http.get(base + '/api/panel', timeout=20).json()
model = next(item for item in data['models'] if item['id'] == 'deepseek')
assert model['current']['batch'] == 'geo-panel-deepseek-20261016-094039-dc64b7e1'
assert model['current']['service_state'] == 'failed'
assert model['current']['needs_review'] == 0 and model['current']['pending_delivery'] == 0
assert model['login_status']['status'] == 'ready' and time.time() - model['login_status']['checked_at'] < 120
assert model['current']['config']['rounds'] == 3 and model['current']['config']['interval'] == 600
key = uuid.uuid4().hex
path = Path('/opt/monitor/geo-capture/maintenance/20261016-daily-start/deepseek-resume-idle-cdp.json')
assert not path.exists(), 'Inspect the existing operation before repeating'
path.write_text(json.dumps({'at': time.time(), 'id': key, 'batch': model['current']['batch'], 'before': model['current']}))
response = http.post(base + '/api/control/deepseek/resume', json={},
                     headers={'Origin': base, 'X-CSRF-Token': data['csrf'], 'X-Action-Id': key}, timeout=30)
response.raise_for_status()
value = json.loads(path.read_text())
value['result'] = response.json()
path.write_text(json.dumps(value, ensure_ascii=False, indent=2))
assert value['result']['ok'], value['result']
print(json.dumps(value['result'], ensure_ascii=False))
