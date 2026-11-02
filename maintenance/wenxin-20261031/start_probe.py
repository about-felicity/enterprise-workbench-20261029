import json,shutil,subprocess
from pathlib import Path
base=Path('/opt/monitor/geo-capture');work=base/'maintenance/wenxin-20261031'
subprocess.run(['systemctl','stop','geo-wenxin-repair-proof-20261031.service'],capture_output=True,timeout=30)
runtime=base/'batches/geo-panel-wenxin-card-20261030-112402-2047183d/collector'
assert runtime.is_dir()
unit='geo-wenxin-session-proof-20261031'
cmd=['systemd-run','--unit',unit,'--uid=user','--property=RuntimeMaxSec=180','--property=KillMode=control-group','--working-directory='+str(base),
     '/usr/bin/flock','-x','-w','90',str(base/'search_browser.lock'),str(base/'venv/bin/python'),'-u','-B',str(base/'wenxin_readiness_probe.py'),
     '--runtime',str(runtime),'--question','推荐一款染发剂']
subprocess.run(cmd,check=True,capture_output=True,text=True,timeout=15)
print('READINESS_PROBE_STARTED',unit)
