"""A specific Codex editorial revision, independently reviewed under original cap."""
import json,shutil,sys,time
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
from creation.client import CreationClient
from geo_source_cards.staged_editorial import research_for_writer,check
from geo_source_cards.runtime import atomic_write,atomic_json
from geo_source_cards.word_export import export_docx
from geo_source_cards.api_prompts import build_prompt
from geo_source_cards.api_worker import materialize
from geo_source_cards.daily_editorial import finalize,file_hash
from geo_source_cards.pipeline_control import event
root=runtime.job_root('creation-1792479954-8a96bc88');day='2026-10-20';category='科普类';number=5
side=Path('/opt/monitor/geo-content/runtime/quality-repair/manual-eye-20261021');assert not side.exists(),'Already issued; inspect durable review response'
assert runtime.read(root/'control.json').get('reason')=='consumer_prompt_maintenance'
assert runtime.read(root/'api/active.json').get('state')=='SUBMITTED'
assert not (root/'approved'/day/category/'05').exists()
original=root/'days'/day/'jobs'/category/'05/writer';research=research_for_writer(original)
base=side/'days'/day/'articles'/category/'05';base.mkdir(parents=True)
shutil.copytree(original,base/'writer');shutil.copytree(research,base/'research')
atomic_json(side/'days'/day/'day.json',{'date':day,'status':'isolated_codex_editorial_revision'})
atomic_json(side/'job.json',runtime.read(root/'job.json'));shutil.copy2(runtime.SHARED/'settings.json',side/'settings.json')
writer=base/'writer';draft=Path('/tmp/eye-consumer-revised.md').read_text()
atomic_write(writer/'draft.md',draft);export_docx(draft,writer/'article.docx')
paras=[p for p in draft.split('\n\n') if p.strip() and not p.startswith('#')]
claims=[{'text':paras[0],'evidence_ids':['KU01']},{'text':next(p for p in paras if p.startswith('以姿生怡')),'evidence_ids':['PF1','PF2','PF4','PF5']}]
atomic_json(writer/'claim_map.json',{'claims':claims})
mapping=[('S1',['KU01','KU19']),('S2',['KU02','KU15']),('S3',['KU01','KU14']),('S4',['KU07','KU14']),('S6',['KU14','KU15'])]
atomic_json(writer/'knowledge_to_sections.json',{'sections':[{'section_id':s,'knowledge_ids':ids,'innovation':'直接回答消费者问题，删除来源解读与未经验证机制'} for s,ids in mapping]})
job=runtime.read(writer/'writing_job.json');atomic_json(writer/'writer_done.json',{'job_id':job['job_id'],'prompt_sha256':job['prompt_sha256'],'status':'completed','draft_file':'draft.md','word_file':'article.docx','authoring_origin':'Codex editorial correction requested by user; not an API writer delivery'})
report=check(base/'research',writer);assert not report['failures'],report
review=base/'review';review.mkdir()
for n in ('draft.md','knowledge.json','product.json','category.json'):shutil.copy2(writer/n,review/n)
ticket={'stage':'review','meta':{'date':day,'category':category,'number':number,'consumer_rewrite':True}}
budget=runtime.SharedBudget(side)
try:
    response=CreationClient(runtime.KEY,budget=budget).complete(build_prompt(ticket,review),side/'calls/review',max_tokens=1800,stage='review',meta=ticket['meta'])
    materialize(ticket,review,response);finalize(side,review)
finally:budget.db.close()
output=side/'approved'/day/category/'05'
note={'at':time.time(),'reason':'用户指出来源解读式正文，Codex按原主题作编辑重写，并由独立API审稿；未新增付费写作请求','writer_origin':'Codex editorial correction','paid_writer_calls':0,'original_evidence_unchanged':True,'original_quarantine_preserved':True,'review_draft_sha256':file_hash(output/'draft.md'),'new_word_sha256':file_hash(output/'article.docx'),'publication_approved':False}
atomic_json(output/'content_revision.json',note)
receipt=runtime.read(output/'receipt.json');receipt['files']['content_revision.json']=file_hash(output/'content_revision.json');receipt['content_revision']='consumer-voice-v1';atomic_json(output/'receipt.json',receipt)
destination=root/'approved'/day/category/'05';assert not destination.exists();shutil.copytree(output,destination)
event(root,'content_revision','用户截图文章完成独立编辑重写及重新审稿；正文与溯源分开，原预算未改',category=category,number=number)
atomic_json(side/'complete.json',note);print(json.dumps(note,ensure_ascii=False))
