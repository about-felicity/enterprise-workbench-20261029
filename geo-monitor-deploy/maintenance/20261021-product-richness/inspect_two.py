import json
from pathlib import Path
r=Path('/opt/monitor/geo-content/runtime/runs/creation-1792556219-bbc55e13')
for p in (r/'queue').glob('*/ticket.json'):
 v=json.loads(p.read_text())
 if v['meta'].get('category')=='排行类' and v['meta'].get('number')==2:print(json.dumps({k:v.get(k) for k in ['id','stage','state','location','meta','error','replaced_by']},ensure_ascii=False))
