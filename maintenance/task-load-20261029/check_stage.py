import json,hashlib
from pathlib import Path
base=Path('/opt/monitor/geo-content/maintenance/task-load-20261029')
for name in ['validation.json','release.json']:
 p=base/name
 if p.exists():print(name,p.read_text())
for name in ['runtime.py','service.py','panel.html']:
 for prefix in [Path('/opt/monitor/geo-content/creation'),base/'stage/creation']:
  p=prefix/name
  if p.exists():print(str(p),hashlib.sha256(p.read_bytes()).hexdigest())
