import json, sqlite3, subprocess
from pathlib import Path

def read(p):
    p=Path(p)
    return json.loads(p.read_text()) if p.exists() else {}

geo=Path('/opt/monitor/geo-capture')
content=Path('/opt/monitor/geo-content')
for name in ('creation_search_pool.json','materials/settings.json','materials/health.json','studio/health.json','runtime/worker_health.json'):
    v=read(content/name)
    print(name,json.dumps({k:v[k] for k in v if k not in {'product','studio_plan','questions'}},ensure_ascii=False))
print('daily_plan', {k:v for k,v in read(geo/'daily_plan.json').items() if k not in {'questions','products'}})
for path in (content/'studio/plans').glob('*.json'):
    p=read(path)
    print('plan',{k:p.get(k) for k in ('plan_id','name','enabled','channels','frequency','start_date')})
print(subprocess.run(['systemctl','list-units','--type=service','--state=running','--no-pager','--no-legend'],capture_output=True,text=True).stdout)
with sqlite3.connect((Path('/home/user/geo-editorial/runtime-api/api/costs.sqlite')).as_uri()+'?mode=ro',uri=True) as db:
    print('recent_cost',db.execute('select date,sum(coalesce(charged,reserved)) from costs group by date order by date desc limit 2').fetchall())
print('budget_settings', read('/home/user/geo-editorial/runtime-api/settings.json'))
for model in ('baidu_ai','wenxin_card'):
    p=geo/'profiles/search'/model
    print('profile',model, read(p/'migration.json'))
