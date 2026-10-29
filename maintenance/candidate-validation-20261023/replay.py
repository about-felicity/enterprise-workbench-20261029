"""Historical response replay and explicitly synthetic routing checks; never a model eval."""
import copy,json,math,shutil,sys,time,traceback
from pathlib import Path
import offline_guard
D=Path(__file__).resolve().parent;S=D/'isolated';E=S/'evidence';sys.path[:0]=[str(S/'engine'),str(S)]
from geo_source_cards import article_compiler as compiler,section_writer as w,structure_analyzer as a,review_arbitration as r
from geo_source_cards.consumer_prompts import evidence_units,reader_facts
from geo_source_cards.genre_length import policy,validate as length_validate,body,hanzi
from geo_source_cards.product_richness import contract as detail_contract
from geo_source_cards.deepseek_api import APIError,request_payload
from geo_source_cards.runtime import atomic_json
from geo_source_cards.quality_checks import findings,semantic_candidates
from geo_source_cards import review_quality
def read(p):return json.loads(Path(p).read_text('utf8'))
def failed(call):
 try:call()
 except (ValueError,APIError) as e:return str(e)
 raise AssertionError('Expected rejection did not happen')
def raw_response(call):
 if (call/'response.json').exists():return read(call/'response.json')
 value=read(call/'answer.json')
 if value.get('finish_reason')=='length':raise APIError('output_incomplete')
 try:return json.loads(value['content'])
 except (ValueError,KeyError):raise APIError('invalid_response')
def tasks_for(c,k,p):
 tasks=w.plan(c,policy(k['reference_design']));detail=detail_contract(p,True)
 for t in tasks:
  if t.get('subject')==p['name']:
   t['target_hanzi']=max(t['target_hanzi'],detail['target_hanzi']);t['product_detail_contract']=detail
   t['commercial_relationship']='本文涉及自有品牌产品。仅在本节简短披露一次，其他章节不重复。'
 w.bound_lengths(tasks,policy(k['reference_design']));return tasks
