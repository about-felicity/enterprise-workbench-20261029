import json,subprocess,time
from pathlib import Path
B=Path(__file__).resolve().parent
s=json.loads((B/'acceptance-status.json').read_text());state=json.loads((B/'state.json').read_text())
assert s['phase']=='capturing' and not state.get('job_id'),'Cannot restart this pre-writing maintenance helper after handoff'
subprocess.run(['systemctl','stop','geo-brow-v2-acceptance-20261024'],check=True)
(B/'driver-maintenance.json').write_text(json.dumps({'at':time.time(),'reason':'Read final day status when worker becomes idle','phase':'capturing','paid_requests_at_restart':0,'capture_services_restarted':False}))
subprocess.run(['systemd-run','--unit=geo-brow-v2-acceptance-20261024','--collect','--property=UMask=0077','/home/user/geo-editorial/venv/bin/python','-u',str(B/'run_acceptance.py')],check=True)
