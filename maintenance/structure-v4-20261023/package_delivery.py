"""Offline evidence/summary packaging after the real V4 run has stopped."""
import hashlib,json,shutil,sys,zipfile
from pathlib import Path
sys.dont_write_bytecode=True
def deny(event,args):
 if event in ('socket.connect','socket.getaddrinfo','socket.sendto'):raise RuntimeError('Offline delivery only')
sys.addaudithook(deny)
root=Path(sys.argv[1]);base=Path('/opt/monitor/geo-capture/maintenance/20261023-structure-v4-final')
sys.path[:0]=[str(base/'isolated/current/engine'),str(base/'isolated/current')]
from geo_source_cards import structure_protocol as sp,structure_analyzer as sa
read=lambda p:json.loads(Path(p).read_text('utf8'));sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
auth=read(root/'preflight.json');value=read(root/'article_structure.json');before=sha(root/'article_structure.json')
data=sa.source_input(root/'article/writer',read(root/'article/writer/knowledge.json'));sp.verify(value,data)
summary=read(root/'summary.json');cost=read(root/'cost_ledger.json');api=read(root/'api_calls.json');tests=read(base/'linux-results.json')
assert value['status']=='structure_ready_with_checks' and api['real_completion_calls']==1
assert summary['validation']['covered_anchors']==84 and len(summary['validation']['products'])==10
assert summary['restoration']['shared_exactly_restored'] and all(summary['preservation'][k] for k in ('protected_unchanged','old_ledger_rows_unchanged','new_rows_only_this_run','unknown_preserved'))
assert all(sha(p)==h for p,h in auth['protected_before'].items())
for name,h in read(base/'manifest.json')['execution_source_sha256'].items():assert sha(base/'isolated/current'/name)==h
initial=root/'initial_delivery';initial.mkdir(exist_ok=False)
for n in ('acceptance_summary.md','output_manifest.json'):shutil.copy2(root/n,initial/n)
proof=root/'candidate_evidence';proof.mkdir()
for n in ('manifest.json','candidate.diff','linux-results.json'):shutil.copy2(base/n,proof/n)
shutil.copytree(base/'logs',proof/'logs')
shutil.copytree(base/'candidate-source',proof/'candidate-source')
legacy=Path(auth['legacy_run']);legacy_proof=root/'legacy_v3_evidence';legacy_proof.mkdir()
for p in (legacy/'article/writer/structure_calls/compact-v2').rglob('*'):
 if p.is_file():
  dest=legacy_proof/p.relative_to(legacy/'article/writer/structure_calls/compact-v2');dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
legacy_partial=read(legacy/'partial_structure.json')
(root/'previous_9_regions.md').write_text('# V3已通过的9个真实区域（本轮未重跑）\n\n'+'\n'.join(f"- {s['section_id']} | {s['role']} | {s['topic']} | {s['purpose']} | {','.join(s['moves'])} | {'—'.join(s['anchors'])}" for s in legacy_partial['accepted_sections']),encoding='utf8')
move={'question':'提问','define_scope':'界定范围','explain':'解释','compare':'比较','qualify':'限定条件','describe':'描述','answer':'回答','conclude':'收束'}
role={'opening':'引言','subject':'产品介绍','comparison':'横向比较','body':'正文','criteria':'比较标准','summary':'结尾','unknown':'待核对'}
rows='\n'.join(f"| {s['order']} | {s['id']} | {s['topic']} | {role[s['role']]}{'（待核）' if s['role_status']=='needs_check' else ''} | {s['purpose']} | {'、'.join(move[m] for m in s['moves'])} | {'—'.join(s['anchors'])} |" for s in value['sections'])
first=next(s for s in value['sections'] if s['id']=='AS-O0003');blocks={b['id']:b for b in data['blocks']}
questions='\n'.join(f"- {a}：{blocks[a]['text']}" for a in first['subsection_anchors'])
files=read(base/'manifest.json')['files'];source_shas='\n'.join(f"- {n}：`{v['sha256']}`" for n,v in files.items())
regressions=[]
for t in tests:
 regressions.append(f"| {t['suite']} | {t['tests']} | {t['tests']-len(t['failures'])-len(t['errors'])-len(t['skips'])} | {len(t['failures'])} | {len(t['errors'])} | {t['network_attempts']} |")
