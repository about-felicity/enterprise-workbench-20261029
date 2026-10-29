"""Offline estimates with existing rates. No balance endpoint or reservations."""
import copy,json,math,statistics,sys
from pathlib import Path
import offline_guard
D=Path(__file__).resolve().parent;S=D/'isolated';sys.path[:0]=[str(S/'engine'),str(S)]
from geo_source_cards.deepseek_api import request_payload
from geo_source_cards.api_budget import INPUT_MISS,INPUT_HIT,OUTPUT,PRICE_DATE
from geo_source_cards.consumer_prompts import build,evidence_units
from geo_source_cards import article_logic as logic,review_arbitration as arbitration
from geo_source_cards.argument_plan import digest
def read(p):return json.loads(Path(p).read_text('utf8'))
def size(prompt):return len(json.dumps(request_payload(prompt,0)['messages'],ensure_ascii=False).encode('utf8'))+256
def reserve(n,o):return (n*INPUT_MISS+o*OUTPUT)/1_000_000
def envelope(n):return math.ceil((n+16384)/4096)*4096
replay=read(D/'replay-results.json');audit=read(D/'audit-before.json');history=read(D.parent/'real-acceptance-20261022/final-audit.json')
observed={}
for path in (S/'evidence/api/runs').rglob('request.json'):
 if 'section_calls' in path.parts:stage='sections'
 elif 'structure_calls' in path.parts:stage='structure'
 elif 'logic-call' in path.parts:stage='logic'
 elif 'arbitration-call' in path.parts:stage='arbitration'
 elif 'call' in path.parts:stage='facts'
 else:continue
 ans=path.with_name('answer.json')
 if not ans.exists():continue
 request,answer=read(path),read(ans);usage=answer.get('usage',{})
 if 'prompt_tokens' not in usage or 'completion_tokens' not in usage:continue
 b=len(json.dumps(request['messages'],ensure_ascii=False).encode('utf8'))+256
 observed.setdefault(stage,[]).append((usage['prompt_tokens']/b,usage['completion_tokens']))
empirical={k:{'samples':len(v),'max_input_token_byte_ratio':max(i for i,o in v),'median_completion_tokens':statistics.median(o for i,o in v)} for k,v in observed.items()}
estimates=[]
for sample in replay['samples']:
 work=Path(sample['work_dir']);writer=work/'writer';k,p=read(writer/'knowledge.json'),read(writer/'product.json');compiled=read(writer/'compilation.json')
 old=read(S/'evidence/api/runs'/sample['run_id']/'answer.json')['document']
 # Cost-only surrogate from historical paragraphs; this is not a candidate draft.
 lines=['# '+old['title']]+[v['text'] for v in old['introduction']]
 for section in old['sections']:lines+=['## '+section['heading']]+[v['text'] for v in section['paragraphs']]
 lines += [v['text'] for v in old['conclusion']]
 text='\n\n'.join(lines)+'\n';cost_dir=work/'cost-only';cost_dir.mkdir()
 for name in ('knowledge.json','product.json'): (cost_dir/name).write_bytes((writer/name).read_bytes())
 (cost_dir/'draft.md').write_text(text,encoding='utf8');(cost_dir/'writer_done.json').write_text(json.dumps({'compilation':compiled},ensure_ascii=False),encoding='utf8')
 # build() needs original research nearby, already located at work/research.
 fact_bytes=size(build('review',cost_dir));logic_bytes=size(logic.prompt(logic.build_input(cost_dir)))
 data=read(S/'arbitration-input.json');data.update(knowledge=k,product=p,compilation=compiled,paragraphs=logic.segments(text),original_source_units=evidence_units(writer),draft_sha256=logic.text_hash(text),evidence_sha256=digest({'knowledge':k,'product':p}))
 arb_bytes=max(size(arbitration.prompt({**data,'proposals':data['proposals'][offset:offset+3]})) for offset in range(0,len(data['proposals']),3))
 structure_bytes=max(len(json.dumps(read(f)['messages'],ensure_ascii=False).encode('utf8'))+256 for f in Path(sample['structure_response_origin']).glob('structure_calls/*/request.json'))
 writes=read(work/'writer-cost-inputs.json');writer_bytes=max(v['utf8_bytes'] for v in writes)
 inputs={'structure':structure_bytes,'sections':writer_bytes,'facts':fact_bytes,'logic':logic_bytes,'arbitration':arb_bytes}
 outputs={'structure':2400,'facts':1800,'logic':2400,'arbitration':2200}
 n=len(writes);parts=[]
 for stage,count,tokens in [('structure',1,2400),('sections',n,sum(v['max_tokens'] for v in writes)),('facts',1,1800),('logic',1,2400),('arbitration',9,9*2200)]:
  ceiling=envelope(inputs[stage]);hist=empirical[stage]
  projected_input=inputs[stage]*hist['max_input_token_byte_ratio']
  projected_output=(sum(min(v['max_tokens'],hist['median_completion_tokens']) for v in writes) if stage=='sections' else count*min(outputs[stage],hist['median_completion_tokens']))
  estimated=(count*projected_input*INPUT_MISS+projected_output*OUTPUT)/1e6
  cap=reserve(count*ceiling,tokens)
  parts.append({'stage':stage,'initial_calls':count,'measured_max_input_byte_bound':inputs[stage],'planned_per_request_input_byte_ceiling':ceiling,'initial_output_tokens_upper':tokens,'estimated_initial_cny':estimated,'initial_reservation_upper_cny':cap})
 first=sum(v['initial_reservation_upper_cny'] for v in parts)
 # Absolute planned call bounds: analyzer at most 2, each part at most 3,
 # full rewriting both repair rounds as worst case, 30 findings => 10 batches.
 phase_caps={
  'structure_total':reserve(2*envelope(inputs['structure']),2*2400),
  'initial_sections':reserve(3*n*envelope(inputs['sections']),3*sum(v['max_tokens'] for v in writes)),
  'initial_fact_logic_arbitration':reserve(envelope(fact_bytes)+envelope(logic_bytes)+10*envelope(arb_bytes),1800+2400+10*2200)}
 repair_one=phase_caps['initial_sections']+phase_caps['initial_fact_logic_arbitration']
 total=phase_caps['structure_total']+phase_caps['initial_sections']+phase_caps['initial_fact_logic_arbitration']+2*repair_one
 per=audit['ledger']['per_article'][sample['category']];authorized_remainder=2-per
 estimates.append({'sample':sample['category']+str(sample['number']).zfill(2),'body_sections':n-2,'initial_components':n,'phases':parts,
  'expected_initial_calls_with_26_findings':n+12,'expected_initial_cny':sum(v['estimated_initial_cny'] for v in parts),
  'initial_full_output_reservation_upper_cny':first,'structure_second_attempt_extra_cny':reserve(envelope(structure_bytes),2400),
  'all_components_two_supplement_attempts_extra_cny':2*reserve(n*envelope(writer_bytes),sum(v['max_tokens'] for v in writes)),
  'one_repair_full_upper_cny':repair_one,'two_repairs_full_upper_cny':2*repair_one,'total_full_upper_cny':total,
  'maximum_calls_in_planned_envelope':2+9*n+36,'phase_caps':phase_caps,
  'historical_article_used_cny':per,'historically_authorized_article_remainder_cny':authorized_remainder,
  'current_effective_article_remainder_cny':max(0,min(2,audit['shared_settings']['article_budget_cny'])-per),
  'fits_historical_authorization_for_complete_envelope':total<=authorized_remainder,'allowed_to_send_now':False,
  'warning':'费用输入使用历史正文仅作长度与材料体积替身；不是新合格正文。26条为历史实测意见数量；未来最多30条作为方案容量，超出必须停止重算，不得丢弃意见。'})
