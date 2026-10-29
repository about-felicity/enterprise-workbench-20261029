"""Preserve real rejected prose and explicit incomplete status. Zero API calls."""
import hashlib,json,shutil,sys,zipfile
from pathlib import Path
def deny(event,args):
 if event in ('socket.connect','socket.getaddrinfo','socket.sendto'):raise RuntimeError('Offline packaging')
sys.addaudithook(deny)
root=Path(sys.argv[1]);read=lambda p:json.loads(Path(p).read_text('utf8'));sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
auth=read(root/'preflight.json');plan=read(root/'execution_plan.json');summary=read(root/'summary.json')
assert summary['status']=='writer_technical_failure' and summary['real_model_calls']==3
assert summary['settings_restored'] and all(summary['preservation'][k] for k in ('old_rows_unchanged','protected_unchanged','unknown_preserved','original_job_unchanged'))
for p,h in auth['protected_before'].items():assert sha(p)==h
received=[];folder=root/'received';folder.mkdir(exist_ok=False)
for p in sorted(root.glob('article/writer/section_calls/INTRO/attempt-*/response.json')):
 v=read(p);draft='# '+v['title']+'\n\n'+'\n\n'.join(x['text'] for x in v['paragraphs'])+'\n'
 out=folder/('INTRO-'+p.parent.name+'.md');out.write_text(draft,encoding='utf8')
 failure=read(p.parent/'section_failure.json');answer=read(p.parent/'answer.json')
 received.append({'attempt':p.parent.name,'raw_response_sha256':sha(p),'markdown':str(out),'failure':failure,'finish_reason':answer['finish_reason'],'usage':answer['usage'],
  'characters':sum(len(x['text']) for x in v['paragraphs'])})
assert len(received)==3
latest=folder/'INTRO-attempt-2.md';shutil.copy2(latest,root/'draft.md')
acceptance={'status':'writer_failed_partial_intro_only','complete':False,'accepted_components':[],'received_components':['INTRO'],
 'received_attempts':received,'missing_components':[t['id'] for t in plan['tasks']],'body_sections':0,'expected_body_sections':15,
 'generated_article_complete':False,'draft_origin':'Last real received INTRO response, unchanged; rejected by character ceiling, not an accepted or complete first draft.',
 'draft_sha256':sha(root/'draft.md'),'intro_limits':plan['tasks'][0],'pending_roles':['AS-O0070','AS-O0084'],
 'pending_role_body_not_generated':True,'owned_product_body_not_generated':True,'not_quality_approved':True,'no_review_executed':True}
