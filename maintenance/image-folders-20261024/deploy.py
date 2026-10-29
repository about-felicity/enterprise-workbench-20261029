import hashlib,json,os,shutil,time
from pathlib import Path
D=Path('/tmp/image-folders-20261024');B=Path('/opt/monitor/geo-content/maintenance/image-folders-20261024');L=Path('/opt/monitor/geo-content/creation')
assert json.loads((D/'qa.json').read_text())['success']
baseline={'panel.html':'b06277ec8d2a0595ebe718850d3ba1f7346e34558ade5fc215e5289de029a035','library.js':'02e91ed1f29441f659b0b22774ae5cc308f62fca8d5f13c57b592f8d0643d5d3'}
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
