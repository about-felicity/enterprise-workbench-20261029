import sqlite3,json,sys
from datetime import datetime,timedelta
from zoneinfo import ZoneInfo
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import studio
now=datetime.now(ZoneInfo('Asia/Shanghai'));start=now.replace(hour=0,minute=0,second=0,microsecond=0).timestamp();end=start+86400
with sqlite3.connect('file:/home/user/geo-editorial/runtime-api/api/costs.sqlite?mode=ro',uri=True) as db:
 for label,where,args in [('today_created','c.created>=? and c.created<?',(start,end)),('today_tasks','s.task_day=?',(now.date().isoformat(),))]:
  rows=db.execute('select s.scope,count(*),sum(case when c.charged is not null then c.charged else 0 end),sum(case when c.charged is null then coalesce(c.reserved,0) else 0 end),sum(case when c.charged is null then 1 else 0 end) from costs c join studio_cost_scopes s on c.id=s.id where '+where+' group by s.scope',args).fetchall()
  out=[]
  for pid,n,charged,reserved,pending in rows:
   try:name=studio.plan(pid,include_deleted=True).get('name',pid)
   except Exception:name=pid
   out.append(dict(name=name,calls=n,charged=charged,reserved_unsettled=reserved,unsettled_calls=pending))
  print(label,json.dumps(out,ensure_ascii=False))
  print('TOTAL',label,json.dumps({'charged':sum(r[2] for r in rows),'reserved_unsettled':sum(r[3] for r in rows),'calls':sum(r[1] for r in rows)}))
 print('STATES',json.dumps(db.execute('select c.state,count(*),sum(coalesce(c.charged,0)),sum(case when c.charged is null then coalesce(c.reserved,0) else 0 end) from costs c join studio_cost_scopes s on s.id=c.id where c.created>=? and c.created<? group by c.state',(start,end)).fetchall()))
 print('UNSCOPED_TODAY',json.dumps(db.execute('select count(*),sum(coalesce(c.charged,0)),sum(case when c.charged is null then coalesce(c.reserved,0) else 0 end) from costs c left join studio_cost_scopes s on s.id=c.id where s.id is null and c.created>=? and c.created<?',(start,end)).fetchone()))
print('AS_OF',now.isoformat())
