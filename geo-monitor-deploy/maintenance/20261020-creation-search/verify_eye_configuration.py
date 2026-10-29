import json,sys,time,urllib.request
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import studio,runtime
pid='plan-c32eb3793b6846e39f72cb25f9e06d1c'
p=studio.plan(pid);root=studio.capture_root(pid);cfg=runtime.read(root/'settings.json')
assert p['enabled'] and p['frequency']=='daily' and p['article_target']==15
assert p['capture_time']=='01:00' and p['writing_time']=='04:00'
assert p['channels']==['baidu_ai','wenxin_card'] and len(p['questions'])==7
assert cfg['search_pool']=='creation_only' and cfg['day_policy']=='today_first'
assert studio.scheduled_day(p,'2026-10-21')=='2026-10-21'
assert runtime.read(studio.capture_root('plan-fbb1750d49ea45cb8d3a490b44a19e32')/'settings.json').get('paused_day')=='2026-10-20'
data=json.load(urllib.request.urlopen('http://127.0.0.1:8804/api/status',timeout=15))
task=next(t for t in data['studio']['daily_tasks'] if t['plan_id']==pid and t['date']=='2026-10-20')
assert task['article_target']==15
out={'at':time.time(),'plan_id':pid,'api_daily_task':{k:task[k] for k in ('date','status','article_target','error','articles')},'tomorrow_scheduled_day':studio.scheduled_day(p,'2026-10-21'),'main_geo_time':runtime.read(Path('/opt/monitor/geo-capture/daily_plan.json')).get('time'),'dedicated_scope':cfg['search_pool']}
Path('/tmp/eye-configuration-verification.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
print(json.dumps(out,ensure_ascii=False))
