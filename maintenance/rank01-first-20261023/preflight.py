"""Read-only real acceptance preflight. No model, balance or budget mutations."""
import hashlib,json,sqlite3,time,uuid
from datetime import datetime,timezone,timedelta
from pathlib import Path

NOW=datetime.now(timezone(timedelta(hours=8)));RUN='rank01-first-'+NOW.strftime('%Y%m%dT%H%M%S')+'-'+uuid.uuid4().hex[:8]
ROOT=Path('/opt/monitor/geo-content/runtime/acceptance/20261023-rank01-first')/RUN
ROOT.mkdir(parents=True,exist_ok=False)
BASE=Path('/opt/monitor/geo-capture/maintenance/20261023-b2-repair-entry-v2-final')
ORIGINAL=Path('/opt/monitor/geo-content/runtime/runs/creation-1792575159-0a8f9221')
OLD=Path('/opt/monitor/geo-content/runtime/acceptance/20261022-three-agent')
SHARED=Path('/home/user/geo-editorial/runtime-api');DAY='2026-10-21'
read=lambda p:json.loads(Path(p).read_text('utf-8-sig'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
oldjob=read(OLD/'job.json');job=read(ORIGINAL/'job.json');scope=job['studio_plan_id']
assert oldjob['job_id']==job['job_id'] and oldjob['studio_plan_id']==scope and job['date']==DAY
manifest=read(BASE/'manifest.json')
assert manifest['version']=='candidate-b2-repair-entry-v2-20261023'
verified={p:{'expected':r['sha256'],'actual':sha(BASE/'candidate-source'/p)} for p,r in manifest['files'].items()}
assert all(v['actual']==v['expected'] for v in verified.values())
src=ORIGINAL/f'days/{DAY}/compiler-pilots/排行类/01'
input_files=[p for folder in (src/'writer',src/'research') for p in folder.rglob('*') if p.is_file()]
inputs={str(p):{'sha256':sha(p),'bytes':p.stat().st_size} for p in input_files}
required=['writing_prompt.md','writing_job.json','knowledge.json','product.json','writing_task.txt','category.json','batch_rules.md']
assert all((src/'writer'/n).is_file() for n in required)
assert (src/'research/research_input.json').is_file() and (src/'research/research_result.json').is_file()
paths=[SHARED/'settings.json',ORIGINAL/'job.json',ORIGINAL/'control.json',OLD/'control.json',OLD/'job.json',OLD/'api/active.json']
paths=[p for p in paths if p.is_file()]+input_files
protected_before={str(p):sha(p) for p in paths}
settings=read(SHARED/'settings.json')
def ledger():
 with sqlite3.connect((SHARED/'api/costs.sqlite').as_uri()+'?mode=ro',uri=True) as db:
  db.row_factory=sqlite3.Row
  rows=[dict(r) for r in db.execute('select * from costs order by id')]
  tags=[dict(r) for r in db.execute('select * from studio_cost_scopes order by id')]
 lookup={r['id']:r for r in rows}
 joined=[{**lookup[t['id']],**{k:v for k,v in t.items() if k!='id'}} for t in tags if t['id'] in lookup and t['scope']==scope and t['task_day']==DAY]
 used=lambda seq:sum(r['charged'] if r['charged'] is not None else r['reserved'] for r in seq)
 article=[r for r in joined if r['job']==job['job_id'] and (r['category']=='' or r['category']=='排行类' and r['article'] in ('shared','1'))]
 return {'rows':len(rows),'logical_sha256':hashlib.sha256(json.dumps([rows,tags],sort_keys=True).encode()).hexdigest(),
  'scope':scope,'scope_used_cny':used(joined),'rank01_cumulative_used_cny':used(article),
  'today_used_cny':used([r for r in rows if r['date']==NOW.date().isoformat()]),
  'unknown':[{'id':r['id'],'state':r['state'],'reserved':r['reserved']} for r in rows if r['charged'] is None]}
before=ledger()
# Current approved prompt envelopes. The old 26-opinion figure is not the
# conservative upper bound for the existing 30-opinion capacity.
plan=read(Path('/tmp/rank01-first-budget-reference.json'))
rates=plan['rates_cny_per_million'];phases=[]
for row in plan['phases']:
 count=10 if row['stage']=='arbitration' else row['initial_calls']
 output=22000 if row['stage']=='arbitration' else row['initial_max_output_tokens_total']
 upper=(count*row['conditional_input_byte_ceiling']*rates['input_miss']+output*rates['output'])/1e6
 phases.append({'stage':row['stage'],'calls_upper':count,'per_call_input_bytes_ceiling':row['conditional_input_byte_ceiling'],
  'total_output_tokens_upper':output,'reservation_upper_cny':upper})
upper=sum(v['reservation_upper_cny'] for v in phases)
limits={'incremental_spend':7.20,'article_cumulative':8.00,'task_scope_cumulative':12.00,'daily':10.00}
checks=[('incremental_spend',0),('article_cumulative',before['rank01_cumulative_used_cny']),('task_scope_cumulative',before['scope_used_cny']),('daily',before['today_used_cny'])]
checks=[{'limit_name':key,'used_cny':used,'authorized_cap_cny':limits[key],'remaining_cny':max(0,limits[key]-used),
 'required_upper_cny':upper,'fits':used+upper<=limits[key]+1e-9,'shortfall_cny':max(0,used+upper-limits[key])} for key,used in checks]
blockers=[v for v in checks if not v['fits']]
old_tickets=[read(p) for p in (OLD/'queue').glob('*/ticket.json')]
revision_counts=[t.get('meta',{}).get('compiled_repair_round',0) for t in old_tickets if t.get('meta',{}).get('category')=='排行类' and t.get('meta',{}).get('number')==1]
assert blockers,'This script does not execute. A successful preflight requires the separate guarded first-round runner.'
after=ledger();protected_after={str(p):sha(p) for p in paths}
assert before==after and protected_before==protected_after
result={'run_id':RUN,'at':NOW.isoformat(),'status':'BLOCKED_BEFORE_FIRST_REQUEST','candidate_version':manifest['version'],
 'candidate_sha_verified':verified,'original_job_id':job['job_id'],'original_scope':scope,'new_billing_job_or_scope_created':False,
 'original_input_location':str(src),'input_files':inputs,'input_file_count':len(inputs),'originals_unchanged':True,
 'phases':phases,'price_date':plan['price_date'],'rates_cny_per_million':rates,
 'reservation_policy':'Existing per-request UTF-8-byte bound plus maximum output; no cache or off-peak discount. One initial attempt for each component, not content revisions.',
 'historical_26_opinion_9_batch_upper_cny':plan['initial_reservation_upper_cny'],'opinion_capacity':30,'arbitration_batch_size':3,
 'initial_upper_cny':upper,'budget_checks':checks,'blocking_budget_checks':blockers,
 'known_failure_retries_included':False,'retry_note':'Even without any known-failure supplemental requests the initial stages exceed authorization. Retries can only increase required reserves.',
 'ledger_before':before,'ledger_after':after,'config_before':settings,'config_after':read(SHARED/'settings.json'),
 'budget_lease_applied':False,'settings_restoration_needed':False,'settings_verified_unchanged':True,
 'old_max_compiled_repair_round':max(revision_counts,default=0),'old_revision_counts_reset':False,
 'execution_intent':'Independent acceptance first version only, not an old third repair; no old task state changed.',
 'real_api_calls':0,'balance_api_calls':0,'actual_known_new_cost_cny':0,'new_reserved_cny':0,'new_unknown_requests':0,
 'remaining_this_authorization_cny':7.20,'remaining_executable_new_spend_under_restored_shared_article_cap_cny':0,
 'production_deployed':False,'article_generation_executed':False,'fact_review_executed':False,'logic_review_executed':False,'arbitration_executed':False,
 'unperformed_required_outputs':['rank01_first_draft.docx','rank01_first_draft.md','article_structure.json','claim_ledger.json','review_fact.json','review_logic.json','review_arbitration.json','section_manifest.json'],
 'unperformed_reason':'Budget preflight failed; no API sent. No old article/response or synthetic prose copied to requested output names.',
 'balance_queried':False,'protected_sha_before':protected_before,'protected_sha_after':protected_after}
(ROOT/'preflight.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
(ROOT/'cost_ledger.json').write_text(json.dumps({'run_id':RUN,'status':'NO_REQUESTS_SENT','requests':[],
 'known_charged_cny':0,'reserved_cny':0,'unknown_requests':[],'historical_ledger_preserved':True,
 'original_job_id':job['job_id'],'scope':scope,'history_before':before,'history_after':after},ensure_ascii=False,indent=2))
(ROOT/'budget_configuration_restoration.json').write_text(json.dumps({'lease_applied':False,'before':settings,'after':read(SHARED/'settings.json'),'verified_unchanged':True,'restoration_action':'Not needed; no configuration was changed.'},ensure_ascii=False,indent=2))
rows='\n'.join(f"| {v['stage']} | {v['calls_upper']} | {v['reservation_upper_cny']:.6f} |" for v in phases)
reasons='\n'.join(f"- {v['limit_name']}: required cumulative {v['used_cny']+upper:.8f} > authorized {v['authorized_cap_cny']:.2f}; shortfall {v['shortfall_cny']:.8f}." for v in blockers)
summary=f'''# 排行01首轮真实验收 发送前停止

run_id：{RUN}。时间：{NOW.isoformat()}。候选版本：{manifest['version']}。

本轮未能开始真实生成。真实API请求0、余额查询0、新增费用0元、新增预留0元。未修改任何预算配置，核对前后完全一致。

## 阻断原因

7.153776元的旧首轮数值只覆盖历史26条意见的9批仲裁；现有方案允许最多30条意见，每批3条，需要10批。按原字节和输出上限重算，首轮无任何重试的保守预留已为{upper:.6f}元，超过授权新增硬上限7.20元。不能只取历史意见数量，或少审一批来凑进预算。

| 阶段 | 初始调用上限 | 预留上界 元 |
| --- | ---: | ---: |
{rows}
| 合计 | {sum(v['calls_upper'] for v in phases)} | {upper:.6f} |

{reasons}

日上限保持10元，没有上调。原费用全部计入，本轮未清账。原任务历史最大compiled_repair_round={max(revision_counts,default=0)}，没有清零或恢复；本轮独立首轮尚未执行。

## 实际产物与未完成步骤

实际存在的本轮产物：preflight.json、cost_ledger.json、budget_configuration_restoration.json及本总结。未伪造本次Word、Markdown正文、结构分析、声明账本或审稿文件；它们需要真实执行才能产生。

结构分析、导语、全部主体章节、结尾、事实审稿、逻辑审稿、必要仲裁均未执行。没有文章可判为合格，也没有本轮新的事实/逻辑审稿意见。历史0/2结果不变。

测评02及其余任务没有启动。没有部署、没有覆盖原稿、没有新建计费任务或scope，没有重发3笔原未知请求。核验原始输入、控制文件、预算及账本前后不变。

本轮授权7.20元全部未使用；这不是供应商账户余额。本轮没有查询账户余额。原共享单篇0.35元配置未改，恢复配置下本文章可新增执行额度仍为0元。
'''
(ROOT/'acceptance_summary.md').write_text(summary)
outfiles={p.name:{'server_path':str(p),'sha256':sha(p),'bytes':p.stat().st_size} for p in ROOT.iterdir() if p.is_file()}
(ROOT/'output_manifest.json').write_text(json.dumps({'run_id':RUN,'files':outfiles,'new_cost_cny':0,'status':'BLOCKED_BEFORE_FIRST_REQUEST'},ensure_ascii=False,indent=2))
print(json.dumps({'run_id':RUN,'root':str(ROOT),'status':result['status'],'initial_upper_cny':upper,'blocking_budget_checks':blockers,
 'ledger_rows':before['rows'],'unknown_requests_preserved':len(before['unknown']),'config_unchanged':True,'real_api_calls':0,'files':outfiles},ensure_ascii=False))
