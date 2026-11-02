import json,subprocess
from pathlib import Path
for d in ['/opt/monitor/deepseek_monitor','/opt/monitor/runtime','/opt/monitor/geo-capture/daily','/opt/monitor/geo-capture']:
 p=Path(d);print('DIR',d,[x.name for x in p.iterdir() if x.is_dir() or 'deepseek' in x.name][:50])
print('CONTAINERS',subprocess.run(['docker','ps','--format','{{.Names}}'],capture_output=True,text=True).stdout)
