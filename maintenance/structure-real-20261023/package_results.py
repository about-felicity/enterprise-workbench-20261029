"""Offline result inspection and delivery; never constructs or calls an API client."""
import hashlib,json,shutil,sys,zipfile
from pathlib import Path
sys.dont_write_bytecode=True
def block_network(event,args):
 if event in ('socket.connect','socket.getaddrinfo','socket.sendto'):raise RuntimeError('Offline delivery inspection')
sys.addaudithook(block_network)
root=Path(sys.argv[1]);base=Path('/opt/monitor/geo-capture/maintenance/20261023-structure-recovery-v3-final')
sys.path[:0]=[str(base/'isolated/current/engine'),str(base/'isolated/current')]
from geo_source_cards import structure_protocol as sp,structure_analyzer as sa
read=lambda p:json.loads(Path(p).read_text('utf-8-sig'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
auth=read(root/'preflight.json');plan=auth['plan'];writer=root/'article/writer';callsroot=writer/'structure_calls/compact-v2'
summary=read(root/'summary.json');cost=read(root/'cost_ledger.json');api=read(root/'api_calls.json')
assert api['real_completion_calls']==5 and cost['new_cost_known_cny']<=auth['max_new_spend_cny']
assert read(root/'budget_restoration.json')['shared_exactly_restored']
data=sa.source_input(writer,read(writer/'knowledge.json'));assert sp.digest(data)==auth['source_digest']
for path,expected in auth['protected_before'].items():assert sha(path)==expected,path
m=read(base/'manifest.json')
for name,expected in m['execution_source_sha256'].items():assert sha(base/'isolated/current'/name)==expected
article_sha=sha(root/'article_structure.json');assert read(root/'article_structure.json')['status']=='structure_incomplete'
backup=root/'report_initial';backup.mkdir(exist_ok=False)
for name in ('structure_validation.json','summary.json','acceptance_summary.md','output_manifest.json'):shutil.copy2(root/name,backup/name)
accepted=[];coverage=[];chunk_results=[];failure_evidence=[]
for c in plan['calls']:
 folder=callsroot/c['key'];a=folder/'accepted.json'
 if a.exists():
  record=read(a);value=sp.validate_chunk(record['result'],data,c['units'],c['mode'])
  assert sp.digest(value)==record['result_sha256']
  chunk_results.append({'key':c['key'],'result':value,'evidence':str(a.relative_to(root))})
  for section,unit in zip(value['sections'],c['units']):
   blocks=[b['id'] for b in unit['blocks']];accepted.append({**section,'source_block_ids':blocks,'subsection_anchors':unit['subsection_anchors'],'request_key':c['key']});coverage.extend(blocks)
 f=folder/'known_failure.json'
 if f.exists():
  response=read(folder/'response.json');diff=[]
  expected=sp.TOP_KEYS
  if set(response)!=expected:diff.append({'type':'schema_keys','expected':sorted(expected),'actual':sorted(response),'extra':sorted(set(response)-expected)})
  for v,u in zip(response.get('sections',[]),c['units']):
   if v.get('anchors')!=u['anchors']:diff.append({'type':'anchors','section_id':u['section_id'],'expected':u['anchors'],'actual':v.get('anchors')})
   if v.get('role_status')=='needs_check':diff.append({'type':'role_needs_check','section_id':u['section_id'],'role':v.get('role')})
  failure_evidence.append({'key':c['key'],'reason':read(f)['reason'],'differences':diff,'raw_answer':str((folder/'answer.json').relative_to(root))})
assert len(accepted)==9 and coverage==[b['id'] for b in data['blocks'][:61]]
fullids=[b['id'] for b in data['blocks']];missing=[i for i in fullids if i not in coverage]
products=[{'section_id':s['section_id'],'order':i+1,'anchors':s['anchors'],'topic':s['topic']} for i,s in enumerate(accepted) if s['role']=='subject']
planned_products=[{'section_id':u['section_id'],'order':i+1,'anchors':u['anchors'],'accepted':u['section_id'] in {s['section_id'] for s in accepted}} for i,u in enumerate(plan['units']) if u['role_hint']=='subject']
validation={'status':'structure_incomplete','passed':False,'real_api_output':True,'protocol':sp.VERSION,
 'source_digest_unchanged':True,'expected_anchors':84,'validated_covered_anchors':61,'validated_coverage_ratio':61/84,
 'validated_anchor_ids':coverage,'missing_validated_anchor_ids':missing,'validated_order_exact':True,'validated_ids_unique':True,
 'expected_regions':15,'accepted_regions':9,'accepted_product_regions':8,'expected_product_regions':10,
 'accepted_product_positions':products,'planned_product_positions_not_all_model_validated':planned_products,
 'unresolved_roles_in_rejected_response':['AS-O0070'],'failure_evidence':failure_evidence,
 'full_structure_or_writer_ready':False,'finish_reasons':[v['finish_reason'] for v in api['requests']],
 'scope_of_validation':'Partial chunks locally validated against real frozen protocol; no complete merge. Planned positions beyond accepted chunks are not model acceptance.'}
partial={'status':'partial_not_writer_ready','not_a_complete_structure':True,'topic_from_first_real_chunk':chunk_results[0]['result']['article_topic'],
 'purpose_from_first_real_chunk':chunk_results[0]['result']['article_purpose'],'genre':'ranking',
 'accepted_sections':accepted,'accepted_chunk_results':chunk_results,'coverage':{'validated':61,'expected':84},'failure_evidence':failure_evidence}
def save(name,v):(root/name).write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf8')
save('partial_structure.json',partial);save('structure_validation.json',validation)
summary.update(validation=validation,failure_reason='Primary singleton anchor repeated; recovery emitted prohibited units field; recovery exhausted; stopped without additional calls.')
save('summary.json',summary)
rows='\n'.join(f"| {i} | {s['section_id']} | {s['topic']} | {s['purpose']} | {', '.join(s['moves'])} | {'–'.join(s['anchors'])} |" for i,s in enumerate(accepted,1))
text=f'''# 排行01真实结构分析：失败，保留真实部分结果

run_id：{root.name}。冻结候选：{auth['candidate']}。

本次确实发送 DeepSeek API 请求：4 次初始分块请求、1 次最小恢复，共 5 次 completions；另有 5 次现有流程的余额检查。5 次 finish_reason 均为 stop，无输出截断。原始 HTTP、请求参数、模型原文、usage、解析结果、校验失败均保存。新增已知费用为 {cost['new_cost_known_cny']:.8f} 元，沿用原任务和 scope 记账；费用是按现有规则从真实 usage 计算的人民币估算，非独立发票。

## 本次真实输出

第一块返回主题：{partial['topic_from_first_real_chunk']}。第一块返回目的：{partial['purpose_from_first_real_chunk']}。这是局部结果，不能当作最终合并主题。后续分块主题略有差异，原样保存在 partial_structure.json 的 accepted_chunk_results 中。

| 顺序 | section_id | 主题 | 作用 | 论证动作 | 原文锚点 |
|---|---|---|---|---|---|
{rows}

前三个分块通过本地校验，共 9/15 个区域、8/10 个原文产品介绍位置；覆盖 O0001–O0061，共 61/84 个锚点（{61/84:.2%}），顺序无误、无重复。O0062–O0084 共 23 个锚点尚未通过验收。第一产品位置 AS-O0003，原文 O0003–O0033，保持跨段落产品边界。未执行新文章自有产品槽绑定和写作。

## 具体失败证据

第四分块 chunk-003/primary 的 AS-O0070 应返回单锚点 ["O0070"]，真实返回 ["O0070","O0070"]，触发 Source anchor/range/dependency differs from plan。同一条还返回 role_status=needs_check，该处角色尚未获得完整确认。

候选执行整块回退策略，从 AS-O0062 开始恢复。chunk-003/recover-AS-O0062 虽然 finish_reason=stop 且 JSON 可解析，却在顶层多返回了 units，并复制原文 blocks，违反精简 Schema，触发 Structure schema fields missing or unexpected。该区域一次恢复已耗尽，后续恢复及第五分块均未发送。未把收到但未通过验证的内容纳入有效覆盖。

article_structure.json 是冻结候选实际输出的 structure_incomplete 状态文件，sections=[]，不是完整结构合同。真实已通过的9个区域单独保存在 partial_structure.json；完整5次答复保存在 api_calls.json 指向的答复目录。本轮没有通过结构验收，没有触发 Writer。

## 费用、预算恢复与保护

新增费用 {cost['new_cost_known_cny']:.8f} 元；排行01累计 {cost['article_cumulative_after_cny']:.8f} 元；scope累计 {cost['scope_cumulative_after_cny']:.8f} 元；当日累计 {cost['daily_cumulative_after_cny']:.8f} 元。scope剩余 {cost['scope_remaining_cny']:.8f} 元、每日剩余 {cost['daily_remaining_cny']:.8f} 元。临时1.02元单篇累计配置已恢复为0.35元，原始任务文件未改动；恢复后本篇可新增执行额度为0。

原有全部2006条费用记录逐条不变，本轮新增5条且均已结算；3笔历史未知请求未改、未重发，无新增未知请求。原稿、原任务修订次数、冻结候选和输入来源均核验不变。没有部署、重启生产服务，也没有启动正文、审稿、返修或Word生成。

## 下一步最小修复建议（未实施）

单锚点应由程序保留唯一的可信区间，或只对完全相同且重复的首尾端点做可审计的等价归一化；不得接受不同锚点。恢复提示应将输入 units 与唯一输出 schema 更明确隔离，避免模型回显来源字段。needs_check 仍须保留为待确认，不能静默放行。以上需独立候选修复及后续授权，不能用本轮离线判断冒充真实恢复通过。

本次到此停止，不额外修改候选或重复付费请求。
'''
(root/'acceptance_summary.md').write_text(text,encoding='utf8')
assert sha(root/'article_structure.json')==article_sha
files={str(p.relative_to(root)):{'sha256':sha(p),'bytes':p.stat().st_size,'server_path':str(p)} for p in sorted(root.rglob('*')) if p.is_file() and p!=root/'output_manifest.json'}
save('output_manifest.json',{'run_id':root.name,'status':'structure_incomplete','files':files})
archive=Path('/tmp')/(root.name+'.zip')
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(root.rglob('*')):
  if p.is_file():z.write(p,str(p.relative_to(root)))
print(json.dumps({'root':str(root),'archive':str(archive),'archive_sha256':sha(archive),
 'completion_calls':5,'known_cost_cny':cost['new_cost_known_cny'],'coverage':'61/84','accepted_regions':'9/15',
 'manifest_sha256':sha(root/'output_manifest.json'),'required_files':{n:files[n] for n in ('article_structure.json','structure_validation.json','api_calls.json','cost_ledger.json','acceptance_summary.md','partial_structure.json')}},ensure_ascii=False))
