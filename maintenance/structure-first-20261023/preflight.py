"""Structure-only read-only preflight. Never sends or instantiates a model client."""
import hashlib,json,sqlite3,sys,uuid
from datetime import datetime,timezone,timedelta
from pathlib import Path

sys.dont_write_bytecode=True
network_attempts=[]
def deny_network(event,args):
 if event in ('socket.connect','socket.getaddrinfo','socket.sendto'):
  network_attempts.append(event)
  raise RuntimeError('Network disabled in structure preflight')
sys.addaudithook(deny_network)
read=lambda p:json.loads(Path(p).read_text('utf-8-sig'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
digest=lambda x:hashlib.sha256(json.dumps(x,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
now=datetime.now(timezone(timedelta(hours=8)))
run='rank01-structure-preflight-'+now.strftime('%Y%m%dT%H%M%S')+'-'+uuid.uuid4().hex[:8]
root=Path('/opt/monitor/geo-content/runtime/acceptance/20261023-structure-first')/run
root.mkdir(parents=True,exist_ok=False)
base=Path('/opt/monitor/geo-capture/maintenance/20261023-structure-recovery-v3-final')
original=Path('/opt/monitor/geo-content/runtime/runs/creation-1792575159-0a8f9221')
previous=Path('/opt/monitor/geo-content/runtime/acceptance/20261023-rank01-staged/rank01-staged-20261023T120816-e50a98ac')
shared=Path('/home/user/geo-editorial/runtime-api')
assert sha(base/'manifest.json')=='b2fffe9a51e968689dfba104918f77545278e51c2bf5cad7a78ec538e96030ed'
manifest=read(base/'manifest.json')
assert manifest['version']=='candidate-structure-recovery-v3-20261023'
candidate_checks={name:{'expected':v['sha256'],'actual':sha(base/'candidate-source'/name)} for name,v in manifest['files'].items()}
execution_checks={name:{'expected':v,'actual':sha(base/'isolated/current'/name)} for name,v in manifest['execution_source_sha256'].items()}
assert all(v['expected']==v['actual'] for v in [*candidate_checks.values(),*execution_checks.values()])
job=read(original/'job.json');settings=read(shared/'settings.json')
assert job['job_id']=='creation-1792575159-0a8f9221'
assert job['studio_plan_id']=='plan-33e7bfca8bb6497da10b28f0444a693b'
src=original/f"days/{job['date']}/compiler-pilots/排行类/01"
writer=src/'writer'
input_files=sorted(p for folder in (writer,src/'research') for p in folder.rglob('*') if p.is_file())
assert all((writer/n).is_file() for n in ('knowledge.json','product.json','writing_job.json','writing_prompt.md'))
assert (src/'research/research_result.json').is_file()
protected=[*input_files,original/'job.json',shared/'settings.json',base/'manifest.json']
protected += [p for p in (original/'control.json',previous/'cost_ledger.json',previous/'summary.json') if p.is_file()]
protected += list((previous/'article/writer/structure_calls').rglob('*.json'))
protected += [base/'candidate-source'/n for n in candidate_checks]
protected += [base/'isolated/current'/n for n in execution_checks]
before={str(p):sha(p) for p in protected}
old=read(previous/'preflight.json')['protected_before']
input_history_matches={str(p):{'current':sha(p),'previous':old.get(str(p))} for p in input_files if str(p) in old}
assert all(v['current']==v['previous'] for v in input_history_matches.values())
sys.path[:0]=[str(base/'isolated/current/engine'),str(base/'isolated/current')]
from geo_source_cards import structure_analyzer as analyzer,structure_protocol as protocol,api_budget
assert Path(protocol.__file__).resolve()==(base/'isolated/current/engine/geo_source_cards/structure_protocol.py').resolve()
source=analyzer.source_input(writer,read(writer/'knowledge.json'))
plan=protocol.plan(source)
price_age=(now.date()-datetime.strptime(api_budget.PRICE_DATE,'%Y-%m-%d').date()).days
assert 0<=price_age<=30
initial=[c for c in plan['calls'] if c['mode']=='compact']
recovery=[c for c in plan['calls'] if c['mode']=='minimal']
upper=plan['reservation_upper_cny']
def ledger():
 with sqlite3.connect((shared/'api/costs.sqlite').as_uri()+'?mode=ro',uri=True) as db:
  db.row_factory=sqlite3.Row
  rows=[dict(r) for r in db.execute('select * from costs order by id')]
  tags=[dict(r) for r in db.execute('select * from studio_cost_scopes order by id')]
 lookup={r['id']:r for r in rows}
 joined=[{**lookup[t['id']],**{k:v for k,v in t.items() if k!='id'}} for t in tags if t['id'] in lookup]
 used=lambda seq:sum(r['charged'] if r['charged'] is not None else r['reserved'] for r in seq)
 scope=[r for r in joined if r['scope']==job['studio_plan_id'] and r['task_day']==job['date']]
 article=[r for r in joined if r['job']==job['job_id'] and (r['category']=='' or r['category']=='排行类' and r['article'] in ('shared','1'))]
 return {'rows':len(rows),'logical_sha256':digest([rows,tags]),'article_used_cny':used(article),
  'scope_used_cny':used(scope),'day_used_cny':used([r for r in rows if r['date']==now.date().isoformat()]),
  'unknown':[{'id':r['id'],'state':r['state'],'reserved':r['reserved']} for r in rows if r['charged'] is None],
  'article_unknown':[{'id':r['id'],'state':r['state'],'reserved':r['reserved']} for r in article if r['charged'] is None],
  'article_cost_rows':article}
ledger_before=ledger()
limits=job.get('budget_limits',{})
checks=[]
for name,cap,used in (
 ('shared_article',settings['article_budget_cny'],ledger_before['article_used_cny']),
 ('job_article',limits.get('article_budget_cny',settings['article_budget_cny']),ledger_before['article_used_cny']),
 ('scope',limits.get('task_budget_cny',settings['test_budget_cny']),ledger_before['scope_used_cny']),
 ('day',settings['daily_budget_cny'],ledger_before['day_used_cny'])):
 checks.append({'name':name,'cap_cny':cap,'used_cny':used,'remaining_raw_cny':cap-used,
  'required_stage_upper_cny':upper,'minimum_cumulative_cap_cny':used+upper,
  'shortfall_cny':max(0,used+upper-cap),'fits':used+upper<=cap+1e-9})
blocked=[c for c in checks if not c['fits']]
previous_cost=read(previous/'cost_ledger.json')
history=[]
for folder in sorted((previous/'article/writer/structure_calls').glob('attempt-*')):
 req=read(folder/'request.json');answer=read(folder/'answer.json')
 history.append({'path':str(folder),'request_sha256':sha(folder/'request.json'),'response_sha256':sha(folder/'answer.json'),
  'max_tokens':req['max_tokens'],'finish_reason':answer['finish_reason'],'usage':answer['usage']})
assert len(history)==2 and all(r['finish_reason']=='length' for r in history)
after={str(p):sha(p) for p in protected}
ledger_after=ledger()
assert before==after and ledger_before==ledger_after
assert not network_attempts
status='BLOCKED_BEFORE_FIRST_REQUEST' if blocked or ledger_before['article_unknown'] else 'PREFLIGHT_PASSED_NO_REQUEST_SENT'
result={'run_id':run,'at':now.isoformat(),'status':status,'candidate_version':manifest['version'],
 'candidate_manifest_sha256':sha(base/'manifest.json'),'candidate_checks':candidate_checks,'execution_checks':execution_checks,
 'job_id':job['job_id'],'scope':job['studio_plan_id'],'task_date':job['date'],'job_input_version':job['input_sha256'],
 'job_file_sha256':sha(original/'job.json'),'budget_config':settings,'job_limits':limits,
 'input_sha256':{str(p):sha(p) for p in input_files},'historical_input_matches':input_history_matches,
 'source_digest':protocol.digest(source),'source_block_count':len(source['blocks']),
 'planned_regions':[{'section_id':g['section_id'],'role_hint':g['role_hint'],'anchors':g['anchors'],'block_count':len(g['blocks'])} for g in plan['units']],
 'plan_type':'deterministic_request_plan_only_not_model_structure','protocol':protocol.VERSION,
 'initial_calls':len(initial),'initial_upper_cny':sum(c['reservation_upper_cny'] for c in initial),
 'max_recovery_calls':len(recovery),'recovery_upper_cny':sum(c['reservation_upper_cny'] for c in recovery),
 'max_stage_calls':plan['max_calls'],'max_stage_output_tokens':plan['max_output_tokens'],'stage_upper_cny':upper,
 'per_call_budget':[{k:c[k] for k in ('key','mode','input_bytes','max_tokens','reservation_upper_cny')} for c in plan['calls']],
 'price_date':api_budget.PRICE_DATE,'rates':{'input_miss':api_budget.INPUT_MISS,'output':api_budget.OUTPUT},
 'budget_checks':checks,'blocking_checks':blocked,'ledger_before':ledger_before,'ledger_after':ledger_after,
 'previous_failed_requests':history,'protected_before':before,'protected_after':after,
 'real_api_calls':0,'balance_api_calls':0,'network_attempts':network_attempts,'new_cost_cny':0,'new_reservation_cny':0,
 'budget_modified':False,'old_attempts_reset':False,'new_billing_job_or_scope':False,'production_deployed':False,
 'unperformed':['real_structure_analysis','model_output_validation','Writer','Reviewer','repair','Word','deployment']}
def save(name,value):
 (root/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf8')
save('preflight.json',result)
save('api_calls.json',{'run_id':run,'status':'NOT_STARTED','calls':[],'reason':status})
save('cost_ledger.json',{'run_id':run,'new_requests':[],'new_cost_cny':0,'new_reserved_cny':0,'history_before':ledger_before,'history_after':ledger_after})
save('structure_validation.json',{'run_id':run,'status':'NOT_EXECUTED','passed':None,'reason':'No real structure generated; preflight only','not_a_structure_acceptance':True})
reason='\n'.join(f"- {c['name']}: 当前累计上限 {c['cap_cny']:.8f} 元，历史累计 {c['used_cny']:.8f} 元；完整结构阶段含恢复需 {upper:.6f} 元，累计上限至少需 {c['minimum_cumulative_cap_cny']:.8f} 元，缺口 {c['shortfall_cny']:.8f} 元。" for c in blocked)
summary=f'''# 排行01真实结构分析：发送前检查

run_id：{run}。状态：{status}。

冻结候选 {manifest['version']}，{len(candidate_checks)} 份覆盖文件、{len(execution_checks)} 份完整执行源码 SHA 全部一致。真实原文和产品资料保留，原任务 {job['job_id']}、scope {job['studio_plan_id']}；未创建新的计费身份。

仅计算当前精简协议的请求计划：{len(source['blocks'])} 个原文锚点、{len(plan['units'])} 个自然区域（其中 {sum(g['role_hint']=='subject' for g in plan['units'])} 个产品介绍区域）。这些是程序分块信息，不是本次模型输出。

初始 {len(initial)} 次请求预留 {sum(c['reservation_upper_cny'] for c in initial):.6f} 元，最多 {len(recovery)} 次恢复额外预留 {sum(c['reservation_upper_cny'] for c in recovery):.6f} 元。整个阶段最多 {plan['max_calls']} 次、输出上限合计 {plan['max_output_tokens']} tokens、总预留 {upper:.6f} 元，按现有输入未命中 2 元/百万和输出 8 元/百万规则，无折扣。

## 阻断及所需额度

{reason}

scope 已用 {ledger_before['scope_used_cny']:.8f} 元，上限 {limits.get('task_budget_cny',settings['test_budget_cny']):.2f} 元；当日已用 {ledger_before['day_used_cny']:.8f} 元，上限 {settings['daily_budget_cny']:.2f} 元。完整明细见 preflight.json。

本轮真实 API 调用 0、余额查询 0、新增费用 0、预留 0。未构造或调用模型客户端；进程网络保护记录 0 次外连尝试。配置、费用账本、未知请求、原始输入、冻结源码、旧两次截断答复和控制记录核验前后不变。

遵守本轮要求：必须修改共享预算才能执行时停止，未发送第一个请求。article_structure.json 不存在，未用计划、旧答复或合成结构冒充真实结果。structure_validation.json 明确 NOT_EXECUTED，不能视为通过。没有生成文章，没有启动 Writer、Reviewer、返修、Word 或部署。

等待授权调整必要累计限额后才可重新做执行前检查；本次不修改配置，不自动继续。
'''
(root/'acceptance_summary.md').write_text(summary,encoding='utf8')
files={p.name:{'server_path':str(p),'sha256':sha(p),'bytes':p.stat().st_size} for p in root.iterdir() if p.is_file()}
save('output_manifest.json',{'run_id':run,'status':status,'files':files})
print(json.dumps({'run_id':run,'root':str(root),'status':status,'candidate_overlay_files':len(candidate_checks),
 'execution_files':len(execution_checks),'stage_upper_cny':upper,'initial_upper_cny':result['initial_upper_cny'],
 'checks':checks,'ledger_rows':ledger_before['rows'],'global_unknown':len(ledger_before['unknown']),
 'article_unknown':ledger_before['article_unknown'],'real_api_calls':0,'protected_unchanged':True,
 'files':files,'manifest_sha256':sha(root/'output_manifest.json')},ensure_ascii=False))