result={'type':'offline_budget_plan_no_calls','price_rule':{'version_date':PRICE_DATE,'input_miss_cny_per_million':INPUT_MISS,'input_hit':INPUT_HIT,'output':OUTPUT,'off_peak_discount_assumed':False},
 'empirical_usage_projection':empirical,'samples':estimates,'scope_used_cny':audit['ledger']['scope_used'],'scope_authorized_cap_cny':8,'scope_remaining_cny':8-audit['ledger']['scope_used'],
 'current_shared_article_cap_cny':audit['shared_settings']['article_budget_cny'],'current_shared_daily_cap_cny':audit['shared_settings']['daily_budget_cny'],'current_daily_used_cny':audit['ledger']['today_used'],
 'last_observed_balance_cny':15.08,'balance_observed_at':history['at'],'balance_current_verified':False,
 'balance_note':'15.08元为10月22日最终查询记录，隔离api/balance.json为更早15.21元缓存；本轮禁止查询余额API，不能称为当前余额。',
 'fits_last_observed_balance_for_both_envelopes':sum(v['total_full_upper_cny'] for v in estimates)<=15.08,
 'hard_max_new_spend_with_current_settings_cny':0,'new_api_calls':0,'budget_or_history_changed':False,
 'execution_decision':'STOP: two candidate blockers, current shared article cap exhausted, old content revision limits exhausted; preparation only',
 'conditional_envelope_limits':{'max_content_repairs':2,'max_section_attempts':3,'max_structure_attempts':2,'max_arbitration_findings_per_review':30,'max_arbitration_batch_size':3,
 'fact_logic_arbitration_technical_retries':0,'on_exceeded_input_byte_ceiling':'stop before send and recompute; never truncate evidence','on_more_than_30_findings':'stop before arbitration and recompute; never omit issues'},
 'important':'分阶段输入字节上限是本方案的执行前校验条件，目前未安装执行器、未提高额度。未加这些条件时不能宣称仅凭当前历史体积得到无条件完整闭环上界。现有账本始终是每次请求的硬费用保护。'}
(D/'budget-plan.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'samples':[{k:v[k] for k in ('sample','expected_initial_cny','initial_full_output_reservation_upper_cny','total_full_upper_cny','historically_authorized_article_remainder_cny','maximum_calls_in_planned_envelope')} for v in estimates],'scope_remaining':result['scope_remaining_cny'],'new_api_calls':0},ensure_ascii=False,indent=2))
