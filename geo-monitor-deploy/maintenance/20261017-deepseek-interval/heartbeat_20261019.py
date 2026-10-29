import json,sys
from pathlib import Path
sys.path.insert(0,'/opt/monitor/geo-capture')
from control_panel import Controller,read
from daily_tasks import today
c=Controller()
for day in ('2026-10-18',today()):
 for m in c.all(day)['models']:
  d=m['daily'];s=m['current']
  print(json.dumps({'day':day,'model':m['id'],'desired':d['desired'],'status':d['status'],'completed':d['completed'],'target':d['target'],'remaining':d['remaining'],'error':d.get('error'),'current':{k:s.get(k) for k in ('batch','service_state','state','processed','pending_delivery','needs_review','heartbeat_age','progress','tasks','diagnostics')}},ensure_ascii=False))
