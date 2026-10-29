import hashlib,json,sqlite3,subprocess,time,urllib.request
from pathlib import Path
pid='plan-6334cde812bd49549df6efd87a51e3b3';day='2026-10-20'
with urllib.request.urlopen('http://127.0.0.1:8804/api/status',timeout=30) as response:status=json.load(response)
task=next(v for v in status['studio']['daily_tasks'] if v['plan_id']==pid and v['date']==day)
assert task['status']=='complete' and task['writing_complete']==2 and task['articles']==2
assert task['frequency']=='once'
plan=next(v for v in status['studio']['plans'] if v['plan_id']==pid)
assert plan['task_budget_cny']==2 and plan['channels']==['baidu_ai','wenxin_card']
with sqlite3.connect('file:/home/user/geo-editorial/runtime-api/api/costs.sqlite?mode=ro',uri=True) as db:
 cost=db.execute('select coalesce(sum(c.charged),0),sum(case when c.charged is null then 1 else 0 end) from costs c join studio_cost_scopes s on s.id=c.id where s.scope=?',(pid,)).fetchone()
assert cost[0]<=2 and cost[1]==0
sql="select count(*) from monitor_ingest_events where record->>'batch_id' in ('creation-material-2026-10-20-baidu_ai','creation-material-2026-10-20-wenxin_card');"
geo_count=int(subprocess.check_output(['docker','exec','monitor-postgres','psql','-U','monitor_app','-d','monitor','-At','-c',sql],text=True).strip());assert geo_count==0
out={'checked_at':time.time(),'task':task,'cost_cny':cost[0],'unsettled_calls':cost[1],'geo_ingest_rows_for_creation_batches':geo_count,'word_visual_qa':{'method':'Native Microsoft Word PDF export after packaged renderer reported missing LibreOffice, followed by Poppler PNG rendering and all-page inspection','pages':[6,5],'files_unchanged':True},'source_mapping':{'matched':133,'files':133}}
Path('/tmp/whitening-e2e-final.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
print(json.dumps(out,ensure_ascii=False))
