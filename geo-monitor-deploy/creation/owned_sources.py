"""Exclude owned references using the live GEO ownership matcher, before writing."""
import os,sys,json
from pathlib import Path
from functools import lru_cache
from geo_source_cards.runtime import atomic_json

@lru_cache(maxsize=1)
def matcher():
    base=Path(os.environ.get('GEO_ANALYSIS_SOURCE_ROOT','/opt/monitor'))
    if not (base/'monitor_core/analytics.py').is_file():
        base=Path(__file__).resolve().parents[1]/'server-source'
    if not (base/'monitor_core/analytics.py').is_file():
        raise ValueError('自有信源识别服务不可用，暂停仿写以免使用自己的文章')
    sys.path.insert(0,str(base))
    # Article fetching can import the lightweight installed monitor_core first.
    # Updating sys.path alone cannot extend that already-loaded package's path.
    # Keep its loaded browser helper, but resolve analytics from the live GEO tree.
    import monitor_core
    package_root=str(base/'monitor_core')
    monitor_core.__path__=[package_root,*[p for p in monitor_core.__path__ if p!=package_root]]
    from monitor_core.analytics import owned_source_title_metadata
    return owned_source_title_metadata

def ownership(source):
    article=source.get('article') or {}
    title='\n'.join(str(v or '') for v in (source.get('title'),article.get('title')))
    body=str(article.get('text') or '')
    labels=matcher()(title+'\n'+body,str(article.get('final_url') or source.get('url') or ''))
    brands=set(labels.get('owned_brands') or [])|set(source.get('owned_brands') or [])
    products=set(labels.get('own_products') or [])|set(source.get('own_products') or [])
    # Supplement the GEO catalog with newly imported product names/brands.
    from monitor_core.analytics import brand_alias_occurs
    library=Path(os.environ.get('GEO_CREATION_STUDIO_ROOT','/opt/monitor/geo-content/studio'))/'products'
    for path in library.glob('*.json'):
        data=json.loads(path.read_text(encoding='utf-8-sig'))
        product=data.get('product') or data
        for key,target in [('name',products),('brand',brands)]:
            value=product.get(key)
            if isinstance(value,str) and len(value.strip())>=2 and brand_alias_occurs(title+'\n'+body,value):target.add(value)
    return {'owned':bool(source.get('own_brand') or brands or products),'brands':sorted(brands),'products':sorted(products)}

def exclude_owned(rows,root=None):
    kept=[];excluded=[]
    for row in rows:
        sources=[]
        for source in row.get('sources',[]):
            labels=ownership(source)
            if labels['owned']:
                excluded.append({'url':source.get('url'),'title':source.get('title'),'reason':'owned_product_or_brand_mentioned',**labels})
            else:sources.append(source)
        if sources:kept.append({**row,'sources':sources})
    if root is not None:
        atomic_json(Path(root)/'owned_source_exclusions.json',{'policy':'exclude-any-owned-mention-v1','excluded_count':len(excluded),'sources':excluded})
    return kept,excluded

def guard_prepared(root):
    """Old prepared jobs must not bypass the newly enabled exclusion policy."""
    path=Path(root)/'geo_articles.jsonl'
    if not path.is_file():return
    rows=[json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    _,excluded=exclude_owned(rows)
    if excluded:
        atomic_json(Path(root)/'owned_source_guard.json',{'blocked':True,'sources':excluded})
        raise ValueError('已停止仿写：现有任务素材含'+str(len(excluded))+'条自有产品信源，需排除后重新准备素材')
