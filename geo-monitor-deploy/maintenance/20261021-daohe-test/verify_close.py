import sys,json,hashlib,subprocess
from pathlib import Path
from datetime import datetime
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime,observation as o
M=Path('/opt/monitor/geo-capture/maintenance/20261021-daohe-test');lease=runtime.read(M/'budget-lease.json');baseline=o.read(o.OUTPUT/'baseline.json');now=datetime.now(o.ZONE);current=o.collect(now)
assert lease['status']=='restored' and current['daily_budget_cny']==10
assert hashlib.sha256((runtime.SHARED/'control.json').read_bytes()).hexdigest()==lease['control_sha256']
assert set(current['unknown_request_ids'])==set(baseline['unknown_request_ids'])
assert all(current['protected_controls'].get(p)==h for p,h in baseline['protected_controls'].items())
original_controls=runtime.read(Path('/opt/monitor/geo-capture/maintenance/20261021-all-logic/controls-before.json'))
assert len(original_controls)==11
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in original_controls.items())
assert current['source_fingerprint']==baseline['source_fingerprint']
report=runtime.read(M/'test-report.json');assert report['reserved']==0 and all(j['pending']==0 for j in report['jobs'])
assert all(j['control']['paused'] for j in report['jobs'])
timer=subprocess.run(['systemctl','is-active','geo-daohe-budget-restore-20261021.timer'],capture_output=True,text=True).stdout.strip();assert timer=='inactive'
for j in report['jobs']:
 root=runtime.job_root(j['id'])
 for p in (root/'api/runs').rglob('api_state.json'):assert runtime.read(p).get('state') not in {'REQUESTING','REQUEST_UNKNOWN'}
assessment=o.evaluate(current,baseline,now)
value={'at':now.isoformat(),'daily_cap_restored':10,'original_shared_control_unchanged':True,'original_control_hash_count':len(original_controls),'original_control_hashes_unchanged':True,'protected_control_count':len(baseline['protected_controls']),'all_protected_controls_unchanged':True,'original_unknown_ids':current['unknown_request_ids'],'new_unknown_requests':0,'trial_outstanding_reserve':0,'timer_state':timer,'all_trial_jobs_paused_with_no_pending':True,'source_fingerprint_matches':True,'ledger':current['ledger'],'observation':assessment,'budget_note':'Temporary cap16 authorized for this manual trial; restored10 for subsequent work. Today committed amount includes this trial and may exceed restored normal cap. Preserve this signal; do not reset ledger or claim unattended pass.'}
runtime.atomic_json(M/'closing-verification.json',value)
o.main();print(json.dumps(value,ensure_ascii=False))
