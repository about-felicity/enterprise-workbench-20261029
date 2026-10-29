"""Compile frozen real samples and export synthetic golden contracts, no API."""
import sys,json,time
from pathlib import Path
D=Path('/opt/monitor/geo-capture/maintenance/20261022-content-compiler');S=D/'stage-v2'
sys.path[:0]=[str(S),str(S/'engine')]
from geo_source_cards.article_compiler import compile_article
from geo_source_cards.consumer_prompts import evidence_units
from geo_source_cards.repair_router import route
from geo_source_cards.runtime import atomic_json
from geo_source_cards.editorial_schema import SCHEMAS
from tests.test_article_compiler import case
read=lambda p:json.loads(p.read_text('utf8')) if p.is_file() else {}
rows=[]
for identity in ('creation-1792575159-0a8f9221','creation-1792576129-389f575e'):
 root=Path('/opt/monitor/geo-content/runtime/runs')/identity
 for writer in sorted((root/'days/2026-10-21/jobs').glob('*/*/writer')):
  k,p=read(writer/'knowledge.json'),read(writer/'product.json');source=evidence_units(writer)
  c=compile_article(k,p,source);f=c['feasibility'];category=writer.parent.parent.name;number=int(writer.parent.name)
  output=D/'real-preflight'/identity/category/f'{number:02d}';output.mkdir(parents=True,exist_ok=True)
  atomic_json(output/'compilation.json',c)
  text=(writer/'draft.md').read_text('utf8') if (writer/'draft.md').is_file() else ''
  routing=route(text,k,p,read(writer.parent/'review/result.json'),feasibility=f) if text else {}
  atomic_json(output/'repair_route.json',routing)
  rows.append({'job':identity,'category':category,'number':number,'status':f['status'],'reasons':f['reasons'],
      'requested_type':f['requested_type'],'dimensions':list(f['available_dimensions']),'facts':len(c['evidence']),
      'repair_action':routing.get('action'),'compiler_sha256':c['sha256']})
golden=[]
for name,genre,title in [('A','ranking','三款产品信息排行参考'),('B','ranking','三款产品效果排行榜'),('C','review','三款产品资料测评'),('D','science','规格与成分信息怎么选'),('E','review','三款产品资料测评')]:
 k,p=case(genre=genre,title=title)
 if name=='E':p['facts'].append({'approved':True,'text':'规格500ml。'})
 c=compile_article(k,p);atomic_json(D/'golden'/f'{name}.json',{'synthetic':True,'knowledge':k,'product':p,'compilation':c})
 golden.append({'case':name,'synthetic':True,'status':c['feasibility']['status']})
atomic_json(D/'schemas.json',SCHEMAS)
out={'at':time.time(),'new_paid_calls':0,'real_articles':rows,'golden':golden,'article_acceptance_verified':False}
atomic_json(D/'preflight-results.json',out);(D/'preflight-results.json').chmod(0o644)
print(json.dumps(out,ensure_ascii=False))
