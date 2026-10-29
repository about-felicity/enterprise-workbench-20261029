"""Read-only audit. Never import API clients or open a writable ledger."""
import hashlib,json,sqlite3,sys,time
from pathlib import Path
R=Path('/opt/monitor/geo-content/runtime/acceptance/20261022-three-agent')
P=Path('/opt/monitor/geo-content/engine/geo_source_cards')
def read(p):return json.loads(p.read_text('utf-8-sig')) if p.is_file() else {}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
auth=read(R/'authorization.json');originals=auth.get('original_hashes',{})
db=sqlite3.connect('file:/home/user/geo-editorial/runtime-api/api/costs.sqlite?mode=ro',uri=True);db.row_factory=sqlite3.Row
rows=[dict(r) for r in db.execute('select * from costs order by id')]
scopes=[dict(r) for r in db.execute('select * from studio_cost_scopes order by id')]
lookup={r['id']:r for r in rows};job=read(R/'job.json');scope=job['studio_plan_id']
joined=[{**lookup[s['id']],**{k:v for k,v in s.items() if k!='id'}} for s in scopes if s['id'] in lookup and s['scope']==scope and s['task_day']==job['date']]
def used(rows):return sum(r['charged'] if r['charged'] is not None else r['reserved'] for r in rows)
balance=R/'api/balance.json'
files={n:{'production_sha256':sha(P/n),'stage_sha256':sha(R/'stage/engine/geo_source_cards'/n)} for n in ('consumer_prompts.py','structure_analyzer.py','section_writer.py','review_arbitration.py')}
tests={n:sha(R/'stage/tests'/n) for n in ('test_section_budget_revision.py','test_arbitration_batches.py')}
result={'at':time.time(),'read_only':True,'new_api_calls':0,'sources':files,'tests':tests,
 'original_hashes_current':{p:sha(Path(p)) for p in originals},'originals_match_previous':all(sha(Path(p))==v for p,v in originals.items()),
 'ledger':{'rows':len(rows),'rows_sha256':hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest(),'scopes_sha256':hashlib.sha256(json.dumps(scopes,sort_keys=True).encode()).hexdigest(),
 'unknown':[{'id':r['id'],'reserved':r['reserved'],'state':r['state']} for r in rows if r['charged'] is None],
 'scope_used':used(joined),'scope':scope,'per_article':{c:used([r for r in joined if r['job']==job['job_id'] and (r['category']=='' or r['category']==c and r['article'] in ('shared',str(n)))]) for c,n in (('排行类',1),('测评类',2))},
 'today_used':used([r for r in rows if r['date']=='2026-10-23'])},
 'shared_settings':read(Path('/home/user/geo-editorial/runtime-api/settings.json')),
 'acceptance_budget':job.get('budget_limits'),'acceptance_control':read(R/'control.json'),'acceptance_active':read(R/'api/active.json'),
 'balance_cache':read(balance),'balance_cache_mtime':balance.stat().st_mtime if balance.exists() else None,
 'last_final_audit_balance':{k:read(R/'final-audit.json').get(k) for k in ('at','balance_after')}}
print(json.dumps(result,ensure_ascii=False))
