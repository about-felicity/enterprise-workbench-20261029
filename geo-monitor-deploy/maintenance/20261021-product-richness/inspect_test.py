import json
from pathlib import Path
r=Path('/opt/monitor/geo-content/runtime/runs/creation-1792556219-bbc55e13')
def read(p):return json.loads(p.read_text()) if p.exists() else {}
print('EVENTS')
for p in r.glob('**/*events*'):
 if p.is_file():print(str(p),p.read_text()[-9000:])
for p in (r/'days/2026-10-21/jobs').glob('*/*/research/research_input.json'):
 b=read(p).get('reference_design',{});print('SOURCE',str(p.parent.parent.relative_to(r)),b.get('primary_url'),[a['name'] for a in b.get('products',[])])
a=read(r/'api/active.json');run=r/'api/runs'/a.get('run_id','none');print('RUNFILES',[p.name for p in run.rglob('*') if p.is_file()]);print('CONTROL',read(r/'control.json'))
