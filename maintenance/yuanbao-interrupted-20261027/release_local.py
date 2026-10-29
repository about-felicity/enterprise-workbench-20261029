import json,hashlib
from pathlib import Path
D=Path(__file__).parent;W=D.parents[1]
mapping={'yuanbao-deploy/history_refresh.py':'/home/user/redroid-yuanbao/history_refresh.py','yuanbao-deploy/tests/test_history_refresh.py':'/home/user/redroid-yuanbao/tests/test_history_refresh.py'}
(D/'verification/release.json').write_text(json.dumps({'files':[{'source':s,'server':p,'sha256':hashlib.sha256((W/s).read_bytes()).hexdigest()} for s,p in mapping.items()]},indent=2))
