import json,sys
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
from geo_source_cards.pipeline_control import pause
target=Path('/opt/monitor/geo-capture/maintenance/20261020-brow-daily/maintenance-controls.json')
if target.exists():raise SystemExit('Maintenance boundaries already recorded; inspect existing records')
saved=[]
for p in (runtime.BASE/'runs').glob('*/job.json'):
    r=p.parent;j=runtime.read(p);before=runtime.read(r/'control.json')
    if before.get('paused') or runtime.read(r/'days'/j['date']/'day.json').get('status')=='complete':continue
    after=pause(r,'brow_scope_maintenance','创作筛选规则更新：当前已发送请求安全收尾，部署后继续，保留原进度')
    saved.append({'job_id':j['job_id'],'before':before,'maintenance_revision':after['revision']})
runtime.atomic_json(target,{'jobs':saved})
print(json.dumps({'maintenance_jobs':[r['job_id'] for r in saved]},ensure_ascii=False))
