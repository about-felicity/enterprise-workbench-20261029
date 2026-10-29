排行01写作逻辑诊断（只读、零调用）
日期：2026-10-23
对象：rank01-writer-v4-20261023T150914-d4beec2f；候选 candidate-structure-recovery-v4-20261023。

本次只读取现有文件与代码，未执行项目流水线、模型、审稿、余额查询或网络请求；未修改候选、生产、原稿、费用、任务状态。另存本报告与证据索引。本报告区分真实输出观察、静态代码缺陷和待真实验证的风险，不以格式校验代替质量验收。

**1. 结论与证据边界**

优先根因是：①证据范围降级后没有重设全文问题和可交付答案；②现有“论证规划”主要是事实分配及原文结构映射，没有形成新文章的推理设计；③分节写作和局部重试缺少共同的全文编辑合同，已有审稿/返修也未完整消费这种合同。

这不是“没有Planner”或“没有全文审稿”。这些模块已经存在，缺的是把证据变成明确主旨、统一比较与章节贡献的连接层。继续增加免责声明、长度检查或新的Agent，不能补齐这一层。

真实状态：15个结构区域、84个锚点的结构已保存；本次Writer只收到了三版INTRO，全部未被接纳，主体0/15，END未写。三次finish_reason均为stop，并非输出截断；事实审稿、全文逻辑审稿、仲裁和内容返修均未执行。导语缺陷可直接观察，全篇重复、审稿能否抓住问题和返修是否有效尚不能宣称已实测。

真实证据：[三次接收稿](C:/Users/78567/Desktop/隐身浏览器/outputs/rank01-writer-v4-20261023T150914-d4beec2f/received/INTRO-attempt-2.md)、[当前状态](C:/Users/78567/Desktop/隐身浏览器/outputs/rank01-writer-v4-20261023T150914-d4beec2f/writer_acceptance.json)、[审稿状态](C:/Users/78567/Desktop/隐身浏览器/outputs/rank01-writer-v4-20261023T150914-d4beec2f/review_status.json)。

**2. 三个根因，按优先级排列**

**P1：缩小了允许写的内容，却把旧标题继续当作全文目标。**

代码：[argument_plan.py:59](C:/Users/78567/Desktop/隐身浏览器/maintenance/structure-v4-20261023/isolated/current/engine/geo_source_cards/argument_plan.py:59)取原文primary_title为main_question；[article_compiler.py:82](C:/Users/78567/Desktop/隐身浏览器/maintenance/structure-v4-20261023/isolated/current/engine/geo_source_cards/article_compiler.py:82)把无实测任务降为READY_WITH_LIMITS/effective_type=review，proposed_scope只有“依据现有记录比较composition”；但[article_compiler.py:166](C:/Users/78567/Desktop/隐身浏览器/maintenance/structure-v4-20261023/isolated/current/engine/geo_source_cards/article_compiler.py:166)仍把original_title写回合同main_question。[section_writer.py:88](C:/Users/78567/Desktop/隐身浏览器/maintenance/structure-v4-20261023/isolated/current/engine/geo_source_cards/section_writer.py:88)将它原样传为goal，INTRO.topic同样沿用旧题。

实际三次request.json均为：
- goal：“哪个牌子的防脱洗发水好?2026热门高口碑榜防脱实测，码住不踩雷”。
- scope：hands_on → review；缺真实实测；允许比较composition。
- 没有明确article_goal、thesis或有条件比较答案；只有范围和禁止事项。
- 输出标题：“哪个牌子的防脱洗发水好：从配方记录看十款防脱洗发水”。
- 第三版导语却说：“本文提供的是一个阅读配方记录的框架，而不是一份替你下结论的购买指令。”

标题后半句已有缩小范围，但系统仍没有决定“究竟回答什么、凭什么回答到什么程度”。第一版承诺结尾给有条件回答，第三版则退为阅读框架。这里不能据此断言全文必定不回答，因为全文未生成；可以确认标题承诺与正文定位没有统一合同。

[article_compiler.py:268](C:/Users/78567/Desktop/隐身浏览器/maintenance/structure-v4-20261023/isolated/current/engine/geo_source_cards/article_compiler.py:268)的标题校验依赖STRONG类型关键词，能拦“实测”等越界标签，不能核查“哪个更好”与实际有限答案是否一致。

