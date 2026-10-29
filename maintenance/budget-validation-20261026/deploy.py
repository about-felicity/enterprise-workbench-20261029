import hashlib,json,shutil,os
from pathlib import Path
base=Path('/opt/monitor/geo-content/creation');backup=Path('/opt/monitor/geo-content/maintenance/budget-validation-20261026');(backup/'before').mkdir(parents=True,exist_ok=True)
baseline={'panel.html': '490e2eb923fda955630d932192c19b0ac6281ee42a426bcdc3329d9d098727bb', 'wizard.js': '6c490846b8ea0767afe244895b338a66223dd2ba5983e79cf9d600fa4a05007d'}
for n,h in baseline.items():assert hashlib.sha256((base/n).read_bytes()).hexdigest()==h,n
for n in baseline:
 shutil.copy2(base/n,backup/'before'/n);p=base/(n+'.budget-tmp');shutil.copy2(Path('/tmp/budget-validation-20261026')/n,p);os.replace(p,base/n)
result={'files':[{'server':str(base/n),'sha256':hashlib.sha256((base/n).read_bytes()).hexdigest()} for n in baseline],'budgets_changed':False}
(backup/'release.json').write_text(json.dumps(result));print(json.dumps(result))
