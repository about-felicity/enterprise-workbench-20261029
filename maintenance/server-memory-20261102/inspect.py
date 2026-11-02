import subprocess,json,shutil
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
print('TIME',datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),flush=True)
for label,cmd in [('MEMORY',['free','-b']),('UPTIME',['uptime']),('VMSTAT',['vmstat','1','3']),('PROCESSES',['ps','-eo','pid,comm,rss,%mem,%cpu','--sort=-rss']),('CONTAINERS',['docker','stats','--no-stream','--format','{{.Name}} {{.MemUsage}} {{.MemPerc}} {{.CPUPerc}}'])]:
 r=subprocess.run(cmd,text=True,capture_output=True,timeout=35);print(label,r.stdout[:6000],r.stderr[:200],flush=True)
print('PROC',Path('/proc/meminfo').read_text(),flush=True)
for d in ['/var/log/sysstat','/var/log/sa','/var/lib/prometheus','/opt/monitor/observations','/opt/monitor/geo-content/observations']:
 p=Path(d)
 print('HISTORY_DIR',d,[(x.name,x.stat().st_size) for x in list(p.iterdir())[:30]] if p.exists() else 'absent',flush=True)
print('MONITOR_TOOLS',json.dumps({x:shutil.which(x) for x in ['sar','atop','prometheus','nvidia-smi']}),flush=True)
r=subprocess.run(['journalctl','-k','--since','7 days ago','--no-pager','-g','Out of memory|oom-kill|Killed process'],text=True,capture_output=True,timeout=30);print('OOM_LAST7D',r.stdout[-5000:],flush=True)
