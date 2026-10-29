import hashlib,json,os,shutil,time
from pathlib import Path
D=Path('/tmp/image-upload-fix-20261024');B=Path('/opt/monitor/geo-content/maintenance/image-upload-fix-20261024');L=Path('/opt/monitor/geo-content/creation')
assert json.loads((D/'qa.json').read_text())['success']
baseline={'panel.html':'498c84863544f66fe2767efe4c8b0cc0f704ce01855cc065cce0bfe754c6f4c8','library.js':'2d161cd111ba4c4720bcf0d739f24d1a4f2d280edab7be02a61bd14b3dc70111'}
for f,h in baseline.items():assert hashlib.sha256((L/f).read_bytes()).hexdigest()==h,f
B.mkdir(parents=True,exist_ok=True);backup=B/'before';backup.mkdir(exist_ok=True)
assert not (B/'release.json').exists()
try:
 for f in baseline:shutil.copy2(L/f,backup/f)
 for f in baseline:
  temp=L/(f+'.installing');shutil.copy2(D/'candidate/creation'/f,temp);os.replace(temp,L/f)
except Exception:
 for f in baseline:
  if (backup/f).exists():shutil.copy2(backup/f,L/f)
 raise
report={'at':time.time(),'files':[{'server':str(L/f),'sha256':hashlib.sha256((L/f).read_bytes()).hexdigest()} for f in baseline],'services_restarted':False}
(B/'release.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
