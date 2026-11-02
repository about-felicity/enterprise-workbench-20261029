"""Read-only inspection of today's content tasks and worker health."""
import collections
import datetime
import json
import subprocess
import time
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

now=datetime.datetime.now(ZoneInfo('Asia/Shanghai'))
day=now.date().isoformat()
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
started=time.monotonic()
with op.open('http://127.0.0.1:3000/api/geo-creation/status',timeout=35) as response:
    data=json.load(response)
print('SNAPSHOT',json.dumps({'checked_at':now.isoformat(),'seconds':round(time.monotonic()-started,3),'snapshot_at':data.get('at'),'worker':data.get('worker'),'studio_health':data.get('studio',{}).get('health')},ensure_ascii=False),flush=True)
keys=['name','plan_id','date','status','articles','writing_jobs','writing_complete','error','api_recovery','supplement','progress','stages','capture_time','enabled','questions','skipped_questions']
tasks=[t for t in data['studio']['daily_tasks'] if t.get('date')==day]
for task in tasks:
    print('TASK',json.dumps({k:task.get(k) for k in keys},ensure_ascii=False),flush=True)
print('SUMMARY',json.dumps({'today':day,'plans':len(data['studio']['plans']),'today_tasks':len(tasks),'states':dict(collections.Counter(t['status'] for t in tasks)),'articles':sum(t.get('articles',0) for t in tasks),'other_unfinished':[{'name':t.get('name'),'date':t.get('date'),'status':t.get('status'),'error':t.get('error'),'supplement':t.get('supplement')} for t in data['studio']['daily_tasks'] if t.get('date','')<day and t.get('status') not in {'complete','scheduled','not_enabled','paused'}]},ensure_ascii=False),flush=True)
for service in ['geo-content-api.service','geo-content-worker.service','geo-creation-studio.service']:
    result=subprocess.run(['systemctl','show',service,'-p','ActiveState','-p','SubState','-p','NRestarts'],capture_output=True,text=True,timeout=10)
    print('SERVICE',service,result.stdout.strip(),flush=True)
base=Path('/opt/monitor/geo-content/runtime/runs')
for path in sorted(base.glob('*/job.json')):
    job=json.loads(path.read_text())
    if job.get('date')!=day:continue
    root=path.parent
    def read(p):
        try:return json.loads(p.read_text())
        except (FileNotFoundError,json.JSONDecodeError):return {}
    active=read(root/'api/active.json');control=read(root/'control.json');state=read(root/'days'/day/'day.json')
    tickets=[read(p) for p in (root/'queue').glob('*/ticket.json')]
    issues=[{'stage':t.get('stage'),'state':t.get('state'),'error':t.get('error'),'created_at':t.get('created_at')} for t in tickets if t.get('state')=='needs_attention']
    print('JOB',json.dumps({'id':root.name,'question':job.get('question'),'plan_id':job.get('studio_plan_id'),'day':state,'active':{k:active.get(k) for k in ['state','stage','run_id','updated_at']},'control':control,'queue':dict(collections.Counter(t.get('stage','')+':'+t.get('state','') for t in tickets)),'issues':issues},ensure_ascii=False),flush=True)
