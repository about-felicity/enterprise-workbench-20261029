import json,sys
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
from geo_source_cards.pipeline_control import pause
t=runtime.read(Path('/opt/monitor/geo-capture/maintenance/20261020-brow-daily/task.json'))
jobs=[p.parent for p in (runtime.BASE/'runs').glob('*/job.json') if runtime.read(p).get('studio_plan_id')==t['plan_id']]
assert len(jobs)==1
r=jobs[0];pause(r,'source_quality_review','来源主题或体裁不匹配，当前请求安全收尾后核对素材；保留原文、费用和回执')
print(json.dumps({'job':r.name,'control':runtime.read(r/'control.json'),'active':runtime.read(r/'api/active.json')},ensure_ascii=False))
