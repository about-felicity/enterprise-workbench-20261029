import sqlite3,json,sys
from collections import defaultdict
from datetime import datetime
from zoneinfo import ZoneInfo
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import studio
z=ZoneInfo('Asia/Shanghai');out={};groups={k:defaultdict(lambda:dict(calls=0,prompt=0,output=0,hit=0,reasoning=0,charged=0,reserved=0,unsettled=0)) for k in ['day','hour','task','stage','state']}
with sqlite3.connect('file:/home/user/geo-editorial/runtime-api/api/costs.sqlite?mode=ro',uri=True) as db:
 db.row_factory=sqlite3.Row
 rows=db.execute("select c.*,s.scope,s.task_day from costs c left join studio_cost_scopes s on s.id=c.id where c.created>=?",(datetime(2026,10,28,tzinfo=z).timestamp(),)).fetchall()
 for row in rows:
  r=dict(row);dt=datetime.fromtimestamp(r['created'],z);u=json.loads(r['usage'] or '{}') or {};day=dt.strftime('%Y-%m-%d')
  for typ,key in [('day',day),('hour',dt.strftime('%Y-%m-%d %H')),('task',day+' '+str(r['scope'])),('stage',day+' '+str(r['stage'])),('state',day+' '+str(r['state']))]:
   g=groups[typ][key];g['calls']+=1;g['charged']+=r['charged'] or 0;g['reserved']+=(r['reserved'] or 0) if r['charged'] is None else 0;g['unsettled']+=int(r['charged'] is None)
   for field,source in [('prompt','prompt_tokens'),('output','completion_tokens'),('hit','prompt_cache_hit_tokens')]:g[field]+=u.get(source,0) or 0
   g['reasoning']+=(u.get('completion_tokens_details') or {}).get('reasoning_tokens',0) or 0
 names={}
 for r in rows:
  pid=r['scope']
  if pid and pid not in names:
   try:names[pid]=studio.plan(pid,include_deleted=True).get('name',pid)
   except Exception:names[pid]=pid
print(json.dumps(dict(as_of=datetime.now(z).isoformat(),groups=groups,names=names),ensure_ascii=False,indent=2))
