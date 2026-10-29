import json,sqlite3,time,urllib.request
from pathlib import Path
def read(p):
 try:return json.loads(p.read_text())
 except (ValueError,FileNotFoundError):return {}
try:
 with urllib.request.urlopen('http://127.0.0.1:8804/api/status',timeout=45) as response:data=json.load(response)
 print('CREATION_KEYS',list(data))
 studio=data.get('studio',{})
 print('CREATION_HEALTH',json.dumps({str(p):read(p) for p in [Path('/opt/monitor/geo-content/studio/health.json'),Path('/opt/monitor/geo-content/runtime/worker_health.json')]},ensure_ascii=False))
 for task in studio.get('daily_tasks',[]):
  if task.get('date','')<'2026-10-26':continue
  print('CREATION_DAY',json.dumps({k:task.get(k) for k in ['date','name','status','capture_time','questions','writing_jobs','writing_complete','articles','error','plan_id']},ensure_ascii=False))
 print('ARTICLE_DATES',json.dumps({day:sum(a.get('date')==day for a in data.get('articles',[])) for day in ['2026-10-26','2026-10-27','2026-10-28']}))
except Exception as error:print('API_ERROR',type(error).__name__,str(error))
for root in sorted(Path('/home/user/redroid-yuanbao/batches').glob('geo-panel-*'))[-3:]:
 print('YUANBAO',root.name,json.dumps(read(root/'bridge_health.json'),ensure_ascii=False))
 with sqlite3.connect((root/'tasks.sqlite').as_uri()+'?mode=ro',uri=True) as db:
  db.row_factory=sqlite3.Row
  print('COUNTS',json.dumps([dict(r) for r in db.execute('select state,count(*) as count from tasks group by state')]))
  task=db.execute("select * from tasks where state not in ('complete','completed') order by ordinal limit 1").fetchone()
  if task:
   task=dict(task);print('CURRENT_TASK',json.dumps(task,ensure_ascii=False))
   print('EVENTS',json.dumps([dict(r) for r in db.execute('select * from events where task_id=? order by time desc limit 8',(task['task_id'],))],ensure_ascii=False))
   for suffix in ['binding.json','native.json','history-refresh.json','history-restore-v3.json']:
    state=read(root/(task['task_id']+'.'+suffix))
    if suffix=='native.json':state={k:state.get(k) for k in ['conversation','message','question','content']}
    print(suffix,json.dumps(state,ensure_ascii=False)[:6000])
