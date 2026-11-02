import subprocess
code=r'''
import json,time
from pathlib import Path
from monitor_core import analytics as a,database as db
from monitor_core.employee_assessment import build_assessment,_mention_summary,load_config
from monitor_core.performance import daily_employee_performance,_actual_rate,OCTOBER_WEIGHTS
start=time.monotonic()
runs=db.load_owned_product_runs(day_from='2026-10-01',day_to='2026-10-31')
daily=a.daily_owned_product_recommendations(runs,['deepseek','doubao','wenxin','yuanbao'],day_limit=3660)
func=a.owned_product_recommendation_summary
board=func(daily,['deepseek','doubao','wenxin','yuanbao'],month='2026-10')
old=daily_employee_performance(board,date='2026-10')
new=build_assessment(daily,month='2026-10',as_of='2026-10-31')
lookup={(r['question'],r['product']):r for r in board};derived=_mention_summary(daily);deltas=[]
for r in derived:
 other=lookup.get((r['question'],r['product']))
 if not other:continue
 for model in ['deepseek','doubao','wenxin','yuanbao']:
  x=_actual_rate(r,model);y=_actual_rate(other,model)
  if x is not None and y is not None and abs(x-y)>.001:deltas.append({'product':r['product'],'model':model,'current_rate':round(x,5),'board_rate':y})
summary=[]
for person in new['people']:
 prior=next(p for p in old['people'] if p['name']==person['name'])
 summary.append({'name':person['name'],'current_score':person['current']['scores']['mention'],'previous_module_score':prior['score'],'previous_weights':OCTOBER_WEIGHTS[person['name']],'current_weights':load_config('2026-10')['model_weights'],'previous_products':prior['assigned_products'],'current_products':person['product_count']})
report={'seconds':round(time.monotonic()-start,2),'people':summary,'actual_rate_differences':deltas}
Path('/app/maintenance/performance-entry-20261031/mention-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False))
'''
r=subprocess.run(['docker','exec','-w','/app','monitor-dashboard-api','python','-B','-c',code],capture_output=True,text=True,timeout=180)
print(r.stdout)
if r.returncode:raise RuntimeError(r.stderr[-1800:])
