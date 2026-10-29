"""Record unchanged pre-test content/tunnel unit identity for the final report."""
import json
from pathlib import Path
import subprocess
import time

BASE=Path('/opt/monitor/geo-capture')
root=BASE/'soak/all-channel-soak2h-1792056244'
old=json.loads((BASE/'yuanbao_control_frontend.json').read_text())
units=['geo-editorial-scheduler.service','geo-editorial-api-worker.service',
       'geo-editorial-coordinator.service','geo-editorial-session-watch.service','monitor-vps2-tunnel.service']


def parse(text):
    result={}
    for block in text.strip().split('\n\n'):
        fields=dict(line.split('=',1) for line in block.splitlines() if '=' in line)
        if 'Id' in fields:result[fields['Id']]=fields
    return result


current=subprocess.check_output(['systemctl','show',*units,'-p','Id','-p','MainPID','-p','ExecMainStartTimestamp'],text=True).strip()
before=parse(old['services_before']);after=parse(current)
assert all(before[unit]==after[unit] for unit in units)
value={'recorded_at':time.time(),'pre_test_baseline_at':old['created_at'],
       'pre_test_identity_matches':True,'units':units,'services_before':current}
(root/'continuity_baseline.json').write_text(json.dumps(value,indent=2))
print(json.dumps({k:v for k,v in value.items() if k!='services_before'}))
