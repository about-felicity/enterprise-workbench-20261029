import sys,json,hashlib,shutil,os,time
from pathlib import Path
D=Path('/opt/monitor/maintenance/creation-formats-20261028')
target=Path('/opt/monitor/geo-content/creation/materials.py');candidate=Path('/tmp/formats28-materials.py')
assert hashlib.sha256(target.read_bytes()).hexdigest()=='94d62228c9cdd1ec234c314b48bd60142efafe3c8f4e0e7ffe5f4c04123e1d6d'
compile(candidate.read_text(),str(target),'exec');shutil.copy2(target,D/'materials.py.before')
tmp=target.with_suffix('.new');shutil.copyfile(candidate,tmp);os.chmod(tmp,target.stat().st_mode);os.chown(tmp,target.stat().st_uid,target.stat().st_gid);os.replace(tmp,target)
r=json.loads((D/'release.json').read_text());r['files'].append({'source':'geo-monitor-deploy/creation/materials.py','server':str(target),'sha256':hashlib.sha256(target.read_bytes()).hexdigest()});(D/'release.json').write_text(json.dumps(r,indent=2))
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
from geo_source_cards.runtime import process_lock,atomic_json
for jid in ['creation-1793009315-b5caef1c','creation-1793067135-0fd9dc7e','creation-1793091688-ad8c9ac1']:
 root=runtime.BASE/'runs'/jid
 with process_lock(root/'api/worker.lock',blocking=False):
  j=runtime.read(root/'job.json');day=root/'days'/j['date']/'day.json'
  assert j['preparation']=='insufficient' and runtime.read(day)['status']=='blocked_insufficient_sources'
  assert not list((root/'queue').glob('*/ticket.json')) and not list((root/'approved').glob('**/receipt.json'))
  b=D/(jid+'-materials');b.mkdir(exist_ok=False)
  shutil.copy2(root/'job.json',b/'job.json');shutil.copy2(day,b/'day.json')
  day.rename(b/'blocked-day.json')
  atomic_json(root/'job.json',{**j,'preparation':'pending','material_shortfall':''})
  runtime.resume(root,check_balance=False)
 print('RESUMED_MATERIALS',jid,flush=True)
