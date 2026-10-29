import sys,json
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
root=runtime.job_root('creation-1792575159-0a8f9221');day=root/'days/2026-10-21'
t=runtime.read(day/'taxonomy/result.json');a=t.get('assignments',[])
selection=runtime.read(day/'article_allocation.json');chosen={u for urls in selection['selected'].values() for u in urls}
sources=runtime.read(day/'sources.json',[])
if not sources:sources=runtime.read(day/'media_articles.json',[])
index={s['url']:s for s in sources}
result=[{**{k:r.get(k) for k in ('url','title','genre','status','reason','declared_product_count','products_without_neutral_details','article_type')},'products':[p.get('name') for p in r.get('products',[])],'body':index.get(r['url'],{}).get('article',{}).get('text','')} for r in a if r['status']=='ready' and r['url'] not in chosen]
(Path('/opt/monitor/geo-capture/maintenance/20261021-daohe-test')/'unselected-ready.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps([{k:v for k,v in r.items() if k not in {'body','products'}} for r in result],ensure_ascii=False))
