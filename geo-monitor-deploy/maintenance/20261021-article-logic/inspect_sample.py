"""Read-only lookup of the user-reported article and its frozen evidence."""
import json,sys,shutil,zipfile,hashlib
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
from creation.quality_repair import writer_for
from geo_source_cards.staged_editorial import research_for_writer
needle='读懂贴片面膜的配方表';out=Path('/tmp/geo-article-logic');out.mkdir(exist_ok=True);matches=[]
roots=[runtime.SHARED]+[p.parent for p in (runtime.BASE/'runs').glob('*/job.json')]
for root in roots:
 for draft in (root/'approved').glob('*/*/*/draft.md'):
  text=draft.read_text('utf-8-sig')
  if needle not in text:continue
  folder=draft.parent;day,category,number=folder.relative_to(root/'approved').parts
  writer=writer_for(root,day,category,int(number));research=research_for_writer(writer)
  match={'root':str(root),'id':str(folder.relative_to(root/'approved')),'writer':str(writer),'research':str(research),'draft_sha256':hashlib.sha256(draft.read_bytes()).hexdigest(),'word_sha256':runtime.read(folder/'receipt.json').get('word_sha256')}
  matches.append(match)
  with zipfile.ZipFile(out/'sample.zip','w',zipfile.ZIP_DEFLATED) as z:
   for name in ('job.json','control.json'):
    p=root/name
    if p.exists():z.write(p,'job/'+name)
   for label,path in [('approved',folder),('writer',writer),('research',research)]:
    for name in ('draft.md','knowledge.json','product.json','category.json','provenance.json','semantic_review.json','receipt.json','claim_map.json','knowledge_to_sections.json','research_result.json','research_input.json','writing_job.json','writer_done.json','product_detail_review.json'):
     p=path/name
     if p.exists():z.write(p,label+'/'+name)
   z.writestr('match.json',json.dumps(match,ensure_ascii=False,indent=2))
report={'matches':matches};(out/'lookup.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print(json.dumps(report,ensure_ascii=False))
