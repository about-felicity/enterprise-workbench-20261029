import json,sqlite3,time
from pathlib import Path
for name in ['geo-panel-baidu-ai-20261028-090004-03ddefa1','geo-panel-wenxin-card-20261028-112634-dd336205']:
 root=Path('/opt/monitor/geo-capture/batches')/name
 print('BATCH',name)
 for p in root.rglob('*.sqlite'):
  with sqlite3.connect(p.as_uri()+'?mode=ro',uri=True) as db:
   db.row_factory=sqlite3.Row
   tables=[r[0] for r in db.execute("select name from sqlite_master where type='table'")];print(str(p),tables)
   if 'captures' in tables:
    print('SCHEMA',[r[1] for r in db.execute('pragma table_info(captures)')])
    print('TASKS',[dict(r) for r in db.execute("select * from captures where state!='completed' limit 2")])
 for p in [root/'collector_progress.json',root/'collector/search_recovery.json']:
  if p.exists():print(p.name,p.read_text()[:1800])
 if 'baidu' in name:
  for p in root.rglob('*.jsonl'):
   if p.name=='results.jsonl':
    for line in p.read_text().splitlines():
     row=json.loads(line)
     if row.get('availability') or not row.get('sources'):print('MISSING',json.dumps({k:row.get(k) for k in ['question','availability','reason','body_capture_complete','task_id','sources','capture_notes']},ensure_ascii=False))
