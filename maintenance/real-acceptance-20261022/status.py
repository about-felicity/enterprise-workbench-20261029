"""Read-only real acceptance observation; no model/provider calls."""
import json,sqlite3,time
from pathlib import Path
R=Path('/opt/monitor/geo-content/runtime/acceptance/20261022-three-agent')
def read(p):return json.loads(p.read_text('utf8')) if p.is_file() else {}
a=read(R/'authorization.json');out={'status':read(R/'status.json'),'active':read(R/'api/active.json'),'control':read(R/'control.json'),'summary':read(R/'summary.json')}
out['runs']=[]
for run in (R/'api/runs').glob('*'):
    manifest=read(run/'section_calls/manifest.json')
    states=[]
    for p in run.rglob('api_state.json'):
        v=read(p);states.append({'call':str(p.parent.relative_to(run)),**{k:v[k] for k in ('state','failure_code','http_status','started_epoch') if k in v}})
    out['runs'].append({'id':run.name,'sections_status':manifest.get('status'),'sections':list(manifest.get('components',{})),'states':states,'materialization':read(run/'materialization_error.json')})
out['tickets']=[{k:v for k,v in read(p).items() if k in ('id','state','stage','location','meta','error')} for p in (R/'queue').glob('*/ticket.json')]
con=sqlite3.connect('file:/home/user/geo-editorial/runtime-api/api/costs.sqlite?mode=ro',uri=True);con.row_factory=sqlite3.Row
rows=[dict(x) for x in con.execute('select id,category,article,stage,state,reserved,charged,usage,created from costs where created>=? order by created',(a.get('at',time.time()),))]
out['new_calls']=rows;out['new_charged_cny']=sum(x['charged'] or 0 for x in rows);out['new_reserved_cny']=sum(x['reserved'] for x in rows if x['charged'] is None)
out['unknown_ids']=[x[0] for x in con.execute("select id from costs where state!='settled'")]
print(json.dumps(out,ensure_ascii=False))
