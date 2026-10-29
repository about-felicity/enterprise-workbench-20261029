import sys,json,time
from pathlib import Path
sys.path.insert(0,'/opt/monitor/geo-capture')
from control_panel import Controller
from daily_tasks import database_counts,today
b=Path('/opt/monitor/geo-deepseek-browser-test');s=json.loads((b/'state.json').read_text());j=s.get('plugin_job') or {}
print(json.dumps({'browser':{'auth':s.get('auth'),'age':round(time.time()-s['updated_at'],1),'job_state':j.get('state'),'cursor':j.get('cursor'),'inFlight':j.get('inFlight'),'next_send_not_before':s.get('next_send_not_before')}},ensure_ascii=False))
root=Path('/home/user/redroid-deepseek-account2/batches/geo-panel-deepseek2-20261019-103338-38eaf48a')
for p in (root/'outbox').glob('*.json'):
 d=json.loads(p.read_text());r=root/'receipts'/p.name;up=Path('/opt/monitor/runtime/lan_result_receiver/deepseek/done')/p.name
 print(json.dumps({'receipt':{'frozen':True,'local_confirmed':r.exists(),'upstream_processed':up.exists(),'same_receipt':r.exists() and up.exists() and json.loads(r.read_text())==json.loads(up.read_text())}},ensure_ascii=False))
d=Controller(Path('/opt/monitor/geo-capture')).all()
for m in d['models']:
 c=m['current'];print(json.dumps({'model':m['id'],'state':c['state'],'service':c['service_state'],'batch':c['batch'],'captured':c['captured'],'processed':c['processed'],'pending_delivery':c['pending_delivery'],'heartbeat_age':c['heartbeat_age'],'progress':c.get('progress'),'diagnostics':c.get('diagnostics'),'daily':{k:m['daily'].get(k) for k in ['completed','target','status']}},ensure_ascii=False))
print(json.dumps({'pg_today':{k:sum(v.values()) for k,v in database_counts(today()).items()}}))
