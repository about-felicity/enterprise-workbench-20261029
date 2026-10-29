import hashlib,json,shutil
from pathlib import Path
D=Path('/opt/monitor/geo-capture/maintenance/20261024-doubao-stall');L=Path('/home/user/redroid-doubao/geo-batch-code')
path=D/'deployed.json';record=json.loads(path.read_text())
for name in ['tests/test_draft_submission_recovery.py','tests/test_send_layout_guard.py']:
 source=D/'candidate'/name;target=L/name;before=hashlib.sha256(target.read_bytes()).hexdigest() if target.exists() else None
 if target.exists():backup=D/'before-deployment'/name;backup.parent.mkdir(exist_ok=True);shutil.copy2(target,backup)
 shutil.copy2(source,target)
 record['files'].append({'server':str(target),'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'previous_sha256':before,'kind':'regression_test'})
path.write_text(json.dumps(record,ensure_ascii=False,indent=2));print('Two tested regression files preserved alongside deployed runtime')
