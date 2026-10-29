import json,shutil,sqlite3,subprocess
from pathlib import Path
R=Path('/opt/monitor/geo-content/maintenance/20261016-creation-filters');B=Path('/opt/monitor/geo-content')
assert json.loads((R/'qa-preview.json').read_text())['passed']
assert not (R/'release.json').exists(),'Do not repeat release blindly'
def jobs():
 with sqlite3.connect('file:/opt/monitor/geo-capture/panel/control.sqlite?mode=ro',uri=True) as db:names=[r[0] for r in db.execute('select service from jobs where batch in (select current_batch from settings)')]
 names+=['geo-content-worker.service','geo-creation-materials.service']
 return {n:subprocess.check_output(['systemctl','show',n,'--property=MainPID,ActiveEnterTimestampMonotonic'],text=True) for n in names}
before=jobs();(R/'backup').mkdir()
for name in ['runtime.py','service.py','panel.html','test_materials.py']:
 shutil.copy2(B/'creation'/name,R/'backup'/name);shutil.copy2(R/'stage/creation'/name,B/'creation'/name)
subprocess.run(['systemctl','restart','geo-content-api.service'],check=True)
after=jobs();result={'published':True,'collectors_and_workers_unchanged':before==after,'before':before,'after':after}
(R/'release.json').write_text(json.dumps(result,indent=2))
assert result['collectors_and_workers_unchanged']
print(json.dumps({'published':True,'collectors_and_workers_unchanged':True}))
