# B1/B2独立候选修复：零API调用验证

版本：`candidate-b1-b2-v1-20261023`；时间：2026-10-23T10:21:13.587255+08:00。所有修改仅在本目录candidate-source，未改原六份冻结文件、原源码目录、生产、任务、原稿或账本。新增真实API调用0、余额查询0、外部服务调用0、预算变更0、部署0。仅读取本机已有运行依赖路径，没有安装依赖。

## 1. B1根因、修复与前后差异

旧abstract_task主要在purpose中寻找“推介/逐项/产品/品牌”，而“展示某品牌的综合资质、配方体系、功效、安全性与使用体验”没有命中这些词。没有subject角色时，bind按章节下标分配，保存的测评02自有产品S2因此绑定到AS001开场。

新版本先用normalize_roles识别原文功能，再单独给新文章产品槽分配结构位置：读取真实段落锚点、序号/短标题、文内重复的名称形态、段落区间、目的和必要内容、章节顺序；区分opening、criteria、subject、comparison、summary及unknown/body。未编号的原文标题也可以在原文自身有足够重复命名模式时识别，不依赖固定品牌或品类字典。相邻原文片段属于同一个产品时先按锚点归并，避免当成多个产品位置。

产品槽只从subject角色选择；没有可确认位置时，structure_id保持null、structure_binding.status=needs_check，不再按比例回退到引言。该待核对状态不会把READY_WITH_LIMITS退回旧版资料严格阻断。正文仍只能使用当前产品的有效声明。

实际保存资料重放：

- 测评02：旧S2→AS001（开场）；新S2→AS002（真实第一款产品介绍）；十个原文产品介绍均识别为subject。
- 排行01：旧位置均分S2→AS004；新S2→AS003，锚定原文实际产品标题所在段落，而非后续普通说明段。原结构包含降级逐段分析，本轮未让模型生成新结构。
- 两份结构等义改写后，绑定保持；将实际锚点和目的改成比较标准，绑定随角色改变。引言、横向比较、结尾不被用作自有产品介绍。
- Writer只接收抽象组织动作。旧版“安全purpose”直接透传required_content的分支也已移除；即使使用该标签，原品牌92%功效/199元等具体属性也不能变成新产品的必要内容。完整原文仍留给来源复核。

测试区分：保存资料重放证明这两份真实输入的确定性行为；3品类、歧义、角色变更、禁带事实使用合成边界输入，不称为真实模型语义验收。

## 2. B2根因、失效规则与前后差异

旧review_quality.process在quality_pipeline.json命中后，只检查答案、正文、knowledge/product摘要便直接返回；原始research_result及来源映射、合同没有完整纳入最终指纹。底层仲裁能检查新输入，但被最终快路径绕过。

新增review_inputs作为本地摘要工具，按现有writing_job/active ticket与research_for_writer解析实际来源版本。v2指纹包括：正文、knowledge、product，当前及原writer的合同/声明/映射、writer_done、结构、编译结果、原始research_input/research_result、研究来源映射及实际审核知识单元。C编号映射从当前正文重建，若已有映射与重建结果不同则拒绝，避免只检查ID。

缓存命中前读取当前来源；整个审核结束前再核对一次，输入中途变化也不能签发结果。失效时保留旧证书与批次，记录needs_reaudit并抛出明确错误，不调用模型、不把不可用服务当通过。旧v1最终证书没有完整来源绑定，不能直接用于新候选终验。

仲裁证书和批次同时绑定完整输入；即使调用方重复传入旧data，batched也会重新核对当前磁盘来源。只有所有输入相同才复用已完成批次；未知批次不重发。终验、返修路由、已交付稿读取均传入真实来源位置，避免存在第二条绕过路径。带审稿证书的交付读取不再依赖可选logic_policy是否开启。

前后对照：

| 情况 | 旧行为 | 新候选 |
|---|---|---|
| 只改原始研究来源，正文/产品不变 | 最终缓存可能直接返回旧结果 | needs_reaudit，拒绝旧结果 |
| 只改正文、knowledge或product | 部分已有校验 | 统一指纹拒绝，相关断言保留 |
| 只改来源映射、原writer合同或阶段合同 | 最终指纹不完整 | 重新读取并失效 |
| 所有输入相同 | 可复用部分状态 | 最终缓存及已完成仲裁安全复用，新增Mock请求0 |
| 来源变化后传入旧仲裁data | 底层缺少重新读盘的完整保护 | 直接拒绝，不签发通过 |
| 旧v1缓存/证书 | 可能只检查正文和产品 | 拒绝缺失的完整来源绑定 |
| 未知请求/审稿服务不可用 | 原保护应保留 | 不重发、不签发通过 |

真实历史缓存已离线重放：旧证书缺少来源绑定，被新候选明确拒绝，未执行模型复审。新v2缓存的命中、失效和交付行为通过本地Mock路由测试；Mock没有证明真实审稿意见正确。

## 3. 新版本文件与SHA

以下是完整候选包，包含4份逐字继承文件。与baseline-source的完整Git diff在candidate.diff：9份新增/修改文件、388行增加与58行删除（以Git diff为准）。其中creation/runtime.py、daily_editorial.py、repair_router.py只接线来源校验；不改预算、任务调度或写作业务。

