import json
from pathlib import Path
base=Path('/opt/monitor/geo-content/runtime/runs')
for job,run in [('creation-1793252901-ec370f70','b2df0b5b4303459f3f7e5da0'),('creation-1793252898-0afc24a2','bf69eab7ef2bef60bad0ca83'),('creation-1793252896-76293dac','1641469eb6fa9b3d5c903b88'),('creation-1793252890-7d974528','8eb1a2d6a91803a0def26bcc')]:
 root=base/job
 print('JOB',job)
 for p in (root/'api/runs'/run).rglob('api_state.json'):
  state=json.loads(p.read_text())
  print(json.dumps({'path':str(p),'state':state,'response_exists':(p.parent/'response.json').exists(),'answer_exists':(p.parent/'answer.json').exists(),'mtime':p.stat().st_mtime},ensure_ascii=False))
 for name in ['geo_worker.json','api/active.json']:
  p=root/name
  if p.exists():print(name,p.read_text())
