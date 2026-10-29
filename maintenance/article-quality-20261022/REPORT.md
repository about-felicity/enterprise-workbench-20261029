# 三个逻辑 Agent 改造与质量闭环验收

更新：2026-10-22 17:05:37（北京时间）。状态：**代码已修改、部署与同环境自动化回归通过；真实 API 小样本及跨日无人值守尚未验收。** 没有把 Mock、旧答复重放或 HTTP 检查当作真实文章质量通过。

## 1. 已确认根因

1. 排行01的付费原始响应以 `finish_reason=stop` 结束，输出1387 tokens，只有导语和结尾、`sections=[]`。既有程序会拒绝它，但 Writer 仍一次请求整篇长文，缺少逐节执行与补生成机制。不是 ZIP、JSON 解析或网络截断导致该次空主体。
2. 事实失败会跳过全文逻辑审稿。CL 编号及来源映射只能证明引用身份，不能证明正文的推论成立；先前缺少独立复核有争议意见的执行路径。
3. 原标题数量检查未覆盖正文中的总数，实际含自有产品11款的稿件仍写“十款”。局部修订后缺少统一的当前正文/材料版本终验。
4. 编译器已经允许 READY_WITH_LIMITS，但旧写作预检仍要求最少知识条数、每款中性资料、足量自有事实，造成前后策略冲突。本轮移除这组数量型阻断，保留来源逐字校验及真实事实约束。
5. 部分任务已无 active 执行，`api/health.json` 仍遗留 requesting，界面误显正在创作。返回答复待处理也没有单独显示。

## 2. 实际研究的参考源码与取舍

