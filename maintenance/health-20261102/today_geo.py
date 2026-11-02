import json,sqlite3,time,subprocess
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
now=time.time();day=datetime.now(ZoneInfo('Asia/Shanghai')).date().isoformat()
print('TIME',datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),flush=True)
base=Path('/opt/monitor/geo-capture')
with sqlite3.connect((base/'panel/control.sqlite').as_uri()+'?mode=ro',uri=True) as db:
 db.row_factory=sqlite3.Row
 for r in db.execute('select model,day,status,desired,batch,error from daily_tasks where day=?',(day,)):print('DAILY',json.dumps(dict(r),ensure_ascii=False))
 for r in db.execute('select * from jobs where batch like ? order by created',('%'+day.replace('-','')+'%',)):
  r=dict(r);p=Path(r['health']);h=json.loads(p.read_text()) if p.exists() else {}
  print('JOB',json.dumps({'model':r['model'],'batch':r['batch'],'service':r['service'],'health_path':str(p),'health':h,'age_seconds':round(now-h.get('time',now),1)},ensure_ascii=False),flush=True)
  print('UNIT',r['service'],subprocess.run(['systemctl','show',r['service'],'-p','ActiveState','-p','SubState'],capture_output=True,text=True).stdout.strip())
  if h.get('status') not in ['complete','complete_with_unavailable']:
   print('LOG',r['batch'],subprocess.run(['journalctl','-u',r['service'],'-n','12','--no-pager','-o','cat'],capture_output=True,text=True).stdout[-5000:])
sql="select day,model_id,status,count(*),max(finished_at) from monitor_runs where day='"+day+"' group by day,model_id,status order by model_id;"
r=subprocess.run(['docker','exec','monitor-postgres','sh','-c','psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At -c "$1"','sh',sql],capture_output=True,text=True,timeout=40)
print('INGEST',r.stdout,r.stderr)
