import sys,json,sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
now=datetime.now(ZoneInfo('Asia/Shanghai'));s=runtime.pipeline_control.settings(runtime.SHARED)
with sqlite3.connect('file:/home/user/geo-editorial/runtime-api/api/costs.sqlite?mode=ro',uri=True) as db:
 values=db.execute('select coalesce(sum(charged),0),coalesce(sum(case when charged is null then reserved else 0 end),0) from costs where date=?',(now.date().isoformat(),)).fetchone()
print(json.dumps({'time':now.isoformat(),'daily_cap':s['daily_budget_cny'],'article_cap':s['article_budget_cny'],'charged':values[0],'reserved':values[1],'remaining':s['daily_budget_cny']-sum(values),'studio_services':runtime.read('/opt/monitor/geo-content/studio/health.json')},ensure_ascii=False))
