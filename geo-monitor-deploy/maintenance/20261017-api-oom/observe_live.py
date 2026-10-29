import json
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

sys.path.insert(0, '/tmp')
from vps_geo_access import browser_cookie

request = urllib.request.Request('https://1any.top/geo_monitor/api/models/doubao/activity?limit=39',
    headers={'Cookie': 'REDACTED_CONFIGURE_LOCALLY' + browser_cookie()})
with urllib.request.urlopen(request, timeout=45) as response:
    public = json.load(response)
assert public.get('ok') and len(public['events']) <= 39
samples = []
for index in range(12):
    with urllib.request.urlopen('http://127.0.0.1:8765/api/health', timeout=20) as response:
        health = json.load(response)
    samples.append({'time': time.time(), 'memory': health['process_memory'],
                    'response_cache': health['http']['response_cache']})
    if index < 11:
        time.sleep(5)
report = {'public_activity_ok': True, 'public_events': len(public['events']), 'samples': samples}
target = Path('/opt/monitor/geo-capture/maintenance/20261017-api-oom/observation.json')
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(json.dumps(report, ensure_ascii=False, indent=2))
print(json.dumps(report, ensure_ascii=False))