run_root=S/('replay-'+str(time.time_ns()))
output={'type':'zero_api_historical_replay','new_api_calls':0,'new_cost_cny':0,'samples':[],'blockers':[],'synthetic_checks':{}}
for category,number,rid in [('排行类',1,'4a3b427ed88d72ed8558bf82'),('测评类',2,'08ee3e1b3de618d868e94cda')]:
 original=E/'api/runs'/rid;work=run_root/str(number);writer=work/'writer';writer.mkdir(parents=True)
 shutil.copytree(E/f'days/2026-10-21/articles/{category}/{number:02}/research',work/'research')
 for name in ('knowledge.json','product.json','revision_note.txt'):
  if (original/name).exists():shutil.copyfile(original/name,writer/name)
 k,p=read(writer/'knowledge.json'),read(writer/'product.json');units=evidence_units(writer);c=compiler.compile_article(k,p,units)
 before_k=a.digest(k);own=[s for s in c['sections'] if s['subject']==p['name']];assert len(own)==1 and own[0]['id']=='S2'
 claims={v['id']:v for v in c['claims']};assert all(claims[i]['source_ids'][0].startswith('PF') for i in own[0]['claim_ids'])
 for section in c['sections']:
  assert not section['subject'] or all(section['subject'] in claims[i]['subjects'] for i in section['claim_ids'])
 no=copy.deepcopy(k);no['product_gate']['decision']='NO_INSERT';no_contract=compiler.compile_article(no,p,units)
 assert not any(v['source_ids'][0].startswith('PF') for v in no_contract['claims'])
 structure_origin=E/'api/runs'/('b13a1acdb95039a6fa6061c2' if category=='排行类' else 'd5a3294bcf0da69f7e82ea87')
 assert read(structure_origin/'knowledge.json')['reference_design']['primary_url']==k['reference_design']['primary_url']
 class HistoricalAnalyzer:
  def __init__(self):self.calls=[]
  def complete(self,prompt,folder,**kw):
   self.calls.append(str(folder));return copy.deepcopy(raw_response(structure_origin/'structure_calls'/folder.name))
 analyzer=HistoricalAnalyzer();structure=a.analyze(analyzer,writer,writer,k,{})
 c=a.bind(c,structure);tasks=tasks_for(c,k,p);atomic_json(writer/'compilation.json',c);atomic_json(work/'tasks.json',tasks)
 original_structure=read(original/'article_structure.json');view=a.writer_view(original_structure)
 leaked=any(s['required_content']==src['required_content'] and s['required_content']!=[s['purpose']+'，只使用当前任务可用的事实'] for s,src in zip(view['sections'],original_structure['sections']))
 historical=[]
 for t in tasks:
  f=original/'section_calls'/t['id']/'accepted.json'
  if not f.exists():continue
  v=read(f)
  try:w.validate_part(copy.deepcopy(v),t,c);error=None
  except (ValueError,APIError) as e:error=str(e)
  historical.append({'id':t['id'],'body_chars':sum(len(x['text']) for x in v.get('paragraphs',[])),'target_hanzi':t['target_hanzi'],'max_chars':t.get('max_chars'),'compatibility_error':error,'not_a_fresh_model_output':True})
 old_answer=read(original/'answer.json');old_comp=read(original/'compilation.json')
 assert not failed(lambda:compiler.validate_document(copy.deepcopy(old_answer)|{'document':{**old_answer['document'],'sections':[]}},old_comp,complete=True)) is None
 error=failed(lambda:compiler.validate_document(copy.deepcopy(old_answer),c,complete=True))
 # Explicitly replay raw historical sections into a new candidate execution.
 # Different payloads are recorded, never represented as exact-cache reuse.
 class HistoricalWriter:
  def __init__(self):self.calls=[]
  def complete(self,message,folder,**kw):
   data=json.loads(message.split('资料：')[-1]);identity=data['task']['id'];self.calls.append({'id':identity,'revision_inherited':data['revision_requirements']==(writer/'revision_note.txt').read_text('utf8') if (writer/'revision_note.txt').exists() else data['revision_requirements']==''})
   path=original/'section_calls'/identity/folder.name
   value=raw_response(path) if (path/'answer.json').exists() or (path/'response.json').exists() else read(original/'section_calls'/identity/'accepted.json')
   atomic_json(folder/'replay_provenance.json',{'historical_source':str(path),'new_api_calls':0,'new_payload_not_original_request':True})
   atomic_json(folder/'response.json',value);return copy.deepcopy(value)
 replay_client=HistoricalWriter()
 try:w.generate(replay_client,writer,{'offline_replay':True});state='historical_schema_compatible_only'
 except (ValueError,APIError) as e:state=str(e)
 prompts=[]
 for t in tasks:
  message=w.prompt(c,tasks,t,[],revision=(writer/'revision_note.txt').read_text('utf8') if (writer/'revision_note.txt').exists() else '')
  prompts.append({'id':t['id'],'utf8_bytes':len(json.dumps(request_payload(message,0)['messages'],ensure_ascii=False).encode('utf8'))+256,'max_tokens':min(2600,max(900,t['target_hanzi']*3+350))})
 atomic_json(work/'writer-cost-inputs.json',prompts)
 assert a.digest(k)==before_k
 sample={'category':category,'number':number,'run_id':rid,'work_dir':str(work),'structure_response_origin':str(structure_origin),'own_slot':own[0]['id'],'own_source_ids':sorted({claims[i]['source_ids'][0] for i in own[0]['claim_ids']}),
 'all_product_claims_subject_scoped':True,'no_insert_releases_no_pf':True,'feasibility':c['feasibility']['status'],
 'source_units':len(units),'source_chars':len(structure['source']['original_text']),'structure_replayed_calls':len(analyzer.calls),'structure_degraded':structure.get('degraded'),
 'expected_body_sections':len(c['sections']),'components_including_intro_end':len(tasks),'allotted_body_chars':sum(t['max_chars'] for t in tasks),'article_max_chars':6000,
 'old_answer_cannot_be_rebound':error,'historical_section_checks':historical,'historical_writer_result':state,'historical_writer_calls':replay_client.calls,
 'structure_own_binding':next(s['structure_id'] for s in c['sections'] if s.get('subject')==p['name'])}
 output['samples'].append(sample)
 # The saved semantic analysis must not supply original product requirements.
 projected=a.writer_view(original_structure)
 assert all('source_quote' not in s for s in projected['sections'])
 # Record binding evidence without treating a successful routing test as quality.
 if category=='测评类':
  first_product=original_structure['sections'][1]
  saved_bound=a.bind(compiler.compile_article(k,p,units),original_structure)
  saved_own=next(s['structure_id'] for s in saved_bound['sections'] if s.get('subject')==p['name'])
  output['structure_binding_evidence']={'first_original_product':first_product['id'],'purpose':first_product['purpose'],
   'regenerated_from_old_api_own_binding':sample['structure_own_binding'],'saved_artifact_own_binding':saved_own,'candidate_roles':[(s['id'],a.abstract_task(s)['role']) for s in original_structure['sections']]}
  if saved_own!=first_product['id']:
   output['blockers'].append({'id':'B1','kind':'structure_mapping','evidence':output['structure_binding_evidence'],'minimal_fix':'统一识别原文各产品介绍的结构角色，再按产品叙述顺序绑定；保留事实边界，不依赖是否出现“产品/品牌”等词。'})

# Use the actual saved fact and logic reviews. Synthetic needs_check decisions
# exercise coverage/state only and never assert that the article is correct.
diag_source=E/'api/runs/cbf30a2a5c4e055440271779';diag=run_root/'arbitration/review';shutil.copytree(diag_source,diag)
shutil.copytree(E/'days/2026-10-21/diagnostic/测评类/02/research',diag.parent/'research')
for name in ('quality_pipeline.json','fact-original.json','review.json','answer.json'):
 if (diag/name).exists():(diag/name).rename(diag/(name+'.historical'))
