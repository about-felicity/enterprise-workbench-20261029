import json
from pathlib import Path
p=Path('/opt/monitor/geo-content/runtime/runs/creation-1793057255-8a64b316/private_source_analysis/analysis.json');r=json.loads(p.read_text());print(list(r))
for k,v in r.items():
 if k in ['answer_analysis','observations']:continue
 if isinstance(v,list):print(k,len(v),json.dumps(v[:3],ensure_ascii=False)[:2500])
 else:print(k,str(v)[:300])
