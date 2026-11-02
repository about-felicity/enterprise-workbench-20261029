from pathlib import Path
import json,subprocess
b=Path('/opt/monitor/geo-capture');print('FLEET',json.dumps(json.loads((b/'fleet.json').read_text())['collectors'],ensure_ascii=False));print('PLAN', (b/'daily_plan.json').read_text())
for n in [3,4]:
 p=Path(f'/home/user/redroid-doubao/batches/geo-expand-doubao{n}-20261102-smoke/bridge_health.json')
 print('HEALTH',n,p.read_text() if p.exists() else 'absent')
 print('LOG',n,subprocess.run(['journalctl','-u',f'geo-expand-smoke{n}-20261102','-n','10','--no-pager'],capture_output=True,text=True).stdout)
