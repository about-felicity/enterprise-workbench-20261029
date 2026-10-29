"""Export inspectable source/skeleton/material evidence without approving anything."""
import json,sys,shutil
from pathlib import Path
BASE=Path(__file__).resolve().parent
sys.path[:0]=[str(BASE/'engine'),str(BASE)]
from geo_source_cards.runtime import atomic_json,atomic_write
from geo_source_cards.rewrite_v2.common import digest
from multi_run import STATE,root_for
review=['# 三产品真实测试：新范文骨架校验','',
 '当前为待确认骨架；确认前不生成全文。采集与素材整理可以继续。','']
checks=[]
for item in STATE['products']:
    out=BASE/'multi-results'/item['key'];root=root_for(item)
    selection=out/'selected-source.json'
    if not selection.exists():continue
    source=json.loads(selection.read_text());article=source['source']['article']
    atomic_write(out/'reference.md',article['text'])
    result=next((root/'days'/item['date']/'jobs').glob('*/01/research/research_result.json'),None)
    if not result:continue
    parsed=json.loads(result.read_text());cache=BASE/'multi-runtime/cache/skeleton'/(parsed['skeleton']['cache_key']+'.json')
    skeleton=json.loads(cache.read_text());atomic_json(out/'skeleton-review.json',skeleton)
    proposal=out/'proposed-skeleton.json'
    proposed=json.loads(proposal.read_text()) if proposal.exists() else skeleton['skeleton']
    displayed={**skeleton,'skeleton':proposed}
    product=json.loads((root/'product.json').read_text())
    review += ['## '+product['name'],'','范文：'+article['title'],'',source['source']['url'],'',
               '体裁：'+skeleton['skeleton']['article_type'],'','段落顺序与功能：','']
    review += [str(i)+'. '+v for i,v in enumerate(proposed['article_structure'],1)]
    review += ['','节奏：'+skeleton['skeleton']['writing_rhythm'],'','风格特征：','']
    review += ['- '+v for v in proposed['special_style_elements']]
    review += ['','生成约束：原产品数字、亲测经历、评分及绝对化结论不直接搬用；自有产品数据仅来自对应完整知识库，保留测试条件。原文不作为竞品功效的独立核验。','',
               '缓存键：`'+skeleton['cache_key']+'`；待确认版本：`'+skeleton['sha256']+'`。','']
    checks.append({'key':item['key'],'cache_key':skeleton['cache_key'],'expected_sha256':skeleton['sha256'],
                   'source_url':source['source']['url'],'product_sha256':digest(product),'proposal_sha256':digest(proposed),'approved':bool(skeleton.get('approval'))})
atomic_write(BASE/'multi-results'/'骨架校验.md','\n'.join(review))
atomic_json(BASE/'multi-results'/'review-manifest.json',checks)
print(json.dumps(checks,ensure_ascii=False))
