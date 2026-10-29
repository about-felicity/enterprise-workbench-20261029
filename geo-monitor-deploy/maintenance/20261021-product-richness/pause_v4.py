import sys,json
from pathlib import Path
sys.path.insert(0,'/opt/monitor/geo-content/engine')
from geo_source_cards.pipeline_control import pause,state
r=Path('/opt/monitor/geo-content/runtime/runs/creation-1792556219-bbc55e13');m=Path('/opt/monitor/geo-capture/maintenance/20261021-product-richness/maintenance-v4-pause.json')
if m.exists():print('Maintenance pause already recorded');raise SystemExit(0)
c=state(r)
if c.get('paused'):print(json.dumps({'existing_pause':c},ensure_ascii=False));raise SystemExit(2)
p=pause(r,'document_projection_maintenance','等待正在执行的请求安全收尾，修正三级标题与结构化段落兼容；不发送新请求')
m.write_text(json.dumps(p));print(json.dumps(p,ensure_ascii=False))
