import json,os,sqlite3
from pathlib import Path
for d in ['/opt/monitor/geo-capture','/home/user/geo-editorial/runtime-api','/opt/monitor/geo-content']:
 p=Path(d);print('DIRECTORY',d,[(x.name,'dir' if x.is_dir() else 'file') for x in p.iterdir()][:65])
for d in ['/opt/monitor/geo-capture/panel','/home/user/geo-editorial/runtime-api/captures','/home/user/geo-editorial/runtime-api/source_cache']:
 p=Path(d);print('SUBDIR',d,[x.name for x in p.iterdir()][:25] if p.exists() else None)
for p in Path('/opt/monitor/geo-capture').glob('**/results.jsonl'):
 print('CAPTURE_FILE',str(p),p.stat().st_size)
 if sum(1 for _ in p.open())>0:
  row=json.loads(next(x for x in p.open() if x.strip()));print('ROW_KEYS',list(row),'SOURCE_SAMPLE',json.dumps((row.get('sources') or [])[:1],ensure_ascii=False)[:900]);break
