import json,sqlite3,subprocess
from pathlib import Path
base=Path('/opt/monitor/geo-capture');root=base/'batches/geo-panel-baidu-ai-20261031-090001-88a32968'
for p in [root/'bridge_health.json',root/'collector/health.json',root/'collector/search_recovery.json',base/'search_last_start.json']:
 if p.exists():print(p.name,p.read_text()[:6500])
with sqlite3.connect((root/'collector/tasks.sqlite').as_uri()+'?mode=ro',uri=True) as db:
 db.row_factory=sqlite3.Row
 print('columns',db.execute('pragma table_info(captures)').fetchall().__str__()[:200])
 print('capture_columns',[r[1] for r in db.execute('pragma table_info(captures)')])
 for row in db.execute("select * from captures where state!='completed' limit 5"):
  print('unfinished',json.dumps({k:v for k,v in dict(row).items() if k not in ['result','response','payload']},ensure_ascii=False)[:2800])
 if db.execute("select 1 from sqlite_master where name='search_recovery_attempts'").fetchone():print('attempts',[dict(r) for r in db.execute('select * from search_recovery_attempts order by epoch desc limit 6')])
print('logs',subprocess.run(['journalctl','-u','geo-web@'+root.name+'.service','--since','today','-n','38','--no-pager'],capture_output=True,text=True).stdout[-6500:])
with sqlite3.connect((base/'panel/control.sqlite').as_uri()+'?mode=ro',uri=True) as db:
 db.row_factory=sqlite3.Row
 print('daily_tables',[r[0] for r in db.execute("select name from sqlite_master where type='table'")])
 for row in db.execute("select * from settings where model in ('wenxin_card','baidu_ai')"):
  v=dict(row);v['value']=json.loads(v['value']);print('settings',json.dumps(v,ensure_ascii=False)[:3200])
