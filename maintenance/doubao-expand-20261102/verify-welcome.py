import subprocess,json
from pathlib import Path
for n in (3,4):
 r=Path(f'/home/user/redroid-doubao/batches/geo-expand-doubao{n}-20261102-smoke');print(n,(r/'bridge_health.json').read_text());print(subprocess.run(['journalctl','-u',f'geo-expand-welcome{n}-20261102','-n','4','--no-pager'],capture_output=True,text=True).stdout)
