import hashlib,json,sys,subprocess
from datetime import date,timedelta
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime,studio,materials
t=runtime.read(Path('/opt/monitor/geo-capture/maintenance/20261020-brow-daily/task.json'));pid=t['plan_id'];p=studio.plan(pid)
root=studio.capture_root(pid);cfg=runtime.read(root/'settings.json')
assert p['enabled'] and p['frequency']=='daily' and len(p['questions'])==8 and p['rounds']==1
assert p['article_target']==15 and p['article_budget_cny']==.35 and p['task_budget_cny']==5.25
assert p['capture_time']=='01:00' and p['writing_time']=='04:00' and p['channels']==['baidu_ai','wenxin_card']
assert cfg['search_pool']=='creation_only' and cfg['day_policy']=='today_first' and not cfg.get('paused')
assert runtime.read(Path('/opt/monitor/geo-capture/daily_plan.json'))['time']=='09:00'
assert hashlib.sha256((studio.ROOT/'imports'/t['import_id']/'source.docx').read_bytes()).hexdigest()==t['sha256']
tomorrow=(date.fromisoformat(t['start_date'])+timedelta(days=1)).isoformat()
assert studio.scheduled_day(p,tomorrow)==tomorrow
private=[]
for f in (root/'days'/t['start_date']).glob('*/results.jsonl'):
    rows=[json.loads(s) for s in f.read_text().splitlines() if s.strip()]
    private.append({'model':f.parent.name,'observations':len(rows),'questions':len(set(r.get('question') for r in rows)),'sources':sum(len(r.get('sources',[])) for r in rows)})
services={s:subprocess.check_output(['systemctl','is-active',s],text=True).strip() for s in ['geo-creation-studio.service','geo-content-worker.service','geo-content-api.service']}
assert set(services.values())=={'active'}
out={'plan_id':pid,'configuration_valid':True,'tomorrow':tomorrow,'main_geo_time':'09:00','private_observations':private,'services':services,'source_unchanged':True}
Path('/tmp/brow-configuration.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out,ensure_ascii=False))
