import subprocess
from pathlib import Path
exec(Path('/tmp/nonexistent').read_text()) if False else None
for n in (3,4):
 print('HEALTH',n,Path(f'/home/user/redroid-doubao/batches/geo-expand-doubao{n}-20261102-smoke/bridge_health.json').read_text())
 print(subprocess.run(['journalctl','-u',f'geo-expand-smoke{n}-20261102','-n','5','--no-pager'],capture_output=True,text=True).stdout)
 subprocess.run(['docker','exec',f'doubao-hpe14-account{n}','uiautomator','dump',f'/data/local/tmp/expand.xml'],capture_output=True,timeout=25)
 print('XML',n,subprocess.run(['docker','exec',f'doubao-hpe14-account{n}','cat','/data/local/tmp/expand.xml'],capture_output=True,text=True).stdout)