| 项目 | 本地版本/许可证 | 实际阅读的实现 | 采用的设计 |
|---|---|---|---|
| [Writing Agent](https://github.com/dongbeixiaohuo/writing-agent) | `041a70f043a29bba58a03e881c5f14f651e73b70`，MIT，Copyright 2025 Dante.sun | `packages/runtime/agent/src/index.ts`、`runtime/recovery/src/index.ts`、`runtime/session/src/index.ts`、`application/src/workflow-handoff.ts`、`agent-context.ts` 及相关测试结构 | 由程序绑定当前角色/阶段；版本及内容哈希校验；已持久化答复可恢复；未知外部结果不直接重试 |
| [Multi-Agent Content Studio](https://github.com/tornikepe/multi-agent-content-studio) | `9c5dd4eb778b57dcd8fe440d9f3c47278291e0fd`，MIT，Copyright 2026 Tornike Petriashvili | `backend/agents.py`、`orchestrator.py` 的 Writer→Reviewer→Editor→再审及有限循环 | 审稿结果结构化传递；返修后重新审稿；由程序限制循环 |

没有复制两个仓库的源代码，也没有新增它们的依赖、服务或前端。没有采用 Content Studio 的“失败后使用离线内容完成”策略，也没有采用分数决定全部质量、人工发布门或无限角色调度。原研究阶段的证据抽取归为 Analyzer 的资料准备子步骤；分类、编译、仲裁调度、验收均是普通程序，**没有第四个 Agent**。

## 3. 三个 Agent 的真实调用链

现有 URL/抓取清洗 → 原研究证据提取 → 程序校验来源/身份与可写性 → **Structure Analyzer** → 编译可写声明与结构任务 → **Article Writer**（长文逐节）→ 正文与来源映射 → **Article Reviewer**（事实子步骤 + 独立全文逻辑子步骤 + 必要的争议复核子步骤）→ 程序定点路由 → **Writer 返修** → **Reviewer 重新审当前版** → 程序终验。

| 角色 | 输入 | 输出及实际执行位置 |
|---|---|---|
| Structure Analyzer | 现有 primary_url 对应的真实 fetched 原文、原文段落 O 编号、当前体裁/任务提纲 | `article_structure.json`：主题、目的、引言/结尾策略、AS 稳定 ID、顺序、必要内容、目的、承接与原文锚点。`api_worker.execute` 在现代原文任务的完整写作之前调用。最多2次已知格式失败；原文可用时按实际标题/段落顺序降级，标明 degraded；未知发送不降级重发 |
| Article Writer | 结构、用户知识库生成的可写 CL/E 账本、任务及各章节约束、前文结尾与全文目标 | 长文生成 `INTRO → S清单 → END`，`section_calls/manifest.json`、各节 accepted/attempt 记录、assembled.json；最终 `draft.md`、Word、映射、writer_done。每节最多3次已知失败尝试，成功节保存；短文保留一次生成及完整性门槛。返修仍是此角色 |
| Article Reviewer | 当前完整正文、原文与结构、实际产品资料、可写声明、源文证据及用户要求 | 事实审核结果、独立逻辑证书、必要的证据复核证书与 `review.json`/result.json。问题有类型、严重程度、P/C定位、依据、原因、修复指令、正文/证据版本。最终交付保存 review.json 和 semantic_review.json |

Analyzer 结构绑定到已有 S 章节的 `structure_id/structure_task`，Writer 每节消费目的、必要内容、论证步骤和承接；不改变已冻结的产品身份、顺序和声明权限。原文锚点保存在分析/审稿材料里，Writer 的结构投影不携带来源原句，避免迁移原品牌事实。返修输入和新编译合同保留原结构。

## 4. 实际修改、合并与删除

以下路径相对于项目根目录；具体部署 SHA 见 `deployment-manifest.json`、`deployed-source.json`。共44个源码/回归文件部署，其中17个引擎文件、4个 creation 文件、23个引擎测试包文件（含 __init__）。未重写整个项目。

| 文件 | 操作及原因 |
|---|---|
| `geo-source-card-collectors/geo_source_cards/structure_analyzer.py` | 新增来源绑定、有限分析、真实段落降级、结构投影及 S 绑定 |
| `geo_source_cards/section_writer.py`（同上包目录） | 新增长文逐节执行、哈希/锁、成功节恢复、已知失败限次补写、未知保护、完整组装；自有产品节读取原详情配置 |
| `geo_source_cards/quality_checks.py` | 汇总程序可确定的数量/已知价格问题；成分外观推功效只生成待审语义候选，不冒充确定判决 |
| `geo_source_cards/review_quality.py` | 新增事实→全文逻辑→必要复核的执行顺序、持久化与最终版本门槛；事实不通过也执行逻辑检查，服务不可用不能生成通过标记 |
| `geo_source_cards/review_arbitration.py` | Reviewer 内部独立复核：确定错误、较充分依据、待核对、一般建议、风格；要求当前正文/来源逐字锚点并保存原审稿结果，不改 false 检查或 unsupported 声明为 true |
| `geo_source_cards/article_compiler.py` | 绑定结构、继承修订结构；完整文档模式拒绝空主体/缺节/顺序错误/空段/重复/明显未完成标记；保留历史仅校验引用身份接口 |
| `geo_source_cards/api_worker.py` | 接入实际三角色执行及长文分节；完整性先于交付；编译稿不套旧增量审稿合并；保存角色/章节清单；终态健康日志不再遗留 requesting |
| `geo_source_cards/consumer_prompts.py` | 审稿读取原始资料而非只看 CL；移除与编译器冲突的数量型严格阻断；**删除已被后文完整覆盖、无消费者的旧 Writer 提示词块及第二种输出协议注入**，保留唯一 document 投影与有调用方的历史 append 协议 |
| `geo_source_cards/api_prompts.py` | 编译文章独立全文审稿，历史稿仍支持原增量协议 |
| `geo_source_cards/argument_plan.py` | 将总产品数量校验扩大到正文的明确总数，排除容量、步骤及其余/其中等子集表述 |
| `geo_source_cards/article_logic.py` | 全文审稿读取原文与结构；审稿复核后有争议的合格审阅稿单独标记 qualified，原逻辑证书不伪造 passed |
| `geo_source_cards/deepseek_api.py` | 基础 API 客户端也提供独立逻辑审查，保留 CreationClient 的预算适配及全部请求保护 |
| `geo_source_cards/repair_router.py` | 校验仲裁/正文版本；保留可定位错误；跨节扩大编辑范围；失效比较依据生成证据范围内 replan.json，交回 Writer 修订；两轮耗尽停止 |
| `geo_source_cards/paragraph_repair.py` | 消费复核后的有效问题及重新规划；提供上下文/声明；每个问题组至少实改一个相关段；正确段落逐字保留，新版必须复审 |
| `geo_source_cards/daily_editorial.py` | 当前材料+正文+独立审稿终验；保存结构、审稿、争议与逻辑状态到交付；过期结果不能交付 |
| `geo_source_cards/staged_editorial.py` | 接入统一确定性检查；取消6条/4条等纯数量阻断，至少有可用证据和有效提纲才可执行；来源逐字、医学风险和权限校验保留 |
| `geo_source_cards/editorial_schema.py` | 允许 Reviewer 仲裁问题来源，保持结构化问题约束 |
| `geo-monitor-deploy/creation/editorial_status.py` | 从 active/队列/day 推导当前状态，保留原健康日志；区分已保存答复和未知请求 |
| `geo-monitor-deploy/creation/runtime.py` | 状态接口采用实际执行状态；交付读取时重验仲裁、声明和逻辑，不把待核对稿冒充已证实通过 |
| `geo-monitor-deploy/creation/panel.html` | 增加待核对审阅提示及真实执行终态，保留旧ZIP下载校验与现有页面功能 |
| `geo-source-card-collectors/tests/test_three_agent_quality.py` | 新增24项回归/故障/Mock闭环测试 |
| `geo-monitor-deploy/creation/test_editorial_health.py` | 新增4项终态、旧健康日志、答复已保存、未知请求测试 |
| `maintenance/package_current.py`、`source-snapshot/`、根目录交接文档 | 更新受控恢复映射和完整源码基线，保存可复现测试/部署证据 |

没有删除有调用方的旧 append、delta、known_response 兼容模块，也没有删除历史任务、原稿、账本、费用或原测试。引擎旧提示块的重复职责已收敛到统一 document/编译合同，其他无法证实安全删除的历史协议保留。原已有嵌套仓库的未提交修改和 Git 状态没有重置。

## 5. 保留的业务边界

- READY 正常写，READY_WITH_LIMITS 缩小可论证范围继续写；缺效果比较/实测/部分属性不整篇阻断。
- 冲突规格排除出可写声明，原冲突保留；资料缺失不发明事实、数据、实验、价格、优劣排名。
- NO_INSERT、自有产品身份、来源映射、版本、预算预留、未知请求保护、已有费用记录继续生效。
- 风格和合理一般建议进入 suggestions；待核对意见可保留争议，不被强行确认为正确，也不凭不确定意见单独阻断整篇。确定事实/逻辑错误、空主体、必要章节缺失仍不可交付。
- 反对意见的仲裁不会改初审 false 检查或 unsupported 声明为 true；这些仍须 Writer 修订后接受新的审稿。确定性错误不能被模型复核豁免。
- 内容修订最多2轮；技术失败、额度不足、未知请求和内容失败有明确记录，不伪造审核通过。

## 6. 测试的真实结果

| 验证 | 结果及边界 |
|---|---|
| 原生产源码基线相关回归 | 172 engine + 74 creation = **246通过**；独立保留 baseline 日志与结果。另在本地先执行过58项原源码重点测试通过 |
| 最终 Linux 生产同环境隔离 stage | 196 engine + 78 creation = **274通过**，包含原246项和新增28项；不是在真实付费任务上伪造输出 |
| 新增24项引擎测试 | 三个角色串联实际生成结构、声明稿、Word与映射再独立复审；实际原文选取/源锚点、Analyzer格式错误限次与降级/未知保护、结构进入写作及修订保留、空主体/缺节/乱序/空段/重复/截断、缺节只补该节、已知解析/限流恢复、未知不重试、恢复零额外调用、输入/组件哈希改变拒绝、并发锁、预算停止、C34/C60通用边界、11与10总数/子集/普通数字、复核伪证据拒绝、确定性错误不得豁免、Reviewer不可用、Mock审稿→补丁→旧版失效→新版复审、replan与两轮封顶 |
| 新增4项 creation 测试 | 已完成/失败不沿用 requesting、已保存答复单列、未知请求保持保护、pending不假称完成 |
| 本地扩展全量扫描 | **418项：412通过、5跳过、1错误**。错误为采集登录 `test_session_detector_distinguishes_ready_logout_and_unknown`：旧 Mock 没有 Network.getAllCookies 列表，与现有 session checkpoint 不匹配。相关 collector/session_store 与任务开始前 Git 快照 SHA 完全一致，未修改其实现或旧测试期望来制造通过。见 local-full-suite.log、capture-test-baseline.json |
| Windows creation 初次扫描 | 本机 Python 缺少 tzdata/Asia-Shanghai 导致5项导入错误；已在 Linux 同环境运行完整78项通过，没有把本机导入失败当产品失败或谎报本机全通过 |
| 前端 | 本地自带 Node `--check`通过；服务器无 Node，记录为未在服务器运行 Node；部署页面 HTTP 200且字节哈希与本地一致。**没有执行真实浏览器操作验收** |
| 部署源与恢复映射 | 44份部署文件逐一SHA一致；恢复包映射 **217/217** 对齐服务器；源码快照 **547文件/543唯一条目** 校验一致 |

C34/C60 的测试验证通用候选筛选、审稿边界合同、复核结果校验及返修路由，独立模型的语义判断使用 Mock，不表示真实模型已经100%校准。

## 7. 真实旧样本重放、计费及真实小样本限制

- 对**保存的真实 API 答复**做了零调用本地重放：排行01 sections=[]被完整性门槛拒绝；测评02正文的“十款”与11款名单冲突定位在 P002/P006，并产生需独立核对的材料/外观→表现语义候选。没有覆盖旧稿或签发新的真值/通过证书。这是历史数据重放，**不是新真实生成或真实模型复审**。
- 原排行01剩余 **¥0.07298220**；按当前长文分节+Analyzer+事实/逻辑首轮，仅输出预留下界 **¥0.163824**（17次初始调用）。
- 原测评02剩余 **¥0.06631544**；同一预留下界 **¥0.166624**（18次初始调用）。以上尚未计输入、可选仲裁、技术补生成与两轮修订，因此不能安全启动完整小样本。
- 本轮新增真实生成、审稿、返修 API 调用均为 **0**，新增费用 **¥0**。计划账本昨日¥2.80204912、今日¥0.90960560，总计仍 **¥3.71165472**，本计划未结算预留0。
- 单篇累计¥0.35、原计划¥5.25、共享每日¥10均未增加。3笔原未知请求ID集合完全一致，未盲目重发、清账或重置预算。
- 因此**原14篇仍0篇合格**，真实排行/测评端到端生成、审稿及返修验收尚未完成，也不能宣称跨日无人值守已通过。

## 8. 部署与实际运行

- 先按既有流程暂停接受新阶段并等待 worker 收尾，检查进行中的付费调用，再备份逐文件原子替换；未中断付费请求。
- 已部署上述代码，`geo-content-api`、`geo-content-worker`、`geo-creation-studio`均 active，worker心跳新鲜；API `/api/status`及前端根页面均HTTP 200。三者启动成功不等于新文章质量验收通过。
- 重新投影状态后，原两项小绿瓶任务显示 complete_with_failures，无活动请求；另一个既有受保护任务保留 RESPONDED，显示 response_saved，未重发。
- 本次部署的临时暂停均按**部署前**控制版本原样恢复，已核对。最早巡检到第一次部署前，3个任务的控制状态已存在变化；部署证据明确记录了这一差异，未用更早快照覆盖可能的新状态，未发继续任务指令。没有新增费用或请求；不能将“最早巡检至最终所有控制完全相同”写成已验证。
- 没有重建 URL 输入、采集、知识库或现有前端架构，也没有恢复老生产镜像。原采集批次不属于本轮内容改造的重启范围。

## 9. 未完成及后续安全边界

1. 预算不足，两个新真实 API 小样本未启动，真实模型语义仲裁、长文各节实际篇幅/衔接和两轮真实返修仍待验；现有测试证明执行及保护机制，不能替代内容效果证据。
2. 跨日持续无人值守、模型长期波动/平台故障没有完成真实观察；不能承诺永远一次通过。
3. 本地扩展采集测试仍有上述1项 Mock 不匹配，5项跳过保持原状。内容相关生产同环境274项无失败。
4. 服务器无Node、没有真实浏览器操作验收；本地语法检查与HTTP/SHA已完成。
5. 参考源没有主原文或完全无可用资料时仍停止；未知付费请求仍保留保护。不要为补齐验收提高预算、创建新计费任务、覆盖旧稿或重发未知请求。

复现入口：`build_stage.py`、`stage_test.py`、`baseline_test.py`、`budget_preflight.py`、`replay_saved_samples.py`、`verify_live.py`。隔离 stage 在服务器维护目录，日志及部署清单已经下载到本目录。
