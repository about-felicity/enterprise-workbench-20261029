import json,sqlite3,subprocess,sys,time,urllib.request
from datetime import date,timedelta
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime,studio
report=runtime.read(Path('/opt/monitor/geo-capture/maintenance/20261020-brow-daily/task.json'));pid=report['plan_id'];day=report['start_date']
with urllib.request.urlopen('http://127.0.0.1:8804/api/status',timeout=30) as response:data=json.load(response)
task=next(t for t in data['studio']['daily_tasks'] if t['plan_id']==pid and t['date']==day);plan=studio.plan(pid)
assert task['status']=='complete' and task['articles']==plan['article_target']==15
assert task['writing_complete']==1 and task['writing_jobs']==1
assert plan['enabled'] and plan['frequency']=='daily' and plan['capture_time']=='01:00' and plan['writing_time']=='04:00'
assert plan['article_budget_cny']==.35 and plan['task_budget_cny']==5.25
assert len(plan['questions'])==8 and plan['questions']==report['questions'] and plan['rounds']==1
assert runtime.read(Path('/opt/monitor/geo-capture/daily_plan.json'))['time']=='09:00'
cfg=runtime.read(studio.capture_root(pid)/'settings.json');assert cfg.get('search_pool')=='creation_only' and cfg.get('day_policy')=='today_first' and not cfg.get('paused')
assert runtime.read(studio.capture_root('plan-fbb1750d49ea45cb8d3a490b44a19e32')/'settings.json').get('paused_day')==day
captures={}
for model in plan['channels']:
 rows=[json.loads(s) for s in (studio.capture_root(pid)/'days'/day/model/'results.jsonl').read_text().splitlines() if s.strip()]
 assert len(rows)==8 and {r['question'] for r in rows}==set(plan['questions'])
 assert all(r.get('body_capture_complete') is True and r.get('source_capture_complete') is True for r in rows)
 captures[model]=len(rows)
for path in (runtime.BASE/'runs').glob('*/control.json'):
 assert runtime.read(path).get('reason')!='brow_scope_maintenance',str(path)
with sqlite3.connect('file:/home/user/geo-editorial/runtime-api/api/costs.sqlite?mode=ro',uri=True) as db:
 cost=db.execute('select count(*),coalesce(sum(c.charged),0),sum(case when c.charged is null then 1 else 0 end) from costs c join studio_cost_scopes s on s.id=c.id where s.scope=?',(pid,)).fetchone()
 per=db.execute('select c.category,c.article,sum(c.charged) from costs c join studio_cost_scopes s on s.id=c.id where s.scope=? group by c.category,c.article',(pid,)).fetchall()
assert not cost[2] and cost[1]<=5.25 and max(r[2] for r in per)<=.35
sql="select count(*) from monitor_ingest_events where record->>'batch_id' in ('creation-material-"+day+"-baidu_ai','creation-material-"+day+"-wenxin_card');"
count=int(subprocess.check_output(['docker','exec','monitor-postgres','psql','-U','monitor_app','-d','monitor','-At','-c',sql],text=True).strip());assert count==0
services={}
for service in ('geo-creation-studio.service','geo-content-worker.service','geo-content-api.service'):
 active=subprocess.check_output(['systemctl','is-active',service],text=True).strip();enabled=subprocess.check_output(['systemctl','is-enabled',service],text=True).strip();assert active=='active' and enabled=='enabled';services[service]={'active':active,'enabled':enabled}
tomorrow=(date.fromisoformat(day)+timedelta(days=1)).isoformat();assert studio.scheduled_day(plan,tomorrow)==tomorrow
out={'at':time.time(),'task':{k:task[k] for k in ('plan_id','date','status','articles','article_target','writing_complete','writing_jobs','capture_time','writing_time','article_budget_cny','task_budget_cny')},'cost_calls':cost[0],'cost_cny':cost[1],'max_article_cost_cny':max(r[2] for r in per),'unsettled_calls':cost[2],'geo_ingest_rows_for_creation_batches':count,'tomorrow':studio.scheduled_day(plan,tomorrow),'captures':captures,'services':services,'scope':'creation_only','limits_unchanged':True}
Path('/tmp/brow-e2e-final.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out,ensure_ascii=False))
