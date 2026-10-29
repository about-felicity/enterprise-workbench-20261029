import json,time,hashlib,subprocess
from pathlib import Path
root=Path('/opt/monitor/geo-content');read=lambda p:json.loads(p.read_text()) if p.exists() else {}
print('NOW',time.time())
print('HEALTH',json.dumps(read(root/'studio/health.json')))
for p in (root/'studio/days/2026-10-29').glob('*.supplement-state'):
 if p.suffix=='.supplement-state':print('SUPPLEMENT',str(p),p.stat().st_mtime,json.dumps(read(p),ensure_ascii=False))
for p in (root/'runtime/runs').glob('creation-*/job.json'):
 j=read(p)
 if j.get('date')!='2026-10-29' or j.get('preparation')=='ready':continue
 print('PENDING',p.parent.name,json.dumps({k:j.get(k) for k in ['question','preparation','material_shortfall','supplement_attempt']},ensure_ascii=False))
print('HASH',hashlib.sha256((root/'creation/supplement.py').read_bytes()).hexdigest())
print('WARNINGS',subprocess.run(['journalctl','-u','geo-content-api','-u','geo-content-worker','-u','geo-creation-studio','--since','2026-10-28 16:00:00 UTC','-p','warning','-n','30','--no-pager'],capture_output=True,text=True).stdout)
print('STUDIO',subprocess.run(['systemctl','show','geo-creation-studio','-p','ExecStart'],capture_output=True,text=True).stdout)
