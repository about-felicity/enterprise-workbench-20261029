import json,sys
from pathlib import Path
BASE=Path(__file__).resolve().parent
sys.path[:0]=[str(BASE/'engine'),str(BASE)]
from creation import runtime,materials
state=runtime.read(BASE/'state.json')
print('run',json.dumps(runtime.read(BASE/'acceptance-status.json'),ensure_ascii=False))
print('capture',json.dumps(materials.progress(state['date'],store_root=Path(state['capture_root'])),ensure_ascii=False))
root=BASE/'runtime/runs'/state.get('job_id','missing')
print('source_preparation',json.dumps(runtime.read(root/'material_preparation.json'),ensure_ascii=False))
if (root/'job.json').exists():
    print('day',json.dumps(runtime.read(root/'days'/state['date']/'day.json'),ensure_ascii=False))
    tickets=[runtime.read(p) for p in (root/'queue').glob('*/ticket.json')]
    print('tickets',json.dumps([{k:t.get(k) for k in ('id','stage','state','error')} for t in tickets],ensure_ascii=False))
