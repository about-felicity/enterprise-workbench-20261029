import json,sys,sqlite3,subprocess,time
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
sys.path[:0]=['/opt/monitor/geo-capture','/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from daily_tasks import database_counts
B=Path('/opt/monitor/geo-capture');day=datetime.now(ZoneInfo('Asia/Shanghai')).date().isoformat()
def read(p):
 try:return json.loads(Path(p).read_text('utf-8-sig'))
 except FileNotFoundError:return {}
p=read(B/'daily_plan.json');out={'at':datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'daily_plan':{k:p.get(k) for k in ['enabled','time','timezone','models','daily_control_enabled']}}
counts=database_counts(day);db=sqlite3.connect('file:'+str(B/'panel/control.sqlite')+'?mode=ro',uri=True);db.row_factory=sqlite3.Row;rows=[]
for r in db.execute('select * from daily_tasks where day=?',(day,)):
 v=dict(r);cfg=json.loads(v['config']);qs=cfg.get('questions',[]);n=cfg.get('rounds',0);c=counts.get(v['model'],{})
 rows.append({'model':v['model'],'status':v['status'],'desired':v['desired'],'batch':v['batch'],'questions':len(qs),'rounds':n,'interval':cfg.get('interval'),'target':len(qs)*n,'credited_pg':sum(min(c.get(q,0),n) for q in qs),'error':v.get('error')})
db.close();out['daily_snapshot']=rows
services=['geo-daily-dispatch.timer','geo-daily-control','geo-creation-studio','geo-content-worker','geo-content-api','geo-deepseek-public-ingest','geo-deepseek-upload-tunnel','geo-deepseek-browser-test','geo-deepseek-browser-receiver']
out['services']={n:subprocess.run(['systemctl','is-active',n],text=True,capture_output=True).stdout.strip() for n in services}
out['next_daily_timer']=subprocess.run(['systemctl','show','geo-daily-dispatch.timer','--property=NextElapseUSecRealtime','--value'],text=True,capture_output=True).stdout.strip()
backend=read(B/'deepseek_backend.json');out['deepseek_backend']={k:v for k,v in backend.items() if k in ['backend','mode','enabled','model','models','channels','default']}
R=Path('/opt/monitor/geo-content');plans=[]
for f in (R/'studio/plans').glob('*.json'):
 v=read(f);plans.append({k:v.get(k) for k in ['plan_id','name','enabled','capture_time','writing_time','frequency','article_target','article_budget_cny','task_budget_cny','genre_targets']})
out['creation_plans']=plans
m=Path('/opt/monitor/geo-capture/maintenance/20261021-product-richness');q=read(m/'final-qa.json');out['mask_test']={k:q.get(k) for k in ['at','count','categories','budget_actual_cny','maximum_article_cny','export_sha256','export_bytes']}
d=read(R/'runtime/runs/creation-1792556219-bbc55e13/days/2026-10-21/day.json');out['mask_day_status']=d.get('status')
out['read_only']=True
Path('/tmp/project-handoff-live-20261021.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out,ensure_ascii=False))