最小修复：在现有Planner/Compiler中同时确定有效问题、可支持的主旨、标题承诺和答案范围，保留original_title仅作来源元数据。资料足够时给对应维度的比较判断；不足时改为可兑现的比较定位，仍继续写作，不退回严格阻断，不编造效果冠军。

**P2：结构覆盖与证据编号代替了真正的论证链，统一矩阵没有完整进入Writer。**

代码：[argument_plan.py:22](C:/Users/78567/Desktop/隐身浏览器/maintenance/structure-v4-20261023/isolated/current/engine/geo_source_cards/argument_plan.py:22)已有产品×字段可用性矩阵，记录recorded/unknown和证据ID；它依据词匹配识别composition、price等字段。这是可用性表，不是同口径数值或可成立判断。[article_compiler.py:139](C:/Users/78567/Desktop/隐身浏览器/maintenance/structure-v4-20261023/isolated/current/engine/geo_source_cards/article_compiler.py:139)把每条证据变成CL，allowed_conclusions基本照录证据；reasoning只有premises、describe/scoped_explanation和各节相同的conclusion_scope。生成合同没有保留上游products.fields矩阵与answer_contract，没有形成“判断—证据—推理—本节结论—承接理由”。

实际例子：E_KU01包含咖啡因及温和、洗感描述；E_KU04只说“配方走清爽路线”；道和PF列具体成分。三者都能被标成composition，但资料粒度、证据性质不同，不能由同一标签推出性能排序或统一评分。部分general advice又以带品牌的source_claim进入产品事实池：CL0010与CL0011同为“菲诗蔻…把需求和配方对应起来；对照成分表逐项确认。”这是保存账本中已存在的重复和分类错位，不是本轮模型新造的事实。

当前实际适配器[plan.py:19](C:/Users/78567/Desktop/隐身浏览器/maintenance/writer-v4-first-20261023/plan.py:19)遵循上轮明确指定的“INTRO＋15区域＋END”，逐个覆盖来源区域；问题不在覆盖15区域本身，而在没有为这些区域重新分配新文章的有效论证任务。适配器把多数非产品区域复制自general[-1]：
- S1“脱发机制与选购判断框架”：只分CL0007。
- S12“多维度评分对比的引入”：仍只分CL0007。
- S13“选购误区与正确选法”：仍只分CL0007。
- S14“资质优先的结尾选购建议”：仍只分CL0007。
- S15“免责声明”：没有CL。
CL0007仅是“排行洗感为编辑转述，结合发质及四周掉发记录判断”的一般建议，不能支持机制解释、分项评分或资质优先结论。S12的评分任务尤其与无统一评分证据的范围不相容。

[structure_analyzer.py:173](C:/Users/78567/Desktop/隐身浏览器/maintenance/structure-v4-20261023/isolated/current/engine/geo_source_cards/structure_analyzer.py:173)把moves转成通用任务；after/reads_previous_section主要保留顺序ID，并未说明上一节哪个结论为何支持下一节。当前任务另保留source_region的topic/purpose/moves/anchors，所以不能说上游信息全丢了；真正缺失的是对新文章的编辑决策。原文opening/summary与额外INTRO/END并存、三个区域共用同一建议，构成重复和空泛扩写风险；正文尚未执行，风险未获实际全文验证。

最小修复：复用现有矩阵和CL/E/KU/PF，不重建事实系统；补充每个产品每个维度的证据内容、性质、缺项和允许比较关系。把一般建议从产品属性中分开，并按相同来源/语义去重。为每节写清唯一贡献和必要前提；覆盖原文区域不必承诺原文评分、机制或资质结论。产品身份和AS-O0003绑定保持不变；两处needs_check不升级为confirmed。

**P3：Writer拿到了大量事实和约束，但局部纠错没有解决全文意义。**

[section_writer.py:81](C:/Users/78567/Desktop/隐身浏览器/maintenance/structure-v4-20261023/isolated/current/engine/geo_source_cards/section_writer.py:81)实际给INTRO和END释放全部35条声明及对应35份证据。事实可追溯性保留，但claims.text与original_evidence.text重复携带，缺少导语专属论证任务。实际首次输入11452tokens，只生成509tokens；后两次输入12096、12026tokens。不能仅凭体积认定模型能力不足，但可以确认输入主要负担在事实/边界，且没有thesis、比较矩阵或每节已确立结论。

