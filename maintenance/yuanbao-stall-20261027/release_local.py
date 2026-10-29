import hashlib,json
from pathlib import Path
W=Path(__file__).resolve().parents[2];D=Path(__file__).parent
mapping={'yuanbao-deploy/android_ui.py':'/home/user/redroid-yuanbao/android_ui.py','yuanbao-deploy/draft_recovery.py':'/home/user/redroid-yuanbao/draft_recovery.py','redroid-deploy/question_only_worker.py':'/home/user/redroid-doubao/geo-batch-code/question_only_worker.py','yuanbao-deploy/tests/test_draft_recovery.py':'/home/user/redroid-yuanbao/tests/test_draft_recovery.py'}
(D/'verification/release.json').write_text(json.dumps({'files':[{'source':s,'server':p,'sha256':hashlib.sha256((W/s).read_bytes()).hexdigest()} for s,p in mapping.items()]},indent=2))
