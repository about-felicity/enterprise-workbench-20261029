import subprocess,json
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
print('TIME',datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),flush=True)
print('MEM',Path('/proc/meminfo').read_text(),flush=True)
print('CPU',subprocess.check_output(['nproc'],text=True).strip())
for cid in subprocess.check_output(['docker','ps','-aq'],text=True).split():
 r=json.loads(subprocess.check_output(['docker','inspect',cid],text=True))[0];h=r['HostConfig'];c=r['Config'];pid=r['State'].get('Pid');cg=''
 if pid:
  p=Path(f'/proc/{pid}/cgroup')
  if p.exists():cg=next((x.split(':',2)[2] for x in p.read_text().splitlines() if x.startswith('0::')),'')
 mem={}
 if cg:
  base=Path('/sys/fs/cgroup')/cg.lstrip('/')
  for key in ['memory.current','memory.peak','memory.swap.current','memory.events','memory.stat']:
   p=base/key
   if p.exists():mem[key]=p.read_text().strip()
 # Only allowlisted resource options; never print env or arbitrary commands.
 options=[x for x in (c.get('Cmd') or []) if str(x).startswith(('androidboot.redroid_','androidboot.hardware','ro.'))]
 print('CONTAINER',json.dumps({'name':r['Name'],'image':c['Image'],'running':r['State']['Running'],'memory_limit':h['Memory'],'swap_limit':h['MemorySwap'],'cpu_quota':h['CpuQuota'],'cpuset':h['CpusetCpus'],'shm':h['ShmSize'],'restart':h['RestartPolicy'],'resource_options':options,'memory':mem}),flush=True)
print('SYSCTL',subprocess.run(['sysctl','vm.swappiness','vm.vfs_cache_pressure','vm.overcommit_memory'],capture_output=True,text=True).stdout,flush=True)
print('SERVICES',subprocess.run(['systemctl','list-units','--type=service','--state=running','--no-pager','--no-legend'],capture_output=True,text=True).stdout,flush=True)
print('PS',subprocess.check_output(['ps','-eo','pid,ppid,comm,rss,%cpu','--sort=-rss'],text=True)[:6500],flush=True)
for root in ['/opt/monitor/runtime','/home/user/redroid-doubao','/home/user/redroid-yuanbao']:
 p=Path(root);print('STATE_FILES',root,[x.name for x in p.iterdir() if x.name.endswith(('.json','.service','.sh'))][:45] if p.exists() else [])
