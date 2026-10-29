"""Verify frozen evidence and summarize failures without calling them passes."""
import hashlib,json,subprocess
from datetime import datetime,timezone,timedelta
from pathlib import Path
import offline_guard
D=Path(__file__).resolve().parent;W=D.parents[1];F=W/'maintenance/b1-b2-candidate-20261023'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_text('utf8'))
protected=read(D/'protected-before.json');changed=[p for p,h in protected.items() if not (W/p).is_file() or sha(W/p)!=h]
assert not changed,changed
older=read(F/'protected-before.json');older_changed=[p for p,h in older.items() if not Path(p).is_file() or sha(Path(p))!=h]
assert not older_changed,older_changed
candidate=read(F/'manifest.json');assert all(sha(F/'candidate-source'/p)==row['sha256'] for p,row in candidate['files'].items())
linux=read(D/'linux/linux-results.json');by={r['mode']:r for r in linux['results']}
for mode,n in [('new',20),('engine',288),('creation',78),('baseline-creation',78)]:
 assert by[mode]['tests']==n and not by[mode]['failures'] and not by[mode]['errors'] and not by[mode]['skips'],mode
assert by['edges']['tests']==10 and len(by['edges']['failures'])==2 and not by['edges']['errors'] and not by['edges']['skips']
assert all('non_arbitrated_repair_must_reject_stale_' in name for name in by['edges']['failures'])
assert linux['production_ledger_budget_originals_unchanged']
assert all(r['blocked_network_attempts']==0 and r['external_api_calls']==0 for r in by.values())
tracked=lambda s:[line for line in s.splitlines() if not line.startswith('??')]
assert tracked((D/'git-status-before.txt').read_text('utf8'))==tracked(subprocess.check_output(['git','status','--porcelain'],cwd=W,text=True,encoding='utf8'))
budget=read(D/'budget-plan.json');assert budget['allowed_to_execute'] is False and budget['current_authorized_new_spend_cny']==0
now=datetime.now(timezone(timedelta(hours=8))).isoformat()
out={'at':now,'phase':'zero_call_acceptance_preparation','candidate_version':candidate['version'],
 'frozen_directory_files_unchanged':sum(p.startswith('maintenance/b1-b2-candidate-20261023/') for p in protected),
 'protected_paths_unchanged':len(protected),'older_protected_files_unchanged':len(older),'candidate_source_files_unchanged':len(candidate['files']),
 'tracked_git_status_unchanged':True,'linux_tests':by,'production_and_ledger_unchanged':True,
 'candidate_test_execution_count':396,'candidate_passed':394,'candidate_failed':2,'candidate_errors':0,
 'baseline_test_execution_count':78,'baseline_passed':78,'prior_windows_4_errors_passed_on_linux':True,
 'blocking_gap':'B2 repair_router.route only validates original sources inside the arbitration branch; non-arbitrated quality_pipeline is not verified before route/prepare returns PATCH',
 'minimum_fix_proposal':'In a separate future candidate, validate quality_pipeline source fingerprint before any review is consumed in route, independent of arbitration; preserve old evidence and stop as needs_reaudit on mismatch. Keep current frozen version unchanged.',
 'runtime_code_modified':False,'frozen_candidate_modified':False,'real_api_calls':0,'balance_calls':0,'new_cost_cny':0,
 'budget_changed':False,'deployed':False,'old_tasks_resumed':False,'new_billable_tasks_created':False,
 'real_article_quality_acceptance':'NOT_PERFORMED; prior outcome remains 0/2','can_start_real_acceptance_now':False,
 'decision':'STOP: keep freeze, retain two failed assertions, source-gate gap and zero available budget prevent real acceptance; no source edits in preparation phase.'}
(D/'verification.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf8')
(D/'protected-after.json').write_text(json.dumps(protected,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({k:out[k] for k in ('at','frozen_directory_files_unchanged','older_protected_files_unchanged','candidate_passed','candidate_failed','prior_windows_4_errors_passed_on_linux','can_start_real_acceptance_now')},ensure_ascii=False))
