"""Install the verified minimal V2 release at an idle request/browser boundary."""
import contextlib,hashlib,json,os,signal,shutil,subprocess,sys,time
from pathlib import Path
B=Path(__file__).resolve().parent;LIVE=Path('/opt/monitor/geo-content')
sys.path[:0]=[str(LIVE/'engine'),str(LIVE)]
from geo_source_cards.runtime import atomic_json,process_lock
def read(p):return json.loads(p.read_text()) if p.exists() else {}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
def command(*args):return subprocess.run(args,check=True,capture_output=True,text=True,timeout=30).stdout.strip()
assert read(B/'release/verification.json').get('success') is True
state=read(B/'acceptance-status.json')
assert state.get('phase')=='finished' and state.get('delivered',0)>=7, 'Real unattended acceptance is not complete'
manifest={v['path']:v for v in read(B/'deployment-diff.json')}
names=read(B/'release-files.json')
files=[(B/'release'/n,LIVE/n,manifest[n]['live_sha256']) for n in names]
collector=Path('/opt/monitor/geo-capture/venv/lib/python3.10/site-packages/geo_source_cards/search_profiles.py')
expected=read(B/'profile-baseline.json')['sha256']
files.append((B/'search_profiles.py',collector,expected))
for source,target,digest in files:
 assert sha(target)==digest, 'Live source changed since validation: '+str(target)
 assert source.is_file()
backup=LIVE/'maintenance'/'brow-v2-20261024';backup.mkdir(parents=True,exist_ok=True)
assert not (backup/'deployed.json').exists(),'Already deployed; do not overwrite the original backup'
for source,target,_ in files:
 if target.exists():
  dest=backup/'before'/target.relative_to('/');dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(target,dest)
services=['geo-content-worker','geo-content-api','geo-creation-studio']
worker=int(command('systemctl','show','geo-content-worker','-p','MainPID','--value'))
stopped=False;frozen=False;installed=[]
with contextlib.ExitStack() as locks:
 for path in (LIVE/'search-pool/browser.lock',Path('/opt/monitor/geo-capture/search_browser.lock'),Path('/opt/monitor/geo-capture/deepseek_account.lock')):
  locks.enter_context(process_lock(path,blocking=False))
 try:
  # Freeze between Python instructions, then inspect durable send intent. If a
  # request is active, immediately continue it and postpone deployment.
  if worker:os.kill(worker,signal.SIGSTOP);frozen=True
  pending=[str(p) for p in (LIVE/'runtime').glob('runs/*/api/runs/**/api_state.json') if read(p).get('state')=='REQUESTING']
  if pending:raise RuntimeError('Paid request active; postpone deployment')
  stopped=True
  for service in services:
   command('systemctl','kill','--kill-who=all','--signal=SIGTERM',service)
  if frozen:os.kill(worker,signal.SIGCONT);frozen=False
  command('systemctl','stop',*services);stopped=True
  for source,target,_ in files:
   target.parent.mkdir(parents=True,exist_ok=True);tmp=target.with_suffix('.py.installing');shutil.copy2(source,tmp);os.replace(tmp,target);installed.append(target)
  defaults=LIVE/'runtime/rewrite_defaults.json'
  if defaults.exists():shutil.copy2(defaults,backup/'rewrite_defaults.before.json')
  atomic_json(defaults,{'skeleton_review':'automatic','authorization':'2026-10-24 user: 文章没啥问题，可以直接用了，把系统完善下，然后用这个测试一下，找七个问题，做到无人值守'})
  atomic_json(backup/'deployed.json',{'at':time.time(),'files':[{'server':str(t),'sha256':sha(t),'previous_sha256':d} for _,t,d in files],
   'regression':read(B/'release/verification.json'),'real_acceptance':state,'ui_changed':False})
 except Exception:
  for target in reversed(installed):
   original=backup/'before'/target.relative_to('/')
   if original.exists():shutil.copy2(original,target)
   else:target.unlink()
  raise
 finally:
  if frozen:os.kill(worker,signal.SIGCONT)
  if stopped:command('systemctl','start',*services)
print(json.dumps(read(backup/'deployed.json'),ensure_ascii=False,indent=2))
