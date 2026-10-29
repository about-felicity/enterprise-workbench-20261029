import hashlib,json,shutil,sys
from pathlib import Path
sys.path[:0]=['/tmp/brow-scope-qa/engine','/opt/monitor/geo-content']
from creation import runtime
from geo_source_cards.api_worker import materialize
from geo_source_cards.staged_editorial import validate_research,source_map,sha
task=runtime.read(Path('/opt/monitor/geo-capture/maintenance/20261020-brow-daily/task.json'))
roots=[p.parent for p in (runtime.BASE/'runs').glob('*/job.json') if runtime.read(p).get('studio_plan_id')==task['plan_id']];assert len(roots)==1
r=roots[0];failed=[runtime.read(p) for p in (r/'queue').glob('*/ticket.json') if runtime.read(p).get('state')=='needs_attention'];assert len(failed)==1
t=failed[0];run=r/'api/runs'/t['execution']['run_id'];assert runtime.read(run/'call/api_state.json').get('state')=='RESPONDED'
dry=Path('/tmp/brow-property-recheck-preview');dry.mkdir(exist_ok=False,mode=0o700)
for p in run.iterdir():
 if p.is_file():shutil.copy2(p,dry/p.name)
answer=runtime.read(run/'call/response.json');materialize(t,dry,answer)
inputs=runtime.read(dry/'research_input.json');result=runtime.read(dry/'research_result.json')
decision=validate_research(result,source_map(inputs['observations']),sha(json.dumps(inputs,ensure_ascii=False,sort_keys=True))[:24],primary_url=inputs['reference_design']['primary_url'])
projection=runtime.read(dry/'research_projection.json')
assert projection['derived_neutral_properties'] and projection['demoted_ids']
print(json.dumps({'ticket':t['id'],'new_api_calls':0,'validation':decision,'derived_neutral_properties':projection['derived_neutral_properties'],'original_model_response_preserved':True},ensure_ascii=False))
