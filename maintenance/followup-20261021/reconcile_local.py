"""Compare completed repair against the initial evidence; no network or writes to production."""
import json
from pathlib import Path
from collections import Counter
base=Path(__file__).resolve().parent
before=json.loads((base/'before.json').read_text('utf-8'));after=json.loads((base/'after.json').read_text('utf-8'))
before_ids={c['state'].get('reservation') for r in before['articles'] for c in r['calls']}
new={c['state'].get('reservation'):c['ledger'] for r in after['articles'] for c in r['calls'] if c['state'].get('reservation') not in before_ids and c['ledger']}
def unknown(data):return {c['state']['reservation']:c for r in data['articles'] for c in r['calls'] if c['state'].get('state')=='REQUEST_UNKNOWN'}
assert unknown(before)==unknown(after),'Original unknown request evidence changed'
roots={r['root']:r['root_control'] for r in before['articles']}
current={r['root']:r['root_control'] for r in after['articles']}
assert roots==current,'Original production control changed'
buckets=Counter();items=[]
for r in after['articles']:
 state=r['status'].get('state');reason=r['status'].get('reason','')
 if state=='complete':bucket='complete'
 elif state=='unknown_request':bucket='unknown_request'
 elif r['preflight']!='ready':bucket='insufficient_original_material'
 elif reason=='invalid_response':bucket='malformed_paid_response'
 elif '仅允许复用并审稿' in reason:bucket='delivered_draft_requires_targeted_recovery'
 else:bucket='content_structure_or_review'
 buckets[bucket]+=1
 items.append({'key':r['key'],'root':r['root'],'article':r['id'],'bucket':bucket,'reason':reason,'material_preflight':r['preflight']})
report={'buckets':dict(buckets),'new_paid_calls':len(new),'new_settled_cost_cny':sum((r['charged'] or 0) for r in new.values()),'new_unsettled_calls':sum(r['charged'] is None for r in new.values()),'original_unknown_requests_identical':True,'all_original_controls_identical':True,'articles':items}
(base/'reconciliation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='articles'},ensure_ascii=False))
