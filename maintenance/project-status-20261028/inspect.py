import sys,json,sqlite3,subprocess,urllib.request
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
s=json.load(urllib.request.urlopen('http://127.0.0.1:8804/api/status',timeout=90));st=s['studio'];days={}
for t in st['daily_tasks']:
 d=days.setdefault(t['date'],{'tasks':0,'articles':0,'states':{}});d['tasks']+=1;d['articles']+=t['articles'];d['states'][t['status']]=d['states'].get(t['status'],0)+1
out={'at':datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'services':{},'creation_days':days,'products':len(st['products']),'plans':len(st['plans']),'attention':[{'name':t['name'],'date':t['date'],'status':t['status'],'articles':t['articles'],'reason':t.get('error','')} for t in st['daily_tasks'] if t['status'] not in ['complete','scheduled','not_enabled']],'supplement_policy':runtime.read(runtime.BASE/'supplement_policy.json')}
for name in ['monitor-dashboard','monitor-dashboard-api','geo-content-api','geo-content-worker','geo-creation-studio']:
 out['services'][name]=subprocess.run(['systemctl','is-active',name],capture_output=True,text=True).stdout.strip()
with sqlite3.connect('file:/opt/monitor/geo-capture/panel/control.sqlite?mode=ro',uri=True) as db:
 db.row_factory=sqlite3.Row;jobs=[dict(r) for r in db.execute('select j.* from jobs j join settings s on s.current_batch=j.batch')]
out['geo']=[]
for j in jobs:
 row={k:v for k,v in j.items() if k in ['batch','model','status','state','service','device']};batch=j['batch']
 for base in ['/home/user/redroid-doubao/batches','/home/user/redroid-yuanbao/batches','/opt/monitor/geo-capture/batches']:
  p=Path(base)/batch/'bridge_health.json'
  if p.exists():row['health']=runtime.read(p)
 out['geo'].append(row)
Path('/tmp/project-status-20261028.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
print(json.dumps(out,ensure_ascii=False,indent=2))