上下文只带最近两节末段最多500字符及标题；END另读开头。expected_order只有ID与topic，没有全文结论状态、未回答问题、每节独有信息或重复观点清单。Prompt已有“同一标准、不重复免责声明”等要求，因此不是完全没要求自然写作；它们没有转成可检查、可继承的编辑状态。通用consumer_voice.POLICY和argument_plan.WRITER_RULES也未完整进入这条分节Prompt，实际使用的是section_writer.prompt＋WRITER_CONTRACT，不是旧writing_prompt.md整文模板。

三次真实反馈链：
1. 第一次603字符，第二段讲可写范围，被标inference且claim_ids为空 → validate_part首先报Fact without claim。证据只能证明这是声明分类/支持表达问题；不能把该段所有内容直接认定为“无需证据的一般建议”，它还包含资料完整性断言，应由真实资料缺口记录支持。
2. 第二次改为general_advice后，报494汉字不足500。局部反馈只有扩写要求。
3. 第三次补进道和、六神、蜂花等产品细节，856字符超过722，仍未确定有效核心答案；边界说明占多个段落，导语开始提前罗列正文资料。
这解释了为什么文字越修越像审计说明。长度问题是局部触发器，根因是没有“该补哪一步论证、导语到哪里为止”的计划。

已有全文逻辑审稿[article_logic.py:62](C:/Users/78567/Desktop/隐身浏览器/maintenance/structure-v4-20261023/isolated/current/engine/geo_source_cards/article_logic.py:62)会检查问题回答、因果、矛盾和承接；事实审核和仲裁也有独立证据要求，不能删除。当前逻辑Schema最多3个关键issues，未显式覆盖语义重复、独有信息量及读者承诺兑现。[repair_router.py:49](C:/Users/78567/Desktop/隐身浏览器/maintenance/structure-v4-20261023/isolated/current/engine/geo_source_cards/repair_router.py:49)有PATCH/REPLAN、跨章节扩展、两轮上限和版本校验；[paragraph_repair.py:64](C:/Users/78567/Desktop/隐身浏览器/maintenance/structure-v4-20261023/isolated/current/engine/geo_source_cards/paragraph_repair.py:64)补丁路径却要求保持章节顺序、不能增加/删除段落。局部事实问题可修；全篇目标、顺序或冗余章节问题若落到PATCH，难以根治。该问题是代码路径风险，本次没有真实返修结果证明。

最小修复：同一份论证合同贯穿Writer、Reviewer和返修；给分节生成传全文主旨、对应推理任务、已完成结论摘要与重复主题归属。返修反馈保留完整问题及上下文，分类错误与资料缺口断言分别处理；全局论证/顺序失效明确走REPLAN，局部证据错误继续PATCH。重复免责声明作为编辑改进，不能单凭数量拒绝整篇。

**3. 完整数据流与信息保留情况**

| 环节 | 实际代码位置 | 本次发现 |
|---|---|---|
| 原文解析/结构 | staged_editorial.source_map；structure_analyzer.source_input:17、analyze:75；structure_protocol | research_input中的原文转O锚点，V4保留15区域/84锚点及moves/after。覆盖完整不证明新文章论证完整。 |
| 新章节映射 | structure_analyzer.abstract_task:173、bind:212；实际plan.compile_plan:19 | 保留产品槽与来源区域；将原文动作抽象为通用任务，非产品区域重复继承同一证据。 |
| 产品/声明绑定 | consumer_prompts.reader_knowledge:24、reader_facts:106；argument_plan.build:22；article_compiler.normalize:40 | 道和S2→AS-O0003→CL0025—CL0035，PF和竞品KU分开；有效事实保留。不等于一般建议分类和所有语义范围均正确。 |
| 写作前规划 | argument_plan.build；article_compiler.compile_article:139 | 有字段矩阵和声明分配；没有具体thesis、推理结果与比较结论，矩阵未完整进入实际分节请求。 |
| 全篇/分节/重试Prompt | 旧writing_prompt.md；article_compiler.writer_prompt:223；实际section_writer.prompt:81、generate:104；runner.py:241 | 本次真正执行分节路径。三版均有旧goal、全35CL、空previous_context；后两版只增加上次失败及被拒稿。不能用旧模板的良好要求当作实际执行证据。 |
| 分类、证据、长度 | section_writer.validate_part:44；article_compiler.validate_document:258；quality_checks.findings/semantic_candidates | 校验身份、映射、空节、重复原句和范围关键词；不以CL作为语义证明。缺少全文编辑合同校验。 |
| 审稿/仲裁/返修 | review_quality.process:25；article_logic.prompt:62；review_arbitration.context:12；repair_router.route:49；paragraph_repair.prompt:64 | 版本、来源、两轮和争议保护已存在，应保留。本次未执行，不能评价真实审稿检出率。 |

