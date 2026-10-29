import sys,json
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime,studio,materials
m=Path('/opt/monitor/geo-capture/maintenance/20261021-daohe-test');s=runtime.read(m/'task.json');r=Path(s['capture_root']);task=runtime.read(studio.day_path(s['plan_id'],s['date']))
print(json.dumps({'capture':materials.progress(s['date'],store_root=r),'health':runtime.read(r/'health.json'),'task':{k:v for k,v in task.items() if k not in {'plan'}},'capture_config_exists':(r/'days'/s['date']/'config.json').exists()},ensure_ascii=False))
