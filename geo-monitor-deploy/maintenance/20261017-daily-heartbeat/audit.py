"""Read-only daily capture audit; no task creation, recovery or configuration writes."""
import json,sqlite3,subprocess,time,urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
B=Path('/opt/monitor/geo-capture');day=datetime.now(ZoneInfo('Asia/Shanghai')).date().isoformat()
def read(p):
 try:return json.loads(Path(p).read_text())
 except FileNotFoundError:return {}
panel=json.load(urllib.request.urlopen('http://127.0.0.1:8803/api/panel',timeout=25))
rows=[]
with sqlite3.connect((B/'panel/control.sqlite').as_uri()+'?mode=ro',uri=True) as db:
 db.row_factory=sqlite3.Row
 saved={r['model']:dict(r) for r in db.execute('select * from daily_tasks where day=?',(day,))}
 jobs={r['model']:dict(r) for r in db.execute('select j.* from jobs j join settings s on s.current_batch=j.batch')}
 for m in panel['models']:
  j=jobs[m['id']];d=m['daily'];cfg=json.loads(saved[m['id']]['config']);assert cfg==d['config']
  service=subprocess.check_output(['systemctl','show',j['service'],'--property=ActiveState,Result,ExecMainStatus'],text=True).strip()
  h=read(j['health']);session=read(Path(j['health']).parent/'collector/deepseek_session.json') if m['id']=='deepseek' else {}
  rows.append({'model':m['id'],'day_status':d['status'],'desired':d['desired'],'day_batch':d['batch'],'current_batch':j['batch'],'question_count':len(cfg['questions']),'rounds':cfg['rounds'],'interval':cfg['interval'],'completed':d['completed'],'target':d['target'],'remaining':d['remaining'],'processed':m['current']['processed'],'pending_delivery':m['current']['pending_delivery'],'needs_review':m['current']['needs_review'],'service':service,'health':{k:h[k] for k in ('status','state','time','message','child_exit_code','last_exit_code','next_retry_at') if k in h},'login':{k:m.get('login_status',{}).get(k) for k in ('status','checked_at','message')},'session':{k:session[k] for k in ('status','message','time') if k in session}})
sql="""BEGIN READ ONLY; SELECT coalesce(json_agg(t),'[]') FROM (SELECT e.source_device,count(*) AS receipts,max(r.finished_at) AS latest FROM monitor_ingest_events e JOIN monitor_runs r ON r.model_id=e.model_id AND r.run_id=e.run_id WHERE r.day='%s' AND r.status='success' AND coalesce(r.payload->>'body_capture_complete','true')='true' GROUP BY e.source_device ORDER BY e.source_device)t; COMMIT;"""%day
raw=subprocess.check_output(['docker','exec','monitor-postgres','psql','-X','-qAt','-U','monitor_app','-d','monitor','-v','ON_ERROR_STOP=1','-c',sql],text=True,timeout=20)
result={'checked_at':datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'day':day,'daily_plan':read(B/'daily_plan.json'),'daily_control_health':read(B/'daily_control_health.json'),'persisted_status':read(B/'daily'/day/'status.json'),'models':rows,'database_receipts':json.loads(raw.strip())}
print(json.dumps(result,ensure_ascii=False,indent=2))
