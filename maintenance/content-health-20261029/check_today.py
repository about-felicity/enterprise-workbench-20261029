import json,subprocess,time,urllib.request
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
now=datetime.now(ZoneInfo('Asia/Shanghai'));today=now.date().isoformat()
op=urllib.request.build_opener(urllib.request.ProxyHandler({}));out={'at':now.isoformat(),'services':{}}
for name in ['geo-content-api','geo-content-worker','geo-creation-studio']:
 out['services'][name]=subprocess.run(['systemctl','show',name,'-p','ActiveState','-p','SubState','-p','MainPID','-p','NRestarts'],capture_output=True,text=True).stdout
out['dashboard']=subprocess.run(['docker','inspect','monitor-dashboard','--format','{{json .State}}'],capture_output=True,text=True).stdout
for endpoint in ['status','uploads']:
 start=time.monotonic()
 try:
  with op.open('http://127.0.0.1:8804/api/'+endpoint,timeout=90) as r:s=json.load(r)
  out[endpoint+'_seconds']=round(time.monotonic()-start,3)
  if endpoint=='status':
   st=s['studio'];out['today_tasks']=[t for t in st['daily_tasks'] if t['date']==today];out['older_attention']=[t for t in st['daily_tasks'] if t['date']!=today and t['status'] not in ['complete','scheduled','not_enabled']];out['plans']=st['plans'];out['jobs']=s.get('jobs',[])
  else:out['upload_counts']={k:len(s['studio'].get(k,[])) for k in ['products','knowledge_library','product_images']}
 except Exception as e:out[endpoint+'_error']=str(e)
out['logs']=subprocess.run(['journalctl','-u','geo-content-api','-u','geo-content-worker','-u','geo-creation-studio','--since',str(int(now.replace(hour=0,minute=0,second=0,microsecond=0).timestamp())),'-n','160','--no-pager'],capture_output=True,text=True).stdout
Path('/tmp/content-health-20261029.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
compact={k:v for k,v in out.items() if k not in ['plans','jobs','older_attention']};print(json.dumps(compact,ensure_ascii=False,indent=2))