total=sum(t['tests'] for t in tests);nonpass=sum(len(t['failures'])+len(t['errors']) for t in tests)
text=f'''# 排行01 V4结构分析真实验收

候选：candidate-structure-recovery-v4-20261023。运行编号：{root.name}。

**15个区域、84/84个锚点完整覆盖，10个原文产品介绍位置均已识别；状态为structure_ready_with_checks，保留2处角色待核对，不是无条件通过，也不代表文章质量通过。**

本轮只新增1次DeepSeek真实生成调用和1次发送前余额检查。新增答复finish_reason=stop，prompt_tokens=1317、completion_tokens=246、缓存命中256；真实答复、请求参数及原始HTTP响应保留在article/writer/structure_calls/compact-v2/chunk-004/primary。新增已知费用{cost['new_cost_known_cny']:.8f}元，按现有价格规则从真实usage计算；不等同独立供应商账单。

此前5次真实调用费用0.02588384元仍完整保留，本轮没有重新运行前三个成功分块。经严格来源和协议迁移，复用前4块的真实初始答复：前三块内容不改，第四块仅将AS-O0070的["O0070","O0070"]确定性归一化为["O0070"]。旧的带units非法恢复答复只留作失败证据，没有冒充成功。本轮与此前V3结构调用合计6次、已知费用{cost['new_cost_known_cny']+.02588384:.8f}元。

## 完整真实结构

文章主题：{value['article_topic']}。

文章目的：{value['article_purpose']}。主题和目的沿用第一块真实答复，其他区域来自对应真实模型答复，程序只校验、归一化、按顺序合并；未人工补写结构语义。

| 顺序 | ID | 章节主题 | 角色 | 作用 | 论证动作 | 来源锚点 |
|---|---|---|---|---|---|---|
{rows}

产品介绍位置为AS-O0003、0034、0038、0042、0046、0050、0054、0058、0062、0066，对应区域均为subject/inferred。第一产品AS-O0003完整覆盖31个原文锚点O0003—O0033，内部7个问答保留在同一产品区域：

{questions}

以上问答标题仅表示原文组织方式，不授予新产品任何原品牌属性或功效。确定性绑定探针确认自有产品仍绑定AS-O0003，未绑定引言；编译前后所有产品身份、claim_ids权限一致，详见product_binding_validation.json。该探针未启动Writer。

## 两处待核对及安全处理

- AS-O0070，多维度评分对比的引入：真实role=comparison，role_status=needs_check。
- AS-O0084，免责声明：本轮真实role=unknown，role_status=needs_check；程序原文角色提示为summary，但没有把模型未知状态强行改成确定结尾。

两处原文位置、章节ID及前后顺序均完整保留。模型没有返回具体的角色存疑原因，记录明确注明“模型标为待核对，wire schema未提供详细原因”，没有编造解释。两处binding_allowed均为false，均不属于原文产品区域，不影响已识别的10个产品身份；不得用于产品槽绑定。本轮结构覆盖和顺序通过，但角色尚未全部确认；现有Writer仍有ready状态保护，本次也未启动。

## V4最小修复与零调用验证

仅修改structure_protocol.py、structure_analyzer.py，新增test_structure_v4.py。V3冻结源码、旧答复、失败记录和原稿未覆盖。新候选源码SHA：

{source_shas}

- 仅在期望单锚点且实际为同一锚点重复两次时去重，保留原始响应、前后值、理由和SHA。不同、缺失、越界、逆序或多点错误仍拒绝。
- 恢复提示把唯一输出合同与单个失败区域资料隔离，不注入整文、旧任务提示或其他区域。新恢复提示/解析器通过零调用故障测试，本轮真实执行未触发恢复，不能声称新恢复请求已通过真实模型验收。
- needs_check原样保留且阻断相关绑定；不确定产品位置保留占位，防止后续产品前移。结构可完整保存为with_checks，不会静默签发无待核的ready。
- 复用必须显式迁移，核验V3固定代码SHA、原始来源、知识库、产品资料、请求参数、原始答复和目标Schema；新输入指纹包含协议代码、角色代码、来源文件及元数据。实质变化后旧结果失效，未知请求不重发。

目标Linux零调用回归：

| 测试组 | 执行 | 通过 | 失败 | 错误 | 外连尝试 |
|---|---:|---:|---:|---:|---:|
{chr(10).join(regressions)}

合计{total}项执行、{total-nonpass}项通过、{nonpass}项未通过，未修改旧测试断言。旧V3的1项仍要求“不确定产品角色导致整份structure_incomplete”，与本轮明确允许结构保留待核对的规则冲突；另2项旧夹具在结构生成后才创建或替换knowledge/product，触发了新输入指纹保护。失败原文保留在candidate_evidence/logs/linux-v3.log；不是全部回归通过。V4新增16项包含在资料预先存在条件下的真实历史绑定、全部声明权限及完整原文保留检查，均通过；B1/B2相关54、引擎288、创作78均通过。

## 预算、历史保护及执行边界

剩余阶段发送前含全部潜在恢复的预留上界0.058118元。沿用原任务{auth['original_job_id']}、scope {auth['scope']}，没有新建计费身份。临时共享/隔离任务单篇累计上限1.02元，scope5.25元、每日10元；结束后配置恢复到原值。原始任务文件、修订次数、全部旧费用行、3笔旧未知请求、V3冻结源码和运行证据逐项核验未变。

本轮费用{cost['new_cost_known_cny']:.8f}元；排行01累计{cost['article_cumulative_after_cny']:.8f}元，scope累计{cost['scope_cumulative_after_cny']:.8f}元，当日累计{cost['daily_cumulative_after_cny']:.8f}元。没有失败付费请求，没有新增未知请求。共享单篇恢复0.35元后本篇可新增执行额度为0；这不是供应商账户余额结论。

没有运行Writer、Reviewer、仲裁、内容返修、Word生成或生产部署。结构结果已完整保存，到此停止。文章事实、逻辑质量及无人值守闭环仍未真实验收，两个待核角色和旧测试夹具/规则冲突继续保留。
'''
(root/'acceptance_summary.md').write_text(text,encoding='utf8')
assert sha(root/'article_structure.json')==before
files={str(p.relative_to(root)):{'sha256':sha(p),'bytes':p.stat().st_size,'server_path':str(p)} for p in sorted(root.rglob('*')) if p.is_file() and p!=root/'output_manifest.json'}
(root/'output_manifest.json').write_text(json.dumps({'run_id':root.name,'status':value['status'],'files':files},ensure_ascii=False,indent=2),encoding='utf8')
zpath=Path('/tmp')/(root.name+'.zip')
with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED) as z:
 for p in sorted(root.rglob('*')):
  if p.is_file():z.write(p,str(p.relative_to(root)))
print(json.dumps({'root':str(root),'archive':str(zpath),'archive_sha256':sha(zpath),'manifest_sha256':sha(root/'output_manifest.json'),
 'status':value['status'],'calls':1,'cost':cost['new_cost_known_cny'],'sections':len(value['sections']),'coverage':'84/84',
 'main_files':{n:files[n] for n in ('article_structure.json','structure_validation.json','api_calls.json','cost_ledger.json','acceptance_summary.md','product_binding_validation.json')}},ensure_ascii=False))
