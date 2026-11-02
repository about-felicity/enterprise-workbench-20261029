import json,urllib.request,time,subprocess,collections
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
now=datetime.now(ZoneInfo('Asia/Shanghai'));day=now.date().isoformat();print('TIME',now.isoformat())
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
for route in ['status','ui']:
 start=time.monotonic()
 with op.open('http://127.0.0.1:3000/api/geo-creation/'+route,timeout=30) as r:
  data=r.read();print('HTTP',route,r.status,len(data),round(time.monotonic()-start,3))
  if route=='status':panel=json.loads(data)
tasks=[t for t in panel['studio']['daily_tasks'] if t.get('date')==day]
for t in tasks:
 print('TASK',json.dumps({k:t.get(k) for k in ['name','plan_id','status','articles','writing_jobs','writing_complete','error','api_recovery']},ensure_ascii=False))
print('SERVICES',subprocess.check_output(['systemctl','show','geo-content-api','geo-content-worker','geo-creation-studio','-p','Id','-p','ActiveState','-p','SubState','-p','NRestarts']).decode())
logs=subprocess.run(['journalctl','-u','geo-content-api','-u','geo-content-worker','-u','geo-creation-studio','--since','2 hours ago','--no-pager','-o','cat','-n','2000'],capture_output=True,text=True).stdout
print('LOG_ERROR_COUNTS',json.dumps({s:logs.lower().count(s) for s in ['traceback','out of memory','http 502','http 503','error','exception']}))
base=Path('/opt/monitor/geo-content/runtime/runs')
for p in base.glob('*/job.json'):
 j=json.loads(p.read_text())
 if j.get('date')!=day:continue
 root=p.parent
 def read(name):
  try:return json.loads((root/name).read_text())
  except FileNotFoundError:return {}
 d=read('days/'+day+'/day.json');a=read('api/active.json');m=read('material_preparation.json')
 if d.get('status') not in ['complete','completed']:
  print('JOB',json.dumps({'id':root.name,'question':j.get('question'),'preparation':j.get('preparation'),'shortfall':j.get('material_shortfall'),'day_status':d.get('status'),'api_state':a.get('state'),'api_stage':a.get('stage'),'material_phase':m.get('phase'),'processed':m.get('processed'),'total':m.get('total'),'cache_hits':m.get('cache_hits'),'material_age_seconds':round(time.time()-m['at']) if m.get('at') else None},ensure_ascii=False))
