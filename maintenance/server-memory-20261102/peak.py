import subprocess,json
from pathlib import Path
print('CGROUP_FS',subprocess.check_output(['stat','-fc','%T','/sys/fs/cgroup'],text=True).strip())
for n in ['memory.peak','memory.current','memory.swap.current','memory.events']:
 p=Path('/sys/fs/cgroup')/n
 if p.exists():print('HOST_CGROUP',n,p.read_text().strip())
ids=subprocess.check_output(['docker','ps','-q'],text=True).split()
for cid in ids:
 r=json.loads(subprocess.check_output(['docker','inspect',cid],text=True))[0];pid=r['State']['Pid']
 cg=Path(f'/proc/{pid}/cgroup').read_text();path=next((x.split(':',2)[2] for x in cg.splitlines() if x.startswith('0::')),None)
 if path:
  base=Path('/sys/fs/cgroup')/path.lstrip('/');out={'name':r['Name'],'started':r['State']['StartedAt']}
  for key in ['memory.current','memory.peak','memory.swap.current','memory.events']:
   p=base/key
   if p.exists():out[key]=p.read_text().strip()
  print('CONTAINER_PEAK',json.dumps(out))
for pid in [61550,50088,30297]:
 p=Path(f'/proc/{pid}')
 if p.exists():
  args=(p/'cmdline').read_bytes().replace(b'\0',b' ').decode(errors='replace')
  print('TOP_PROCESS',pid,args[:220],[(x.split(':')[0],x.split(':')[1].strip()) for x in (p/'status').read_text().splitlines() if x.startswith(('VmRSS:','VmHWM:','VmSwap:'))])
