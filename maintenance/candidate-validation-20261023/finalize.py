"""Freeze verification and human report; does not mutate implementation/history."""
import hashlib,json,math,subprocess
from datetime import datetime,timedelta,timezone
from pathlib import Path
from zoneinfo import ZoneInfo
D=Path(__file__).resolve().parent;B=D.parents[1];C=B/'maintenance/real-acceptance-20261022/candidate-source'
read=lambda p:json.loads(Path(p).read_text('utf8'))
frozen=read(D/'frozen-manifest.json');before,after=read(D/'audit-before.json'),read(D/'audit-after.json');replay=read(D/'replay-results.json');budget=read(D/'budget-plan.json')
checks={}
for name,record in frozen.items():
 if name=='evidence_archive':continue
 actual=hashlib.sha256((C/name).read_bytes()).hexdigest();assert actual==record['candidate_sha256']
 live=after['sources'][Path(name).name]['stage_sha256'] if name.startswith('geo_source_cards/') else after['tests'][Path(name).name]
 assert live==actual
 if name.startswith('geo_source_cards/'):assert after['sources'][Path(name).name]['production_sha256']==record['production_sha256']
 checks[name]={'sha256':actual,'matches_frozen':True,'matches_previous_server_stage':True}
assert before['sources']==after['sources'] and before['ledger']==after['ledger']
assert before['original_hashes_current']==after['original_hashes_current'] and after['originals_match_previous']
assert before['shared_settings']==after['shared_settings'] and before['acceptance_control']==after['acceptance_control']
assert frozen['evidence_archive']['sha256']==hashlib.sha256((B/'maintenance/real-acceptance-20261022/evidence.zip').read_bytes()).hexdigest()
engine,creation=read(D/'engine-regressions-linux.json'),read(D/'creation-regressions-linux.json')
assert engine['tests']==288 and creation['tests']==78 and not any(v['failures'] or v['errors'] for v in (engine,creation))
proof={'at':datetime.now(timezone(timedelta(hours=8))).isoformat(),'frozen_files':checks,'production_unchanged':True,'originals_unchanged':True,
 'ledger_rows_before':before['ledger']['rows'],'ledger_rows_after':after['ledger']['rows'],'ledger_rows_sha256':after['ledger']['rows_sha256'],
 'ledger_and_scope_rows_unchanged':True,'unknown_requests_unchanged':True,'budget_settings_unchanged':True,'acceptance_control_unchanged':True,
 'new_api_calls':0,'new_cost_cny':0,'linux_regressions':{'engine':engine,'creation':creation},'candidate_ready_for_real_acceptance':False,'blocker_ids':[v['id'] for v in replay['blockers']]}
(D/'verification.json').write_text(json.dumps(proof,ensure_ascii=False,indent=2),encoding='utf8')
hashrows='\n'.join(f"| {name} | `{record['sha256']}` |" for name,record in checks.items())
phase_names={'structure':'结构分析','sections':'逐节生成（含导语、结尾）','facts':'事实审稿','logic':'独立逻辑审稿','arbitration':'独立仲裁（26意见、9批）'}
phase_rows=[]
for a,b in zip(*[v['phases'] for v in budget['samples']]):
 phase_rows.append(f"| {phase_names[a['stage']]} | {a['initial_calls']}/{b['initial_calls']} | {a['estimated_initial_cny']:.4f}/{b['estimated_initial_cny']:.4f} | {a['initial_reservation_upper_cny']:.6f}/{b['initial_reservation_upper_cny']:.6f} |")
