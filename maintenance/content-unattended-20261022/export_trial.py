"""Export only yesterday's article evidence for local regression, no execution."""
import json,tarfile,time,sqlite3,hashlib
from pathlib import Path
B=Path('/opt/monitor/geo-content/runtime/runs')
ids=['creation-1792575159-0a8f9221','creation-1792576129-389f575e']
names={'knowledge.json','product.json','writing_job.json','category.json','draft.md','claim_map.json','knowledge_to_sections.json','draft_review.json','result.json','research_result.json','research_input.json','stage_job.json'}
out=Path('/tmp/content-trial-evidence22.tar.gz');summary=[]
with tarfile.open(out,'w:gz') as tar:
 for identity in ids:
  root=B/identity
  for path in (root/'days/2026-10-21/jobs').rglob('*'):
   if path.is_file() and path.name in names and path.parent.name in {'writer','review','research'}:
    tar.add(path,arcname=identity+'/'+path.relative_to(root).as_posix())
    if path.name=='knowledge.json':
     value=json.loads(path.read_text());summary.append({'path':str(path),'bytes':path.stat().st_size,'unit_count':len(value.get('knowledge_units',[])),'outline':value.get('outline'),'blueprint_keys':list(value.get('reference_design',{}))})
with sqlite3.connect('file:/home/user/geo-editorial/runtime-api/api/costs.sqlite?mode=ro',uri=True) as db:
 unknown=[r[0] for r in db.execute('select id from costs where charged is null')]
out.chmod(0o644)
report={'at':time.time(),'archive':str(out),'sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'articles':summary,'unknown_ids':unknown}
Path('/tmp/content-trial-evidence22.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps({**report,'articles':[{'path':s['path'],'bytes':s['bytes'],'unit_count':s['unit_count'],'blueprint_keys':s['blueprint_keys']} for s in summary]},ensure_ascii=False))
