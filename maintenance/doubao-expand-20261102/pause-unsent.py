import subprocess,json
from pathlib import Path
for n in (3,4):
 p=Path(f'/home/user/redroid-doubao/batches/geo-expand-doubao{n}-20261102-smoke/bridge_health.json');h=json.loads(p.read_text());print(n,h)
 if h.get('captured')==0 and h.get('tasks')=={'pending':1}: subprocess.run(['systemctl','stop',f'geo-expand-smoke{n}-20261102'],check=True,timeout=45);print('STOPPED_UNSENT',n)
print(Path('/proc/meminfo').read_text().splitlines()[:5])
