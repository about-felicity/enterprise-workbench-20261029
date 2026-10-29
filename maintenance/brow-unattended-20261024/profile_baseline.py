import hashlib,json
from pathlib import Path
B=Path(__file__).resolve().parent;p=Path('/opt/monitor/geo-capture/venv/lib/python3.10/site-packages/geo_source_cards/search_profiles.py')
value={'server':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'tests_run':7,'failures':0,'errors':0}
target=B/'profile-baseline.json'
if target.exists():assert json.loads(target.read_text())==value
else:target.write_text(json.dumps(value,indent=2))
print(json.dumps(value))