| 文件 | 状态 | SHA256 |
|---|---|---|
| creation/runtime.py | modified | `abba3c1084e0953740a00916c03987efab9d71e1d60afc7aee0a637772cbfb8d` |
| geo_source_cards/consumer_prompts.py | unchanged | `d4f906ade8e9850ed7c7b5e4da388d25159867b00a15b7541904debd1871d2b0` |
| geo_source_cards/daily_editorial.py | modified | `c98993370318ea24f0fdf2d72e7f62f64148503bd13570f43f5fbe7548d12c75` |
| geo_source_cards/repair_router.py | modified | `1b2bdde41f9ad5ac9b6e1b9998c66172be19a18c71c35bba4afa95f33f043c0c` |
| geo_source_cards/review_arbitration.py | modified | `03aed7119d9d8cac26937e620c3c6710656b85dcddd875c517ec870aea6cdf7e` |
| geo_source_cards/review_inputs.py | added | `c8ff98708204ef2ce176c6dd2eeb7c9702e4421e5ef583c05895f612ca80a5ec` |
| geo_source_cards/review_quality.py | modified | `5da64b2cd498a58c3dffc83eb89da1d39d0629f8c420317dfe190728815d8dcf` |
| geo_source_cards/section_writer.py | unchanged | `c96957d1b2c6e82487841f487ac079df0b7c68fbbc6ac45f43debe189599d22c` |
| geo_source_cards/structure_analyzer.py | modified | `f4f213e49d18bc7f99855e1cc545779d3fa42db61c04043d569ee8605915eede` |
| tests/test_arbitration_batches.py | unchanged | `6f0835d15c3b695f9f236e2650a00768b655cd72ef1935b8d3963c9f8dd61185` |
| tests/test_b1_b2_offline.py | added | `be144ebe82a5e10dbda1b229a7da2851e5ecca6e06a3f9992e7cced1bc561267` |
| tests/test_section_budget_revision.py | unchanged | `a3a475c6dae2915772b5b24d968d9d0ac0c351e594c4e9b7e4c3e8edf81a7b7c` |
| tests/test_three_agent_quality.py | modified | `7c4bb8ece75ce4a68aa77213a5403d91337eba1eac8d6cd62aa49a99caeee83e` |

原6份冻结文件和上一轮日志/证据共33份受保护文件SHA均未改变。根仓库已跟踪修改状态与本轮开始时一致；本轮仅新增维护目录。没有把新候选混进生产恢复映射。

## 4. 实际测试结果

先执行保存资料重放，再执行本机离线回归：

- 新增20项：20通过、0失败、0错误，覆盖8组结构角色与12组缓存/终验/未知保护边界。
- 引擎相关回归288项：288通过、0失败、0错误。
- 创作扩展78项：74通过、0断言失败、4项执行错误。相同环境下用修复前基线复跑，完全相同的4项错误，详见creation-baseline-tests.json；本轮没有把它们记成通过。
- 合计386项执行计数：382通过、4项既有环境错误；没有跳过测试或放宽事实、逻辑、未知请求保护。
- 原test_three_agent_quality中1个测试的有效输入由手造v1空证书更新为真实绑定当前文件的v2证书；所有原assert/assertRaises内容通过AST对照确认完全保留。原文件留在baseline-source，未覆盖原项目或冻结测试。这是新来源绑定所需的有效夹具，不是删除失效断言。
- 外部socket和未Mock的HTTP被禁止；扩展下载测试仅放行本进程创建的127.0.0.1回环HTTP夹具，不访问服务器或外部服务。各测试日志外部网络尝试0、真实API请求0。

完整日志：new-tests.log、engine-tests.log、creation-tests.log；前后对比：real-material-replay.json；版本与保护证据：manifest.json、protected-before.json。Windows初次缺少IANA时区资料的加载错误保留在creation-before-tzpath.log；随后仅指定应用已自带的tzdata路径，没有安装或伪造时区。

## 5. 未解决的问题

1. 本轮没有新文章生成、真实模型审稿、仲裁或返修；真实合格仍为上轮0/2。不能从20+288项通过推断文章语义已合格。
2. 通用角色识别是多证据的确定性推断；无标题、无稳定锚点或功能描述冲突的资料会保留needs_check，不保证任意措辞均自动判定。真实模型的结构分析质量、语义审稿边界仍待将来获准验收。
3. 4项本机既有环境错误为：旧Word/ZIP读取的Windows路径问题2项、SQLite清理时文件句柄占用1项、Linux原生fcntl模块不可用1项。候选与旧基线完全一致。未为此扩大修改；本轮未访问服务器，因此也没有声称新的Linux同环境全套验证已通过。
4. v1未绑定原始来源的历史证书，不能自动升级为v2或沿用为通过；后续需要在原额度与授权允许时重新审核。原始证据、未知请求、账本和预算不变。
5. 新候选尚未部署，不报告新的生产运行状态、实时余额或服务器账本实时笔数。本阶段至此保持零调用。
