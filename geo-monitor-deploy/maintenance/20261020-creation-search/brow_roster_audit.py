import json,sys
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
from geo_source_cards.reference_design import clean_roster
from geo_source_cards.genre_pools import classify_source
t=runtime.read(Path('/opt/monitor/geo-capture/maintenance/20261020-brow-daily/task.json'));out=[]
for f in (runtime.BASE/'runs').glob('*/job.json'):
 j=runtime.read(f)
 if j.get('studio_plan_id')!=t['plan_id']:continue
 r=f.parent;day=r/'days'/j['date'];sources={s['url']:s for s in runtime.read(day/'media_articles.json',[])}
 for p in sorted((day/'jobs'/'排行类').glob('*/research/research_input.json')):
  b=clean_roster(runtime.read(p)['reference_design']);s=sources[b['primary_url']];c=classify_source(s)
  out.append({'number':p.parents[1].name,'names':[b['owned_product']['name']]+[p['name'] for p in b['products']],'source_declared':c['declared_product_count'],'status':c['status']})
assert len(out)==14 and all(r['status']=='ready' for r in out)
Path('/tmp/brow-roster-audit.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out,ensure_ascii=False))
