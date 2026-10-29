import json,collections
from pathlib import Path
r=Path('/opt/monitor/geo-content/runtime/runs/creation-1793057255-8a64b316');m=json.loads((r/'geo_material_manifest.json').read_text());print('keys',list(m))
for k,v in m.items():
 if k=='observations':continue
 if isinstance(v,list):print(k,'count',len(v),'sample',json.dumps(v[:2],ensure_ascii=False)[:1800])
 else:print(k,str(v)[:1000])
print('analysis files',[str(p.relative_to(r)) for p in (r/'private_source_analysis').glob('*')][:8])