x,y=budget['samples'];phase_rows='\n'.join(phase_rows)
text=f'''# 候选修复零调用验证与真实验收准备

核验时间：{proof['at']}（北京时间）。**本轮新增API请求0、费用0、生产部署0；真实文章合格仍为上一轮0/2。候选源码保持冻结，发现两处阻断缺陷，暂不进入真实调用。**

## 一、冻结与生产差异

6份文件的本地SHA、上轮服务器隔离stage SHA一致；4份生产文件仍为上轮旧版。详细差异已保存为 `candidate-v-production.diff`，完整冻结清单为 `frozen-manifest.json`，复核证据为 `verification.json`。

| 冻结文件 | SHA256 |
|---|---|
{hashrows}

四份源码分别修复：KU过滤后保留产品槽且不回填其他产品事实；把原文产品事实从写作要求中抽离；分节继承返修要求、分配字符预算、恢复已返回的标题格式；将仲裁按每批3条拆分并保留完整上下文及已完成批次。

没有改动这6份文件，没有安装新架构或增加Agent。没有改生产、重启服务、创建新计费任务、覆盖原稿或清零修订次数。原始文件哈希仍与上轮授权基线一致；canonical费用账本前后均2004条，全部行和scope行摘要一致，原3笔未知ID与预留保持不变。共享预算、失败版本暂停状态和active空状态保持。第三部分的费用上限只是测算条件，未写入设置。

## 二、零调用验证范围与结果

本地隔离目录从受控生产源码快照复制基础模块，再覆盖6份冻结候选；输入来自上轮 `evidence.zip` 的593份已保存文本/JSON。原归档SHA保持。历史答复的原始输入与新候选Prompt不同，**只把答复作为重放输入测试解析与拒绝行为，绝不把它当成可直接复用的新正文或新合格稿**。

隔离进程阻止外部socket和未Mock的HTTP请求。Linux回归另外使用 `unshare -n`；仅下载接口测试在独立网络命名空间内启用回环设备，没有外网路由，也未访问生产接口。没有读取API密钥或查询余额接口。

| 检查项 | 实际结果与边界 |
|---|---|
| 自有产品身份 | 两篇S2均恢复为道和小绿瓶，只绑定PF1—PF11；未从竞品KU补齐。排行仍READY_WITH_LIMITS、测评READY。 |
| 跨产品资料 | 全部产品节的声明subjects与该节产品一致；NO_INSERT不释放PF。3个品类的合成回归通过。语义性偷换仍须真实独立审稿，不能只靠ID证明事实。 |
| 原品牌/价格/功效/测试数据 | 两份保存结构的具体required_content没有原样进入新章节要求；保留原始结构及来源供审稿。仍发现下述B1角色映射缺陷。 |
| 主体完整与篇幅 | 排行12节主体+导语结尾共14组件；测评13节主体+导语结尾共15组件。空主体、缺节、顺序、重复、截断及空段回归通过；候选本地字符预算能拒绝历史测评的多处超长章节。 |
| 数量 | 最终名单分别10款、11款；旧稿的数量矛盾能定位（排行P022、测评P001）。旧排行第一款身份仍被拒绝。旧测评按结构化答复展开为7225字符、6154正文汉字，超过6000；这是重放展开文本口径，不改写上轮7047正文字符统计。 |
| 标题格式 | `title`/冻结topic可恢复已生成主体的展示标题；不补正文。对应回归包括已保存缺heading答复本地恢复、零额外请求。 |
| 分节返修 | 返修要求进入每节输入及恢复指纹；更换返修要求使旧状态失效。超长仅重试该节，已有成功节保留。 |
| 仲裁覆盖 | 真实初审16条事实意见、逻辑及本地意见合计26条；按3/3/3/3/3/3/3/3/2分为9批，26个ID完整且唯一，所有批次读完整正文与资料。 |
| 仲裁续跑与版本 | 已完成9批复读新增Mock调用0；改变正文、知识库或原始来源时，分批输入校验均拒绝旧状态。最终缓存快路径仍有B2缺陷。 |
| 保护 | 未知批次不重发、请求指纹、预算拒绝、并发锁、两轮上限与失败状态相关回归保留。两份真实材料重放的attempts=2均路由REPAIR_EXHAUSTED。 |

历史正文重放进入逐节执行器后，两篇均以 `section_generation_exhausted` 停止：这是预期拒绝旧的不合格答复，**不是候选已生成或已修好两篇文章**。排行旧答复不能绑定新合同，S2有未分配声明；测评多个旧段超过新字符上限。

仲裁覆盖测试使用真实初审意见，但其返回decision为明确标注的合成 `needs_check` 占位。它只验证分批、证据定位格式、恢复与版本失效，**没有验证模型仲裁判断是否正确**，没有给正文签发合格结论。

### 新阻断B1：已有结构分析的角色识别不稳定

复用测评02已保存、SHA有效的article_structure时，AS002实际上是第一个产品的介绍：“以第一名身份完整展示首迷的综合资质、配方体系、功效、安全性与使用体验”。候选abstract_task将AS002—AS011全部判为body，未识别成产品叙述角色；bind随后按位置分配，把新稿自有产品S2绑定到了AS001开场，而不是AS002。另一次保存的原始API答复写有“推介第一名产品”，重放后能映射AS002，说明问题取决于角色描述措辞，已有单个成功案例不足以证明通用正确。

最小修复范围：只修structure_analyzer的角色归一化和绑定规则，用原文产品区块与分析顺序共同识别产品叙述；同时回归这两种真实分析描述。保留抽象事实边界，不把原首迷属性变成新产品属性。**本轮仅报告，未修改冻结候选。**

### 新阻断B2：原始来源变化未使最终审稿快路径失效

在隔离副本中用保存的真实初审+合成仲裁走完本地处理，随后只改变research_result.json的原始知识来源，保持正文、knowledge、product不变。再次调用review_quality.process时，其quality_pipeline缓存分支直接返回旧结果，未重建原始来源指纹。底层batched检查能拒绝新来源，但快路径绕过了它。

最小修复范围：最终审稿证书和缓存校验都纳入真实原始来源摘要；复用及终验重新读取来源，比对失败后旧审稿/仲裁失效。必要时把来源摘要显式传给终验，禁止仅依赖knowledge/product摘要。新增来源单独变化、正文变化、证据变化三组回归。**本轮未改review_quality或冻结候选。**

## 三、测试结果

- Linux同环境引擎：288项通过，0失败、0错误、0跳过。
- Linux同环境创作：78项通过，0失败、0错误、0跳过。合计366项相关自动化回归，包括冻结候选新增9项。
- 不是整个项目全套测试，也不是新增366条测试。日志为 `engine-regressions-linux.log`、`creation-regressions-linux.log`。
- Windows首次扩展运行278项通过，另2个加载/执行错误均因本机旧web_collectors缺少PreSubmissionPageError；未改测试断言，转服务器同环境跑，含原来无法加载的模块共288项通过。
- 最初全禁socket时2项本地HTTP下载测试被拦截；保留strict-network日志，再在无外网的独立命名空间仅放行127.0.0.1回环，78项通过。未放行真实API。
- B1/B2来自额外真实资料重放，不在原回归覆盖内；**366项通过不代表候选可进入真实验收**。

## 四、下一轮费用评估（只准备，禁止发送）

沿用代码现有价格版本{budget['price_rule']['version_date']}：输入未命中2元/百万token、缓存命中0.04元/百万token、输出8元/百万token。预算预留按峰值、不假定缓存或半价；这不是供应商精确账单或新价格查询。

正常首轮场景：结构分析1次、排行14/测评15次分节、事实审稿1次、独立逻辑1次；以测评真实26条意见为两篇的容量估算，各需9批仲裁，共排行26次、测评27次。排行新审稿意见数量尚未知，不能把26当成其真实结果。

下表数值顺序均为 **排行01 / 测评02**，单位元。usage投影用保存答复的token/UTF8比例与输出量推算，忽略缓存优惠；保守预留按真实代码的UTF8字节上界+输出max_tokens计算。后者明显高于常见实际扣费，**不是建议直接把预算调到该金额**。

| 阶段 | 首轮调用数 | usage投影费用 | 首轮保守预留上界 |
|---|---:|---:|---:|
{phase_rows}
| 首轮合计 | 26/27 | {x['expected_initial_cny']:.4f}/{y['expected_initial_cny']:.4f} | {x['initial_full_output_reservation_upper_cny']:.6f}/{y['initial_full_output_reservation_upper_cny']:.6f} |

包含故障与两轮修订的压力上界：

| 项目 | 排行01 | 测评02 |
|---|---:|---:|
| 结构分析第二次已知失败重试额外上界 | {x['structure_second_attempt_extra_cny']:.6f} | {y['structure_second_attempt_extra_cny']:.6f} |
| 所有章节各补生成最多2次的额外上界 | {x['all_components_two_supplement_attempts_extra_cny']:.6f} | {y['all_components_two_supplement_attempts_extra_cny']:.6f} |
| 每轮返修（按最贵全节重写+完整复审） | {x['one_repair_full_upper_cny']:.6f} | {y['one_repair_full_upper_cny']:.6f} |
| 两轮返修及全部复审合计 | {x['two_repairs_full_upper_cny']:.6f} | {y['two_repairs_full_upper_cny']:.6f} |
| 初写+补生成+两轮返修的总压力上界 | {x['total_full_upper_cny']:.6f} | {y['total_full_upper_cny']:.6f} |

此上界有明确条件：每节最多3次尝试，最多两轮内容修订，每次审稿最多30条意见、每批3条仲裁；首轮3类审稿故障即停，不盲目重发。输入字节上限逐阶段见budget-plan.json（历史最大值加16KiB余量、向上取4KiB整块）。**这些只是拟议执行前校验条件，未安装或部署**。未来输入超过上限或意见超过30条时，必须发送前停止、保留全部资料并重算，不能截证据或漏意见。没有这些条件，不能从历史体积推出无条件费用上界。最多164/173次为极端压力场景，非建议正常调用数。

真正执行时优先段落补丁，跨节问题扩大到必要章节；无法定位保留争议、排名标准失效重新规划。通常不会用满上界。但本阶段不能通过假定一次必过、只有一条意见或不需要返修来承诺现有预算可完成闭环。

### 现有限额与余额

| 项目 | 目前记录 |
|---|---:|
| 当前共享单篇硬上限 | 0.35元 |
| 当前共享每日硬上限 / 10月23日已有API占用 | 10元 / 0元 |
| 上轮隔离任务累计单篇上限 / 任务范围上限 | 2元 / 8元 |
| 排行历史累计 / 按2元计算剩余 | {x['historical_article_used_cny']:.8f} / {x['historically_authorized_article_remainder_cny']:.8f}元 |
| 测评历史累计 / 按2元计算剩余 | {y['historical_article_used_cny']:.8f} / {y['historically_authorized_article_remainder_cny']:.8f}元 |
| 同scope/task_day已占用 / 剩余 | {budget['scope_used_cny']:.8f} / {budget['scope_remaining_cny']:.8f}元 |
| 最后实际查询余额 | 2026-10-22 18:16约15.08元 |

共享上限和隔离任务上限取更小值，历史两篇费用都已超过当前0.35元，所以**目前允许新增费用为0，预算预检应当直接停止**。即使只比较上轮2元累计额度，其余量也不足以覆盖上述带必要审稿、仲裁、补生成和两轮修订的完整保守方案。两篇合计压力上界73.499216元，最后记录余额也不足以覆盖；这是极保守压力容量，不是本轮或下一轮实际消费。

15.08元是上轮最后查询，不是当前余额。本轮不调用余额API；隔离api/balance.json中的15.21元是更早缓存，不能覆盖最终查询记录。当前实时余额无法在本阶段确认。

**决定：不发送任何请求，不自动恢复临时2元/12元额度，不扩大预算，不清账，也不恢复已耗尽的旧验收版本。至少一个完整闭环目前没有可执行的预算保障。**

## 五、后续授权后的最小验收顺序与状态

这是一份待执行方案，当前不授权任何真实请求：

1. 先修B1/B2并生成新的冻结SHA，零调用复核通过后再提交费用评估。其余4份候选及原稿历史保留。
2. 只有明确批准新候选验收版本、额度及调用清单后，创建原job/scope下的隔离验收版本；不新建计费scope，不清零历史费用，不启动其余12篇，不重发3笔未知。旧失败版本保持两轮耗尽，不能直接当第三轮恢复。
3. 先排行01：资料与知识库版本核对→结构分析/可验证缓存→12节主体及导语结尾→完整性、身份、名单10款、事实边界检查→独立事实+逻辑审稿→所有争议完整仲裁→必要定点返修→当前版本复审。排行未完成有效闭环前不启动测评02。
4. 再测评02：13节主体及导语结尾，2800正文汉字起、导语至少500汉字、全文不超6000字符；包含自有产品共11款。独立审稿、争议仲裁和定点返修同上。
5. 每篇最多两轮内容修订；每轮后重验正文、原始来源、知识库、合同、审稿与仲裁版本。段落补丁必须实际改变错误、保留相邻上下文；变更后旧通过结论不可沿用。
6. 技术故障标technical_failure（空响应、截断、格式或执行错误）；审稿服务不可用标review_unavailable；有有效审稿但不合格标quality_rejected；有争议标needs_check并保留；预算不足标budget_blocked；未知发送标request_unknown并禁止重发。两轮耗尽标repair_exhausted/needs_attention，不签发通过。
7. 完成必须同时满足主体齐全、正确产品及来源、数量与篇幅、真实语义审稿、仲裁有原句和来源依据、返修有效、最终当前版本复审以及费用/状态一致。数据/风格偏好本身不构成拒稿，也不放松具体事实和真实逻辑错误。

原始抓取、KU/PF与原分析可在版本核验后复用，重复的确定性检查不调用模型；修稿后事实/逻辑复审不可省略。未通过任何一步都不得发布或部署候选。后续仍须明确授权，本轮到此停止。
'''
(D/'REPORT.md').write_text(text,encoding='utf8')
print(json.dumps({'proof':proof['at'],'frozen_files':len(checks),'tests':366,'blockers':proof['blocker_ids'],'new_calls':0,'report':str(D/'REPORT.md')},ensure_ascii=False))
