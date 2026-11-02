import hashlib,json,sqlite3,datetime
from pathlib import Path
base=Path('/opt/monitor/geo-capture');root=base/'batches/geo-panel-baidu-ai-20261031-090001-88a32968'
print('time',datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat())
for p in [root/'bridge_health.json',root/'collector_progress.json']:
 print(p.name,p.read_text()[:1900])
with sqlite3.connect((root/'collector/tasks.sqlite').as_uri()+'?mode=ro',uri=True) as db:
 old=json.loads((base/'maintenance/wenxin-20261031/completed-before.json').read_text());now={task:hashlib.sha256(result.encode()).hexdigest() for task,result in db.execute("select task_id,result from captures where state='completed'")};assert all(now.get(t)==h for t,h in old.items())
 print('preserved',len(old),'completed_now',len(now))
for p in (base/'batches').glob('*wenxin*20261031*/bridge_health.json'):print('wenxin_today',p.parent.name,p.read_text()[:1500])
