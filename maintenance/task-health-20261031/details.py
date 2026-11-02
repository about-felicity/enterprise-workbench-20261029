import collections,datetime,json,subprocess,urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo
day=datetime.datetime.now(ZoneInfo('Asia/Shanghai')).date().isoformat()
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:8804/api/status',timeout=35) as r:data=json.load(r)
print('TODAY',json.dumps([{'name':t['name'],'state':t['status'],'articles':t['articles'],'at':t['capture_time']} for t in data['studio']['daily_tasks'] if t['date']==day],ensure_ascii=False))
for service in ['geo-content-api.service','geo-content-worker.service','geo-creation-studio.service']:
 print('SERVICE',service,subprocess.run(['systemctl','show',service,'-p','ActiveState','-p','SubState','-p','NRestarts'],capture_output=True,text=True,timeout=10).stdout.strip())
result=subprocess.run(['journalctl','-u','geo-creation-studio.service','--since','2026-10-31 00:00:00','-n','55','--no-pager','-o','cat'],capture_output=True,text=True,timeout=15)
print('STUDIO_LOG',result.stdout[-10000:])
for path in sorted(Path('/opt/monitor/geo-content/runtime/runs').glob('*/job.json')):
 job=json.loads(path.read_text());root=path.parent
 if job.get('date')!=day:continue
 for p in (root/'queue').glob('*/ticket.json'):
  ticket=json.loads(p.read_text())
  if ticket.get('state')!='needs_attention':continue
  execution=ticket.get('execution',{});run=root/'api/runs'/execution.get('run_id','missing')
  details=[]
  for f in run.rglob('api_state.json'):
   state=json.loads(f.read_text());details.append({k:state.get(k) for k in ['state','http_status','error','reason','finish_reason','message']})
  print('FAILED',json.dumps({'job':root.name,'question':job.get('question'),'stage':ticket.get('stage'),'error':ticket.get('error'),'execution':{k:execution.get(k) for k in ['run_id','state']},'response_states':details},ensure_ascii=False))
print('STUDIO_HEALTH',json.dumps(data['studio'].get('health'),ensure_ascii=False))
