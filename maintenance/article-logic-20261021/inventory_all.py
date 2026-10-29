"""Inventory current approved articles and other generated drafts without sends."""
import sys,json,hashlib,time
from pathlib import Path
from collections import Counter
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime,quality_repair as q,observation as o
from geo_source_cards.staged_editorial import research_for_writer
from geo_source_cards.runtime import atomic_json
OUT=Path('/opt/monitor/geo-capture/maintenance/20261021-all-logic');OUT.mkdir(parents=True,exist_ok=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
roots=[runtime.SHARED]+[p.parent for p in sorted((runtime.BASE/'runs').glob('*/job.json'))]
rows=[];drafts=[];seen=set()
for root in roots:
 for folder in sorted((root/'approved').glob('*/*/*')):
  if not (folder/'draft.md').is_file():continue
  day,category,num=folder.relative_to(root/'approved').parts
  row={'key':hashlib.sha256((str(root)+'/'+str(folder.relative_to(root/'approved'))).encode()).hexdigest()[:24],'root':str(root),'id':str(folder.relative_to(root/'approved')),'date':day,'category':category,'number':int(num),'folder':str(folder),'title':(folder/'draft.md').read_text('utf-8-sig').splitlines()[0],'draft_sha256':sha(folder/'draft.md'),'word_sha256':sha(folder/'article.docx') if (folder/'article.docx').exists() else None}
  writer=None
  try:writer=q.writer_for(root,day,category,int(num))
  except (ValueError,KeyError):pass
  matches=[p.parent for p in (root/'days'/day).glob('**/writer/draft.md') if sha(p)==row['draft_sha256']]
  if matches:writer=matches[0]
  row['writer']=str(writer) if writer else None
  product=folder/'logic_product.json' if (folder/'logic_product.json').exists() else writer/'product.json' if writer and (writer/'product.json').exists() else root/'days'/day/'product.json'
  knowledge=writer/'knowledge.json' if writer else root/'days'/day/'knowledge.json'
  row.update(product_path=str(product) if product.exists() else None,knowledge_path=str(knowledge) if knowledge.exists() else None)
  row['receipt_present']=(folder/'receipt.json').is_file();rows.append(row);seen.add((str(root),row['draft_sha256']))
 for p in sorted((root/'days').glob('**/writer/draft.md')):
  digest=sha(p)
  if (str(root),digest) in seen:continue
  seen.add((str(root),digest));category=runtime.read(p.with_name('category.json'))
  drafts.append({'key':hashlib.sha256(str(p).encode()).hexdigest()[:24],'root':str(root),'path':str(p),'date':p.relative_to(root/'days').parts[0],'category':category.get('label'),'number':category.get('number'),'title':p.read_text('utf-8-sig').splitlines()[0],'draft_sha256':digest,'product_path':str(p.with_name('product.json')) if p.with_name('product.json').exists() else None,'knowledge_path':str(p.with_name('knowledge.json')) if p.with_name('knowledge.json').exists() else None})
value={'at':time.time(),'approved_versions':rows,'non_current_drafts':drafts,'roots':list(map(str,roots))}
atomic_json(OUT/'inventory.json',value)
print(json.dumps({'current_article_versions':len(rows),'other_saved_drafts':len(drafts),'roots':len(roots),'missing_product':sum(not r['product_path'] for r in rows),'missing_knowledge':sum(not r['knowledge_path'] for r in rows),'by_date':dict(Counter(r['date'] for r in rows)),'logic_versions':dict(Counter(runtime.read(Path(r['folder'])/'logic_review.json').get('version','missing') for r in rows))},ensure_ascii=False))