(root/'writer_acceptance.json').write_text(json.dumps(acceptance,ensure_ascii=False,indent=2),encoding='utf8')
manifest=read(root/'writer_manifest.json');manifest['accepted_components']=[];manifest['received_but_rejected']=received;manifest['status']='incomplete';manifest['draft_sha256']=sha(root/'draft.md')
(root/'writer_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
(root/'review_status.json').write_text(json.dumps({'fact_review':'not_started','logic_review':'not_started','reason':'Writer exhausted INTRO attempts; no complete draft exists. No review pass/failed verdict is fabricated.','no_arbitration_no_repairs':True},ensure_ascii=False,indent=2),encoding='utf8')
cost=read(root/'writer_cost_ledger.json');summary['writer_acceptance']=acceptance
(root/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
tests=auth['legacy_tests'];test_rows='\n'.join('- '+name+'：'+reason.splitlines()[-1] for name,reason in tests['failures']+tests['errors'])
text=f'''# 排行01 V4首稿真实执行结果

运行编号：{root.name}。候选candidate-structure-recovery-v4-20261023的结构、知识库和原始来源版本核验通过；未重新调用Structure Analyzer。

**本次Writer失败，停在INTRO；已收到三份真实导语，0个组件通过，15个主体区域及END均未生成。draft.md是最后一次真实导语原文，不是完整文章，也没有通过长度合同。**

## 执行前检查与合同

原结构为structure_ready_with_checks，15个区域、84个锚点完整。读取了V4结构、校验、费用账本及V3 partial_structure.json。旧前三块9个区域与当前结构一致。小绿瓶继续绑定AS-O0003，原有11条自有产品声明及全部产品身份和权限保持。

按本次明确要求建立INTRO+15区域+END隔离执行清单；原冻结Compiler的12节计划、原始知识库和账本未覆盖。派生合同保留parent_sha256，所有claims、evidence和每个产品的claim_ids不变。AS-O0070和AS-O0084仍needs_check，不绑定产品；相关正文因为INTRO失败未执行。

三项旧V3测试具体名称及实际失败：

{test_rows}

第一项旧断言要求不确定角色使整份结构失败，与V4明确的with_checks策略不符；后两项在结构分析后才创建/替换知识库及产品资料，触发Stale compact structure knowledge/research inputs。真实资料在生成前已存在且通过校验，冻结Writer实际通过该入口并发出了三次请求。未删除断言、未改变事实/逻辑质量标准。本次真正的Writer失败出现在后续导语校验。

## 三次真实答复及失败

1. attempt-0：正常stop，509输出tokens。第2段标为inference但claim_ids为空，被现有声明校验拒绝。该段主要说明本文范围；模型在下一次调整了声明类别，程序没有自动替它改标签或放宽规则。
2. attempt-1：正常stop，488输出tokens。494汉字，低于500汉字下限，差6汉字。
3. attempt-2：正常stop，718输出tokens。扩写后856字符，超过分配给INTRO的722字符上限，超出134字符。

现有单节最多3次尝试耗尽，系统停止，没有发送第4次，没有重置旧任务或尝试次数。三份原始JSON、Markdown、请求参数、原始HTTP、usage和失败理由全部保存。没有输出截断或未知发送。

真实导语标题：哪个牌子的防脱洗发水好：从配方记录看十款防脱洗发水。

三份可读导语见received/INTRO-attempt-0.md、INTRO-attempt-1.md、INTRO-attempt-2.md。draft.md与最后一次原文完全一致，未手工补写、裁剪或改写。

## 审稿与后续状态

首稿没有完整生成，因此事实审稿和独立全文逻辑审稿均未启动；没有fact_review.json或logic_review.json，review_status.json明确记为not_started。不能对未生成的主体作事实/逻辑通过判断，也没有以导语审查冒充整篇审稿。没有仲裁、内容返修、Word完整文章或生产部署。

## 费用与保护

执行前初始17个写作组件+2审稿预留2.630944元，含所有写作尝试上界6.584800元，低于沿用的剩余新增授权7.14994172元。只临时设置单篇累计7.29元、隔离任务scope累计11.26元，均在此前8元/12元授权边界内，每日10元未改。

本轮3次真实生成调用，另有3次发送前余额检查。新增已知费用{cost['known_new_cost_cny']:.8f}元；排行01累计{cost['article_cumulative_cny']:.8f}元，scope累计{cost['scope_cumulative_cny']:.8f}元，当日累计{cost['day_cumulative_cny']:.8f}元。费用为真实usage按现有规则计算的账本估算，不是独立供应商账单。

临时配置已恢复；原任务文件、原稿、全部历史账本行、结构候选、产品资料及3笔旧未知请求核验不变。本轮3笔均已结算，无新增未知请求，未创建新计费任务或scope。

## 尚未完成

15个主体区域、END、完整首稿及两次独立审稿均未完成。直接原因是Writer导语的声明类型和双重长度合同未能在3次真实答复内同时满足。后续若继续，应在独立修复版本中处理分类指令和长度纠错，不能在本轮暗中放宽阈值、人工裁剪或重置尝试后继续付费。
'''
(root/'acceptance_summary.md').write_text(text,encoding='utf8')
files={str(p.relative_to(root)):{'sha256':sha(p),'bytes':p.stat().st_size,'server_path':str(p)} for p in root.rglob('*') if p.is_file() and p!=root/'output_manifest.json'}
(root/'output_manifest.json').write_text(json.dumps({'status':'writer_failed_partial_intro_only','files':files},ensure_ascii=False,indent=2),encoding='utf8')
zpath=Path('/tmp')/(root.name+'.zip')
with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED) as z:
 for p in root.rglob('*'):
  if p.is_file():z.write(p,str(p.relative_to(root)))
print(json.dumps({'root':str(root),'archive':str(zpath),'archive_sha256':sha(zpath),'manifest_sha256':sha(root/'output_manifest.json'),
 'status':'writer_failed_partial_intro_only','calls':3,'new_cost_cny':cost['known_new_cost_cny'],'draft_sha256':sha(root/'draft.md')},ensure_ascii=False))
