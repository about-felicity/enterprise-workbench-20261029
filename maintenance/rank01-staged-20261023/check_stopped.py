"""Read-only reconciliation; never imports API clients or mutates the run."""
import hashlib,json,sqlite3
from pathlib import Path
root=Path('/opt/monitor/geo-content/runtime/acceptance/20261023-rank01-staged/rank01-staged-20261023T120816-e50a98ac')
read=lambda p:json.loads(Path(p).read_text('utf-8-sig'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
auth=read(root/'preflight.json');cost=read(root/'cost_ledger.json')
with sqlite3.connect('file:/home/user/geo-editorial/runtime-api/api/costs.sqlite?mode=ro',uri=True) as db:
 db.row_factory=sqlite3.Row
 rows=[dict(db.execute('select * from costs where id=?',(r['id'],)).fetchone()) for r in cost['ledger_after']['run_rows']]
 unknown=[dict(r) for r in db.execute('select id,state,reserved from costs where charged is null order by id')]
assert rows==cost['ledger_after']['run_rows'],'Known run ledger changed; reconcile before any action'
old_unknown=sorted(cost['ledger_after']['unknown'],key=lambda r:r['id'])
result={'run_id':root.name,'status':read(root/'summary.json')['status'],'current_shared_settings':read(Path('/home/user/geo-editorial/runtime-api/settings.json')),'original_limits_restored':read(root/'job.json')==read(Path('/opt/monitor/geo-content/runtime/runs/creation-1792575159-0a8f9221/job.json')),'protected_sha_all_match':all(Path(p).is_file() and sha(p)==v for p,v in auth['protected_before'].items()),'settled_model_calls':len(rows),'known_cost_cny':sum(r['charged'] for r in rows),'incremental_authorization_remaining_cny':7.2-sum(r['charged'] for r in rows),'historical_unknown_records_unchanged':unknown==old_unknown,'new_api_calls_by_this_check':0,'retry_limit':2,'analyzer_max_tokens':2400,'files':{n:(root/n).is_file() for n in ['rank01_first_draft.docx','rank01_first_draft.md','review_fact.json','review_logic.json','cost_ledger.json']}}
print(json.dumps(result,ensure_ascii=False,indent=2))
