import json
from pathlib import Path
def read(p):
 try:return json.loads(p.read_text())
 except (FileNotFoundError,ValueError):return {}
base=Path('/opt/monitor/geo-content/studio')
for p in sorted((base/'plans').glob('*.json')):
 v=read(p)
 if v.get('deleted_at') or 'wenxin_card' not in v.get('channels',[]):continue
 root=base/'capture'/v['plan_id'];h=read(root/'health.json');day=h.get('day','')
 recovery=read(root/'days'/day/'wenxin_card/collector/search_recovery.json')
 block=read(root/'days'/day/'blocked-wenxin_card.json')
 print(json.dumps({'name':v.get('name'),'day':day,'status':h.get('status'),'wenxin_active':'wenxin_card' in h.get('active_channels',[]),'blocked':bool(block or recovery.get('blocked'))},ensure_ascii=False))
rows=[]
for p in Path('/opt/monitor/geo-capture/batches').glob('*/manifest.json'):
 v=read(p)
 if v.get('model')=='wenxin_card':rows.append((v.get('created_at',0),p.parent))
for _,p in sorted(rows)[-1:]:
 h=read(p/'bridge_health.json');print(json.dumps({'main_geo_latest':p.name,'status':h.get('status'),'tasks':h.get('tasks')}))
