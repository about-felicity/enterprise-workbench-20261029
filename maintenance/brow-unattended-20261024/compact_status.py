import json, sys
from pathlib import Path
B=Path(__file__).resolve().parent
sys.path[:0]=[str(B/'release/engine'),str(B/'release')]
from geo_source_cards.staged_editorial import read
state=read(B/'state.json');root=B/'runtime/runs'/state['job_id']
tickets=[read(p) for p in (root/'queue').glob('*/ticket.json')]
print(json.dumps({'driver':read(B/'acceptance-status.json'),
    'active':[{'stage':t['stage'],'state':t['state'],'category':t['meta'].get('category'),
        'number':t['meta'].get('number'),'repair':t['meta'].get('targeted_repair_round',0),
        'error':str(t.get('error',''))[:700]} for t in tickets if t['state'] not in {'accepted','revision_requested'}],
    'approved':len(list((root/'approved').glob('*/*/*/receipt.json'))),
    'requests':[{'path':str(p.relative_to(root)),'state':read(p).get('state')} for p in (root/'api').rglob('api_state.json') if read(p).get('state') in {'REQUESTING','REQUEST_UNKNOWN'}]
},ensure_ascii=False,indent=2))
