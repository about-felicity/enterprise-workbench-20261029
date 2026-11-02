import json,sqlite3,datetime
from pathlib import Path
def read(path):
 try:return json.loads(path.read_text())
 except (OSError,ValueError):return {}
rows=[]
for path in Path('/opt/monitor/geo-capture/batches').glob('*/manifest.json'):
 value=read(path)
 if value.get('model')=='wenxin_card':rows.append((value.get('created_at',0),path.parent))
for _,root in sorted(rows)[-2:]:
 h=read(root/'bridge_health.json')
 print(json.dumps({'batch':root.name,'health':{k:h.get(k) for k in ['status','updated_at','tasks','error','last_error']},'paused':(root/'pause.json').exists()},ensure_ascii=False))
 p=root/'collector/tasks.sqlite'
 if p.exists():
  with sqlite3.connect(p.as_uri()+'?mode=ro',uri=True) as db:
   tables={r[0] for r in db.execute("select name from sqlite_master where type='table'")}
   if 'captures' in tables:print('captures',db.execute('select state,count(*) from captures group by state').fetchall())
   if 'search_recovery_attempts' in tables:print('recovery',db.execute('select kind,error,epoch from search_recovery_attempts order by epoch desc limit 3').fetchall())
  recovery=read(root/'collector/search_recovery.json')
  print('search_recovery',json.dumps({k:recovery.get(k) for k in ['status','blocked','streak','last_error','cooldown_until']},ensure_ascii=False))
print('auto_retry',json.dumps(read(Path('/opt/monitor/geo-capture/profiles/search/wenxin_card/verification_retry.json')),ensure_ascii=False))
