import json,shutil,subprocess,sys,time
from pathlib import Path
B=Path('/opt/monitor/geo-content');M=Path('/opt/monitor/geo-capture/maintenance/20261021-product-richness');mark=M/'deployed-v3.json'
assert not mark.exists()
for p in (B/'runtime/runs').glob('*/api/active.json'):
 a=json.loads(p.read_text())
 if a.get('state') not in (None,'SUBMITTED'):
  assert p.parent.parent.name=='creation-1792556219-bbc55e13' and a['state']=='AUTHORIZING'
  assert not any((p.parent/'runs'/a['run_id']).rglob('api_state.json'))
subprocess.run(['systemctl','stop','geo-content-worker'],check=True)
try:
 for n in ['api_worker.py','reference_design.py']:
  dst=B/'engine/geo_source_cards'/n;bk=M/'backup-v3'/n;bk.parent.mkdir(exist_ok=True);shutil.copy2(dst,bk);shutil.copy2(M/'stage/engine/geo_source_cards'/n,dst)
 mark.write_text(json.dumps({'at':time.time(),'no_paid_request_active':True,'studio_restarted':False}))
finally:subprocess.run(['systemctl','start','geo-content-worker'],check=True)
subprocess.run(['systemctl','restart','geo-content-api'],check=True)
print('v3 applied; existing quality pause retained for controlled recovery')
