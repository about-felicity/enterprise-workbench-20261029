import json,sys,hashlib,subprocess
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
pid='plan-7ec5b8a566c34569b4da63f14eed2741';base=Path('/opt/monitor/geo-content/maintenance/eye-http-recovery-20261030');base.mkdir(parents=True,exist_ok=True)
receipts={}
for p in (runtime.BASE/'runs').glob('*/job.json'):
 j=runtime.read(p)
 if j.get('studio_plan_id')==pid and j.get('date')=='2026-10-30':
  for f in (p.parent/'approved').rglob('*'):
   if f.is_file():receipts[str(f)]=hashlib.sha256(f.read_bytes()).hexdigest()
manifest=base/'approved-before.json'
if not manifest.exists():runtime.atomic_json(manifest,receipts)
print('PRESERVED_FILES',len(receipts),'RECEIPTS',sum(p.endswith('/receipt.json') for p in receipts))
b=runtime.balance();print('BALANCE_AVAILABLE',b.get('is_available'))
print('SERVICES',subprocess.check_output(['systemctl','is-active','geo-content-api','geo-content-worker','geo-creation-studio']).decode())
