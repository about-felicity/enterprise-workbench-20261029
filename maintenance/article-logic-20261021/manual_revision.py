"""Human-authored logical reconstruction, approved only by both independent reviews."""
import sys,json,time,shutil,hashlib
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
from creation.client import CreationClient
from geo_source_cards.runtime import atomic_json,process_lock
from geo_source_cards.staged_editorial import check,research_for_writer
from geo_source_cards.api_prompts import build_prompt
from geo_source_cards.api_worker import materialize
from geo_source_cards.daily_editorial import finalize,file_hash
ROOT=runtime.BASE/'runs/creation-1792556219-bbc55e13';identity='2026-10-21/科普类/04'
draft=Path('/tmp/mask-logic-revised.md').read_text('utf-8');digest=hashlib.sha256(draft.encode()).hexdigest()
side=runtime.BASE/'logic-revision/20261021-mask04'/digest[:16];side.mkdir(parents=True,exist_ok=True)
if (side/'complete.json').exists():print((side/'complete.json').read_text());raise SystemExit(0)
with process_lock(side/'revision.lock',blocking=False):
 original=ROOT/'days/2026-10-21/jobs/科普类/04/writer';base=side/'days/2026-10-21/articles/科普类/04';base.mkdir(parents=True,exist_ok=True)
 writer=base/'writer';review=base/'review';destination=ROOT/'approved'/identity
 expected='7b9e63c3435c28663085d0b0e4b619de26aa462f829457b94c9c26f9296c7c20'
 assert runtime.read(destination/'receipt.json')['word_sha256']==expected,'Original version changed; inspect first'
 if not writer.exists():shutil.copytree(original,writer)
 research=base/'research'
 if not research.exists():shutil.copytree(research_for_writer(original),research)
 if not (side/'original-approved').exists():shutil.copytree(destination,side/'original-approved')
 atomic_json(side/'job.json',runtime.read(ROOT/'job.json'));atomic_json(side/'logic_policy.json',{'required':True,'version':'article-logic-v1'})
 atomic_json(side/'days/2026-10-21/day.json',{'date':'2026-10-21','status':'isolated_logic_revision'})
 (writer/'draft.md').write_text(draft,encoding='utf-8');shutil.copy2('/tmp/mask-logic-revised.docx',writer/'article.docx')
 claims=[]
 for paragraph in draft.split('\n\n'):
  ids=[]
  if '姿生怡鱼子酱胶原塑颜面膜是凝胶' in paragraph:ids=['PF1','PF2','PF9']
  elif '产品名称中的鱼子酱' in paragraph:ids=[f'PF{i}' for i in range(3,9)]
  elif 'HNYD251011046-2报告摘要采用' in paragraph:ids=['PF10','PF11']
  elif 'HNYD251011046-4为弹性' in paragraph:ids=['PF12','PF13']
  elif 'GF04112025457307摘要还记录' in paragraph:ids=['PF14']
  if ids:claims.append({'text':paragraph,'evidence_ids':ids})
 atomic_json(writer/'claim_map.json',{'claims':claims})
 atomic_json(writer/'knowledge_to_sections.json',{'sections':[{'section_id':f'S{i}','knowledge_ids':['KU09'],'innovation':'重建同一比较问题的推理，去掉成分排序与效果、用心和成本之间的无依据跳跃'} for i in range(1,6)]})
 job=runtime.read(writer/'writing_job.json');atomic_json(writer/'writer_done.json',{'job_id':job['job_id'],'prompt_sha256':job['prompt_sha256'],'status':'completed','draft_file':'draft.md','word_file':'article.docx','authoring_origin':'Codex human editorial reconstruction requested by user; no new API writer call'})
 validation=check(research,writer);atomic_json(side/'local-validation.json',validation)
 assert not validation['failures'],validation
 review.mkdir(exist_ok=True)
 for name in ('draft.md','knowledge.json','product.json','category.json'):shutil.copy2(writer/name,review/name)
 meta={'date':'2026-10-21','category':'科普类','number':4,'consumer_rewrite':True};ticket={'stage':'review','meta':meta}
 budget=runtime.SharedBudget(side);client=CreationClient(runtime.KEY,budget=budget)
 try:
  response=client.complete(build_prompt(ticket,review),side/'calls/semantic-review',max_tokens=2000,stage='review',meta=meta)
  response['logic_review']=client.review_logic(review,side/'calls/logic-review',meta)
  materialize(ticket,review,response);finalize(side,review)
 finally:budget.db.close()
 output=side/'approved'/identity
 note={'at':time.time(),'reason':'用户指出全文逻辑严重问题。由单一贴片体验改为明确的贴片与涂抹比较，分清形态、成分、试验三个证据对象；不把涂抹产品作贴片例证，不由排序推出用心、成本或效果。','paid_writer_calls':0,'original_word_sha256':expected,'new_word_sha256':file_hash(output/'article.docx'),'original_research_and_knowledge_unchanged':True,'scope_change_explicit':True,'old_source_role':'原主参考仅是贴片配方话题的来源，原来的因果与机理叙述已撤下；新稿产品事实只据本任务冻结PF，通用比较段是编辑判断。','independent_semantic_review':True,'independent_argument_logic_review':True,'publication_approved':False}
 atomic_json(output/'content_revision.json',note);receipt=runtime.read(output/'receipt.json');receipt['files']['content_revision.json']=file_hash(output/'content_revision.json');atomic_json(output/'receipt.json',receipt)
 with process_lock(ROOT/'coordinator.lock',blocking=True):
  assert runtime.read(destination/'receipt.json')['word_sha256']==expected
  before=(ROOT/'control.json').read_bytes()
  replacement=destination.with_name('04.logic-new');assert not replacement.exists();shutil.copytree(output,replacement)
  retired=side/'replaced-approved';assert not retired.exists();shutil.move(str(destination),retired);replacement.rename(destination)
  assert (ROOT/'control.json').read_bytes()==before
 atomic_json(side/'complete.json',note);print(json.dumps(note,ensure_ascii=False))
