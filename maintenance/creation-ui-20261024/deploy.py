"""Install only the tested creation UI/control changes at a safe idle boundary."""
import contextlib,hashlib,json,os,signal,shutil,subprocess,sys,time,urllib.request
from pathlib import Path
D=Path('/tmp/geo-creation-ui-20261024');C=D/'candidate';L=Path('/opt/monitor/geo-content')
sys.path[:0]=[str(C),str(C/'engine')]
from geo_source_cards.runtime import process_lock,atomic_json
def read(p):return json.loads(p.read_text()) if p.exists() else {}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def cmd(*args):return subprocess.check_output(args,text=True,stderr=subprocess.STDOUT,timeout=40).strip()
assert read(D/'ui-result.json')['success'];assert read(D/'tests.json')['success']
baseline=read(D/'baseline.json');files=list(baseline)
for n in files:assert sha(L/'creation'/n)==baseline[n],n+' changed since inspection'
B=L/'maintenance/creation-ui-20261024';B.mkdir(parents=True,exist_ok=True)
assert not (B/'deployed.json').exists()
worker=int(cmd('systemctl','show','geo-content-worker','-p','MainPID','--value'));frozen=False;stopped=False;installed=[]
supervisors=[]
services=['geo-content-api','geo-creation-studio','geo-content-worker']
with contextlib.ExitStack() as locks:
 for p in [L/'runtime/actions.lock']:
  locks.enter_context(process_lock(p,blocking=False))
 try:
  # Freeze only idle creation supervisors. A collector is never interrupted;
  # unrelated GEO browser services do not need to stop for this release.
  group=Path('/sys/fs/cgroup')/cmd('systemctl','show','geo-creation-studio','-p','ControlGroup','--value').lstrip('/')/'cgroup.procs'
  for raw in group.read_text().split():
   pid=int(raw);command=Path('/proc')/raw/'cmdline'
   try:args=command.read_bytes().split(b'\0')
   except FileNotFoundError:continue
   if b'creation.studio' not in args and b'creation.materials' not in args:raise RuntimeError('Request active; retry at idle boundary (creation collector)')
   os.kill(pid,signal.SIGSTOP);supervisors.append(pid)
  if set(map(int,group.read_text().split()))-set(supervisors):raise RuntimeError('Request active; retry at idle boundary (new child)')
  if worker:os.kill(worker,signal.SIGSTOP);frozen=True
  active=[p for p in (L/'runtime').glob('runs/*/api/runs/**/api_state.json') if read(p).get('state')=='REQUESTING']
  if active:raise RuntimeError('Request active; retry at idle boundary')
  for n in files:
   target=B/'before'/n;target.parent.mkdir(exist_ok=True);shutil.copy2(L/'creation'/n,target)
  stopped=True
  for service in services:cmd('systemctl','kill','--kill-who=all','--signal=SIGTERM',service)
  if frozen:os.kill(worker,signal.SIGCONT);frozen=False
  for pid in supervisors:
   try:os.kill(pid,signal.SIGCONT)
   except ProcessLookupError:pass
  supervisors=[]
  cmd('systemctl','stop',*services)
  for n in files:
   target=L/'creation'/n;tmp=target.with_suffix(target.suffix+'.installing');shutil.copy2(C/'creation'/n,tmp);os.replace(tmp,target);installed.append(n)
 except Exception:
  for n in installed:shutil.copy2(B/'before'/n,L/'creation'/n)
  raise
 finally:
  if frozen:os.kill(worker,signal.SIGCONT)
  for pid in supervisors:
   try:os.kill(pid,signal.SIGCONT)
   except ProcessLookupError:pass
  if stopped:cmd('systemctl','start',*services)
result={'at':time.time(),'files':[{'server':str(L/'creation'/n),'sha256':sha(L/'creation'/n),'previous_sha256':baseline[n]} for n in files],
 'tests':66,'ui':read(D/'ui-result.json'),'services':{s:cmd('systemctl','is-active',s) for s in services}}
atomic_json(B/'deployed.json',result);atomic_json(D/'deployed.json',result);print(json.dumps(result,ensure_ascii=False))
