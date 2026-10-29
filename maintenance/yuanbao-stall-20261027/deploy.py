import hashlib,json,os,shutil,sqlite3,subprocess,time
from pathlib import Path
D=Path('/opt/monitor/geo-capture/maintenance/20261027-yuanbao-stall');D.mkdir(parents=True,exist_ok=True)
R=Path('/home/user/redroid-yuanbao/batches/geo-panel-yuanbao-20261027-090005-e7c7269a');unit='geo-native@'+R.name+'.service'
files=[('android_ui.py','/home/user/redroid-yuanbao/android_ui.py','0e6bbcd15a23d3eecd01711caf157eb422ed6be2605765dd0da2de58302cdf72'),('draft_recovery.py','/home/user/redroid-yuanbao/draft_recovery.py',None),('question_only_worker.py','/home/user/redroid-doubao/geo-batch-code/question_only_worker.py','e13adc206b90c21c5fc904eda2c6fee5cf441233eb3387b12bccbd2d25131f8f')]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
for name,path,expected in files:
 p=Path(path);assert (sha(p) if p.exists() else None)==expected,path
assert not (R/'maintenance_pause.json').exists()
subprocess.run(['systemctl','stop',unit],check=True,timeout=45)
try:
 with sqlite3.connect(R/'tasks.sqlite') as db:
  with sqlite3.connect(D/'before-tasks.sqlite') as out:db.backup(out)
 for name,path,expected in files:
  p=Path(path)
  if p.exists():shutil.copy2(p,D/(name+'.before'))
  temporary=p.with_suffix('.repair27.tmp');shutil.copy2(Path('/tmp/yuanbao27-stage')/name,temporary);temporary.chmod(0o644);os.replace(temporary,p)
finally:subprocess.run(['systemctl','start',unit],check=True)
print(json.dumps({'files':[{ 'path':p,'sha256':sha(Path(p))} for _,p,_ in files],'time':time.time(),'queue_reset':False}))