额外静态缺陷：consumer_prompts.py:232、article_logic.py:72、review_arbitration.py:37仅在版本字面量article-structure-compact-v2时附加完整原文；当前为v4。这会漏掉完整原文上下文（仍有KU原始摘录，不等于完全无证据）。本次runner.py:165—167对事实与逻辑请求显式补入original_article_source，因此这两条特定路径有补偿；默认仲裁路径仍有缺口。本轮未跑审稿/仲裁，这不是三版导语的成因，也不能用它解释已观察导语。本项建议纳入最小兼容修复与离线输入核验。

**4. 最小修复范围评估（尚未实施）**

保留三个Agent，增强现有Planner/Compiler，在原合同中增加可版本化的argument_contract；不增加Agent或框架。建议字段及复用：
- article_goal、thesis：从有效任务和已允许证据形成有限、明确答案；保留原题另存。
- comparison_matrix：复用argument_plan.products.fields与evidence，增加统一维度、事实值/描述、证据性质、可比关系与缺项；不把recorded当成同等可比。
- claim_ledger：沿用CL/E/KU/PF和权限，增加判断→前提→推理规则→结论的引用；普通建议独立分类。
- reasoning_outline：沿用S/AS/moves/after/anchors，每节增加核心判断、证据、推理、本节结论、唯一贡献、下一节进入理由；不照搬原文产品事实和失效评分任务。
- evidence_gaps：复用feasibility.reasons/conflicts/unsupported_dimensions，分别限制具体结论；不要求缺项全部补齐才能写。
- acceptance_criteria：沿用事实、完整性、来源、两轮保护；补标题承诺与实际答案一致、必要论证覆盖、重复观点处理、承接与信息量。可读性问题优先编辑，不把风格偏好提升为事实错误。

预计必要模块：argument_plan.py、article_compiler.py、section_writer.py；适配器plan.py消费同一规划接口；article_logic.py和repair_router/paragraph_repair按问题范围消费合同。完整原文版本兼容集中复用structure_analyzer.review_source，不再各处写死v2。不改结构分析职责、预算/未知请求、产品身份或事实质量标准。只有确认范围后再做独立候选实现。

**5. 零调用回归计划（本轮未运行新测试）**

1. 用三版真实request/response重放“目标降级但旧goal未变”的案例；断言新定位、标题承诺和有效答案统一，且不补造效果排名。
2. 用现有10款/35CL建立维度矩阵，分别验证同口径可比、仅描述可比、缺项不可比；空项不转换成无该属性或较差。一般建议不再伪装品牌属性、重复证据不重复贡献。
3. 检查15区域→写作任务映射，保留84锚点溯源、道和AS-O0003、needs_check和NO_INSERT；S12不继承虚构评分，S1/S12/S13/S14不靠同条建议重复支撑不同结论。
4. 检查实际分节messages包含统一合同及必要事实；导语不默认倾倒全量产品细节；各节输入包含论证前提、已有结论和重复归属。方法说明若含资料完整性断言，引用对应缺口记录；不能单靠改statement_type免责。
5. 使用合成整稿定位标题/结论偏离、跨节矛盾、语义重复和缺承接；局部事实问题PATCH，全篇目标/顺序问题REPLAN；不因免责声明数量或一般建议缺实验而退稿。
6. 对v4默认事实、逻辑、仲裁输入核查完整原文与来源指纹，正文/来源/合同变化使旧结论失效。保留现有B1/B2、未知请求禁止重发、预算、有限恢复及最多两轮回归。

这些只证明程序正确传递和路由，不证明自然语言质量已经达标。不得用Mock语言质量分数宣称真实文章通过。

**6. 必须留待新真实执行验证**

需未来另获授权后，才能确认：模型是否依据有限主旨写出实际比较而非免责教程；统一矩阵能否产出有信息量且不越界的判断；分节结论摘要能否改善衔接；真实Reviewer能否检出并正确定位这些问题；仲裁能否区分误判；定点返修/重新规划后是否真正消除问题。当前没有完整真实文章及审核/修复闭环，以上均未验收。

本轮停止在诊断；不改冻结候选，不发送请求，不重置次数，不部署。

