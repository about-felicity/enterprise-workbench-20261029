"""One-time reviewed source-plan replacement; retain settled runs and raw captures."""
import json,shutil,sqlite3,sys,time
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import materials,runtime
from geo_source_cards.daily_editorial import prepare_day
root=runtime.job_root('creation-1792479954-8a96bc88').resolve()
assert root.parent==(runtime.BASE/'runs').resolve()
assert runtime.read(root/'control.json').get('reason')=='source_quality_review'
backup=root/'revisions/source-quality-v1';assert not backup.exists(),'Already repaired; inspect current state'
active=runtime.read(root/'api/active.json');assert active.get('state')=='SUBMITTED',active
for p in (root/'api').rglob('api_state.json'):
 assert runtime.read(p).get('state')=='RESPONDED',(str(p),runtime.read(p).get('state'))
for p in (root/'queue').glob('*/ticket.json'):assert runtime.read(p).get('state')!='claimed',str(p)
job=runtime.read(root/'job.json')
with sqlite3.connect('file:/home/user/geo-editorial/runtime-api/api/costs.sqlite?mode=ro',uri=True) as db:
 costs=db.execute('select count(*),coalesce(sum(c.charged),0),sum(case when c.charged is null then 1 else 0 end) from costs c join studio_cost_scopes s on s.id=c.id where s.job=?',(job['job_id'],)).fetchone()
assert costs[2]==0,costs
rows=materials.read_lines(root/'private_source_analysis/articles.jsonl');filtered,full=materials.usable_source_rows(rows);assert full>=3
backup.mkdir(parents=True)
for name in ('job.json','control.json','material_preparation.json'):
 if (root/name).exists():shutil.copy2(root/name,backup/name)
for name in ('days','queue','approved','api','logs','geo_articles.jsonl','geo_worker.json','health.json','geo_material_manifest.json'):
 path=root/name
 if path.exists():
  assert root in path.resolve().parents
  shutil.move(str(path),str(backup/name))
runtime.atomic_json(backup/'withdrawal.json',{'at':time.time(),'reason':'Source page chrome and comparison prose incorrectly admitted to science; replace source plan, retain all receipts and original approved test artifact','known_settled_calls':costs[0],'charged_cny_preserved':costs[1],'unknown_requests':0})
runtime.atomic_write(root/'geo_articles.jsonl',''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in filtered))
prepared=prepare_day(root,root/'geo_articles.jsonl',root/'product.json',job['date'],max_per_category=max(job['max_per_category'],job['article_target']))
job.update(preparation='ready',prepared=prepared,material_counts={'geo_observations':0,'private_observations':len(rows),'full_articles':full},source_quality_revision='page-chrome-v1')
runtime.atomic_json(root/'job.json',job)
runtime.atomic_json(root/'material_preparation.json',{'at':time.time(),'phase':'ready','full_article_records':full,'source_quality_revision':'page-chrome-v1'})
runtime.resume(root)
print(json.dumps({'job_id':job['job_id'],'raw_observations':len(rows),'usable_article_records':full,'archive':str(backup),'preserved_cost_cny':costs[1],'same_daily_task':True},ensure_ascii=False))