if (diag/'arbitration-call').exists():shutil.move(str(diag/'arbitration-call'),str(diag/'old-arbitration-call'))
fact=read(diag/'call/response.json');text=(diag/'draft.md').read_text('utf8');k,p=read(diag/'knowledge.json'),read(diag/'product.json')
from geo_source_cards.api_prompts import expand_references
expanded=expand_references('review',diag,copy.deepcopy(fact));logic=read(diag/'logic-call/logic_certificate.json');expanded['logic_review']=logic
local=[*findings(text,k,p),*semantic_candidates(text)];data=r.context(diag,expanded,local)
class MockArbitrator:
 def __init__(self):self.calls=[]
 def complete(self,message,folder,**kw):
  batch=json.loads(message.split('资料：')[-1]);self.calls.append({'ids':[v['id'] for v in batch['proposals']],'max_tokens':kw['max_tokens'],'full_context':batch['paragraphs']==data['paragraphs'] and batch['knowledge']==data['knowledge'],'bytes':len(json.dumps(request_payload(message,0)['messages'],ensure_ascii=False).encode('utf8'))+256})
  decisions=[]
  for v in batch['proposals']:
   ids=v.get('paragraph_ids',[]);quote=next((b['text'][:35] for b in batch['paragraphs'] if b['id'] in ids),'')
   decisions.append({'issue_id':v['id'],'classification':'needs_check','paragraph_ids':ids,'article_quote':quote,'source_ids':[],'source_quote':'','reason':'离线合成占位，仅验证覆盖与状态，不是语义判断。','repair':''})
  return {'decisions':decisions}
mock=MockArbitrator();batchfolder=diag/'coverage-only';value=r.batched(mock,batchfolder,data,{})
assert len(value['decisions'])==len(data['proposals']);assert all(v['full_context'] and len(v['ids'])<=3 for v in mock.calls)
before=len(mock.calls);r.batched(mock,batchfolder,data,{});assert len(mock.calls)==before
invalidations={}
for change in ('body','knowledge','original_source'):
 changed=copy.deepcopy(data)
 if change=='body':changed['draft_sha256']='different-body'
 elif change=='knowledge':changed['knowledge']['knowledge_units'][0]['content']+='材料改变'
 else:changed['original_source_units'][0]['content']+='原始来源改变'
 invalidations[change]=failed(lambda:r.batched(mock,batchfolder,changed,{}))
output['arbitration']={'real_initial_fact_failures':len(fact['failures']),'real_logic_status':logic.get('status'),'total_proposals':len(data['proposals']),
 'batch_sizes':[len(v['ids']) for v in mock.calls],'unique_decisions':len({d['issue_id'] for d in value['decisions']}),
 'all_full_context':True,'resume_extra_calls':len(mock.calls)-before,'invalidations':invalidations,'semantic_arbitration':'NOT_TESTED_SYNTHETIC_NEEDS_CHECK_ONLY','cost_inputs':mock.calls}
atomic_json(S/'arbitration-input.json',data)
# Check the real pipeline fast path after only original research changes.
pipeline_mock=MockArbitrator();answer=review_quality.process(pipeline_mock,diag,copy.deepcopy(fact),{})
research=diag.parent/'research/research_result.json';old_sources=read(research);changed=copy.deepcopy(old_sources);changed['knowledge_units'][0]['content']+='原始来源在审稿后改变'
atomic_json(research,changed)
assert evidence_units(diag)!=data['original_source_units']
try:
 replayed=review_quality.process(pipeline_mock,diag,answer,{})
 source_invalidated=False
except ValueError as e:source_invalidated=True
atomic_json(research,old_sources)
output['source_only_final_pipeline_invalidated']=source_invalidated
if not source_invalidated:
 output['blockers'].append({'id':'B2','kind':'stale_original_source','evidence':'保存真实初审+合成needs_check仲裁后，仅修改research_result.json原始来源；quality_pipeline快路径直接返回旧结果。分批输入校验能拒绝变化，但最终缓存快路径未重新构建来源指纹。','minimal_fix':'把完整原始来源的摘要纳入最终质量证书，并在缓存复用及终验时重新读取核对；来源变化后失效审稿及仲裁，不重写或清空历史。'})
output['blocked_network_attempts']=len(offline_guard.blocked)
atomic_json(D/'replay-results.json',output)
print(json.dumps({'samples':[{k:s[k] for k in ('category','own_slot','expected_body_sections','historical_writer_result','structure_own_binding')} for s in output['samples']],
 'arbitration':{k:v for k,v in output['arbitration'].items() if k!='cost_inputs'},'blockers':output['blockers'],'new_api_calls':0},ensure_ascii=False,indent=2))
