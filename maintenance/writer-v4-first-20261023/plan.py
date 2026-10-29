"""Structure-driven execution plan over frozen V4 writer; no model calls."""
import copy,hashlib,json,math,sys
from pathlib import Path
BASE=Path('/opt/monitor/geo-capture/maintenance/20261023-structure-v4-final')
sys.path[:0]=[str(BASE/'isolated/current/engine'),str(BASE/'isolated/current')]
from geo_source_cards import article_compiler as ac,structure_analyzer as sa,structure_protocol as sp,section_writer as sw,consumer_prompts as cp
from geo_source_cards.genre_length import policy
from geo_source_cards.product_richness import contract as detail_contract
from geo_source_cards.deepseek_api import request_payload
from geo_source_cards.argument_plan import digest
from geo_source_cards.runtime import atomic_json
SOURCE=Path('/opt/monitor/geo-content/runtime/acceptance/20261023-structure-v4/rank01-structure-v4-20261023T144205-61a04a86')
read=lambda p:json.loads(Path(p).read_text('utf-8-sig'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
REVIEW={'fact':{'input_bytes':167936,'max_tokens':3500},'logic':{'input_bytes':131072,'max_tokens':3500}}
NEW_CAP=7.20-.0200742-.02588384-.00410024
def size(payload):return len(json.dumps(payload['messages'],ensure_ascii=False).encode('utf8'))+256
def cost(n,t):return (n*2+t*8)/1e6
def compile_plan(writer):
 writer=Path(writer);k=read(writer/'knowledge.json');product=read(writer/'product.json');structure=read(writer/'article_structure.json')
 data=sa.review_source(structure);sp.verify(structure,data)
 assert structure['status']=='structure_ready_with_checks' and len(structure['sections'])==15 and len(data['blocks'])==84
 base=ac.compile_article(k,product,cp.evidence_units(writer));base=sa.bind(base,structure)
 assert base['feasibility']['writeable']
 products=[s for s in base['sections'] if s.get('subject')];regions=[s for s in structure['sections'] if s['role']=='subject' and s['role_status']=='inferred']
 assert len(products)==len(regions)==10
 assert products[0]['subject']==product['name'] and products[0]['structure_id']=='AS-O0003'
 general=[s for s in base['sections'] if not s.get('subject')];assert general
 result=copy.deepcopy(base);result['sections']=[];mapping=[];pindex=0;previous=None
 for i,region in enumerate(structure['sections'],1):
  subject=region['role']=='subject' and region['role_status']=='inferred'
  source=products[pindex] if subject else general[0] if i==1 else general[-1]
  if subject:pindex+=1
  s=copy.deepcopy(source);s['id']=f'S{i}';s['reads_previous_section']=previous;previous=s['id']
  s['source_section_contract_id']=source['id'];s['source_structure_id']=region['id']
  s['source_region']={key:region[key] for key in ('id','topic','purpose','role','role_status','moves','after','anchors')}
  allowed=region['binding_allowed'];s['structure_id']=region['id'] if allowed else None
  s['structure_binding']={'status':region['role_status'],'binding_allowed':allowed,'role':region['role'],'source_block_ids':region['source_block_ids']}
  s['structure_task']=sa.abstract_task(region,region['role']);s['structure_task']['role_status']=region['role_status']
  if not subject:
   s['subject']=None;s['role']='general_advice';s['topic']=region['topic'];s['question']=region['purpose']
   s['scope_note']='只借鉴本区域组织动作，不复制原文品牌、功效、价格、实测或排名。普通选择建议不冒充实验结论。'
   if not allowed:
    s['scope_note']+='原文语义角色仍待核对，不得宣称已确认，也不得绑定任何产品。'
   texts='\n'.join(b['text'] for b in data['blocks'] if b['id'] in region['source_block_ids'])
   if region['role']=='unknown' and '免责声明' in texts:
    s['claim_ids']=[];s['evidence_ids']=[];s['knowledge_ids']=[];s['allowed_conclusions']=[];s['depends_on_claims']=[];s['reasoning']['premises']=[]
    s['scope_note']+='此原文区域明确含免责声明，只能写本文信息使用范围，不能继承原站责任承诺、资质或功效背书；不擅自确认其抽象角色。'
  result['sections'].append(s);mapping.append({'writer_id':s['id'],'source_structure_id':region['id'],'subject':s.get('subject'),'binding_allowed':allowed,'role_status':region['role_status'],'claim_ids':s['claim_ids']})
 assert result['claims']==base['claims'] and result['evidence']==base['evidence'] and result['feasibility']==base['feasibility']
 assert [(s['subject'],s['claim_ids']) for s in products]==[(s['subject'],s['claim_ids']) for s in result['sections'] if s.get('subject')]
 result['execution_contract']={'parent_sha256':base['sha256'],'reason':'Explicit user request: INTRO + 15 source regions + END; unchanged facts and per-product permissions','structure_sha256':structure['sha256']}
 result.pop('sha256',None);result['sha256']=digest(result);ac.validate(result)
 length=policy(k.get('reference_design'));tasks=sw.plan(result,length);detail=detail_contract(product,True)
 for t in tasks:
  if t.get('subject')==product['name']:
   t['target_hanzi']=max(t['target_hanzi'],detail['target_hanzi']);t['product_detail_contract']=detail
   t['commercial_relationship']='本文涉及自有品牌产品。仅在本节简短披露一次，其他章节不重复。'
 sw.bound_lengths(tasks,length)
 envelopes=[]
 for t in tasks:
  maximum=min(2600,max(900,t['target_hanzi']*3+350));n=size(request_payload(sw.prompt(result,tasks,t,[]),maximum))
  ceiling=min(77824,math.ceil((n+32768)/1024)*1024)
  assert n<=ceiling,f"Writer input exceeds existing safe cap: {t['id']} {n}>{ceiling}"
  envelopes.append({'id':t['id'],'initial_prompt_bytes':n,'input_byte_ceiling':ceiling,'max_tokens':maximum,'max_attempts':3,'per_request_upper_cny':cost(ceiling,maximum)})
 review={stage:{**v,'upper_cny':cost(v['input_bytes'],v['max_tokens'])} for stage,v in REVIEW.items()}
 initial=sum(v['per_request_upper_cny'] for v in envelopes)+sum(v['upper_cny'] for v in review.values())
 worst=3*sum(v['per_request_upper_cny'] for v in envelopes)+sum(v['upper_cny'] for v in review.values())
 return {'base_contract':base,'contract':result,'mapping':mapping,'tasks':tasks,'length':length,'envelopes':envelopes,'review':review,
  'initial_calls':len(tasks)+2,'max_calls':len(tasks)*3+2,'initial_upper_cny':initial,'all_attempts_upper_cny':worst,'remaining_incremental_authorization_cny':NEW_CAP}
if __name__=='__main__':
 p=compile_plan(SOURCE/'article/writer');print(json.dumps({k:v for k,v in p.items() if k not in ('base_contract','contract','tasks')},ensure_ascii=False,indent=2))
