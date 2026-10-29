"""Verify the immutable base, minimal diff and actual offline test evidence."""
import hashlib,json,subprocess
from datetime import datetime,timezone,timedelta
from pathlib import Path
D=Path(__file__).resolve().parent;W=D.parents[1];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_text('utf8'))
protected=read(D/'protected-before.json');assert all((W/p).is_file() and sha(W/p)==h for p,h in protected.items())
prior=read(W/'maintenance/b1-b2-candidate-20261023/protected-before.json');assert all(sha(Path(p))==h for p,h in prior.items())
m=read(D/'manifest.json');assert len(m['files'])==14
for p,v in m['files'].items():
 assert sha(D/'candidate-source'/p)==v['sha256']
 if v['change']!='added':assert sha(D/'baseline-source'/p)==v['baseline_sha256']
assert [p for p,v in m['files'].items() if v['change']=='modified']==['geo_source_cards/repair_router.py']
assert [p for p,v in m['files'].items() if v['change']=='added']==['tests/test_b2_repair_entry.py']
track=lambda s:[line for line in s.splitlines() if not line.startswith('??')]
assert track((D/'git-status-before.txt').read_text('utf8'))==track(subprocess.check_output(['git','status','--porcelain'],cwd=W,text=True,encoding='utf8'))
linux=read(D/'linux-final/linux-results.json');expected={'special':24,'prior':20,'edges':10,'engine':288,'creation':78}
for r in linux['results']:
 assert r['tests']==expected[r['mode']] and r['exit']==0 and not r['errors'] and not r['failures'] and not r['skips']
 assert r['blocked_network_attempts']==r['real_api_calls']==r['balance_calls']==r['external_business_service_calls']==0
assert linux['production_and_ledger_unchanged']
probe=read(D/'linux-final/probe-linux.json')
assert all(v.get('action')=='PATCH' for v in probe['routes']['frozen_v1'].values())
assert all(v.get('rejected') and v.get('status')=='needs_reaudit' for v in probe['routes']['candidate_v2'].values())
assert probe['unchanged_valid_patch']=={'route':'PATCH','prepare':'PATCH'}
assert probe['old_review_bytes_unchanged'] and probe['old_patch_bytes_unchanged'] and probe['new_mock_requests']==0
prod=read(D/'linux-final/production-before.json')
out={'version':m['version'],'at':datetime.now(timezone(timedelta(hours=8))).isoformat(),'candidate_sha_manifest':m['files'],
 'protected_local_files_unchanged':len(protected),'older_protected_files_unchanged':len(prior),
 'frozen_candidate_directory_files_unchanged':sum(p.startswith('maintenance/b1-b2-candidate-20261023/') for p in protected),
 'runtime_files_changed':1,'new_test_files':1,'old_candidate_files_unchanged':12,'tracked_git_status_unchanged':True,
 'linux_tests':420,'linux_failures':0,'linux_errors':0,'linux_skips':0,'test_groups':expected,
 'production_source_and_control_files_checked':len(prod['files']),'ledger_rows':prod['ledger_rows'],
 'production_sources_originals_budget_controls_and_ledger_unchanged':True,'real_api_calls':0,'balance_calls':0,'external_business_service_calls':0,
 'new_agent_count':0,'dependencies_installed':False,'new_billable_tasks':0,'budget_changed':False,'deployed':False,
 'real_article_quality_acceptance':'NOT_PERFORMED; original real sample outcome remains 0/2',
 'validation_scope':'Offline source/version/routing invariants only. Saved real research plus synthetic method paragraphs/Mock judge in probe.',
 'stage_zip_sha256':sha(D/'offline-stage.zip'),'diff_sha256':sha(D/'candidate.diff')}
(D/'verification.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({k:out[k] for k in ('version','at','protected_local_files_unchanged','frozen_candidate_directory_files_unchanged','linux_tests','linux_failures','production_source_and_control_files_checked','ledger_rows','deployed')},ensure_ascii=False))
