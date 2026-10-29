import concurrent.futures
import json
import subprocess
import time
import urllib.request
from pathlib import Path

def get(path):
    with urllib.request.urlopen('http://127.0.0.1:8765' + path, timeout=60) as response:
        return json.load(response)

start = time.monotonic()
with concurrent.futures.ThreadPoolExecutor(max_workers=24) as pool:
    results = list(pool.map(lambda _: get('/api/models/doubao/activity?limit=40'), range(48)))
assert all(x.get('ok') and len(x.get('events', [])) <= 40 for x in results)
assert all(x == results[0] for x in results), 'Concurrent cached responses differ'
health = get('/api/health')
state = json.loads(subprocess.check_output(['docker', 'inspect', 'monitor-dashboard-api']))[0]
pid = state['State']['Pid']
proc = {}
for line in Path(f'/proc/{pid}/status').read_text().splitlines():
    if line.startswith(('VmRSS:', 'VmHWM:', 'Threads:')):
        key, value = line.split(':', 1)
        proc[key] = value.strip()
print(json.dumps({'checked_at': time.strftime('%Y-%m-%d %H:%M:%S %Z'),
 'requests': len(results), 'seconds': round(time.monotonic()-start, 2),
 'queue': results[0]['queue'], 'events': len(results[0]['events']),
 'proc': proc, 'restart_count': state['RestartCount'], 'started_at': state['State']['StartedAt'],
 'memory': health.get('memory'), 'http': health.get('http'),
 'health_keys': list(health)}, ensure_ascii=False))
