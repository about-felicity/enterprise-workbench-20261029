import json,sys,tempfile
from pathlib import Path
sys.path[:0]=['/tmp/eye-daily-qa','/tmp/eye-daily-qa/engine']
from creation import materials,runtime
from geo_source_cards import daily_editorial,genre_pools
source=Path('/opt/monitor/geo-content/runtime/runs/creation-1792479954-8a96bc88')
job=runtime.read(source/'job.json');rows=materials.read_lines(source/'private_source_analysis/articles.jsonl')
filtered,full=materials.usable_source_rows(rows)
with tempfile.TemporaryDirectory(prefix='eye-source-quality-') as folder:
 root=Path(folder);runtime.atomic_json(root/'product.json',runtime.read(source/'product.json'));runtime.atomic_json(root/'article_goal.json',{'target':job['article_target'],'prefer_genres':['排行类','科普类']})
 runtime.atomic_write(root/'articles.jsonl',''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in filtered))
 daily_editorial.prepare_day(root,root/'articles.jsonl',root/'product.json',job['date'],max_per_category=job['article_target'])
 day=root/'days'/job['date'];sources=runtime.read(day/'media_articles.json');taxonomy=genre_pools.classify(sources,limit=job['article_target']);runtime.atomic_json(day/'taxonomy/result.json',taxonomy)
 daily_editorial.start_research(root,day)
 allocation=runtime.read(day/'article_allocation.json');titles={s['url']:s['article']['title'] for s in sources}
 out={'full_article_records':full,'media_sources':len(sources),'state':runtime.read(day/'day.json'),'allocation_counts':{k:len(v) for k,v in allocation['selected'].items()},'selected_titles':{k:[titles[u] for u in v] for k,v in allocation['selected'].items()}}
 Path('/tmp/eye-repair-preview.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out,ensure_ascii=False))
