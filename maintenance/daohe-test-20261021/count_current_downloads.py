import sys,json
from pathlib import Path
from collections import Counter
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
rows=[]
for root in [runtime.SHARED]+[p.parent for p in (runtime.BASE/'runs').glob('*/job.json')]:
 if runtime.read(root/'job.json').get('studio_plan_id')=='plan-33e7bfca8bb6497da10b28f0444a693b':continue
 rows += [{**a,'root':str(root)} for a in runtime.articles(root)]
value={'previous_delivery_versions':len(rows),'quality_status':dict(Counter(r['quality_status'] for r in rows)),'ready':[{'root':a['root'],'id':a['id'],'title':a['title']} for a in rows if a['quality_status']=='ready']}
runtime.atomic_json(Path('/opt/monitor/geo-capture/maintenance/20261021-daohe-test/current-download-counts.json'),value);print(json.dumps(value,ensure_ascii=False))
