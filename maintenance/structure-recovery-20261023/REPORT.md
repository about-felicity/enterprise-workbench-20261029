# 结构分析截断修复与零调用验收

版本：`candidate-structure-recovery-v3-20261023`，基于冻结的 `candidate-b2-repair-entry-v2-20261023`。时间：2026-10-23T13:28:17.135667+08:00。

本轮已完成独立候选代码修改、保存真实资料的离线重放和目标 Linux 回归。**真实 API、余额查询、外部业务服务调用均为 0；没有真实文章生成或质量验收，没有部署、重启、改预算或恢复旧任务。** SSH 仅用于目标隔离目录的传输与测试。

## 1. 两次真实截断的证据与根因

审计对象是 `rank01-staged-20261023T120816-e50a98ac` 保存的两条真实请求/答复，不重新请求。原始记录、usage、成本和失败状态保持原样。

| 项目 | 第一次 | 第二次 |
| --- | --- | --- |
| 模型及参数形式 | deepseek-flash，顶层 max_tokens | 同左 |
| JSON 模式 | response_format.type=json_object | 同左 |
| max_tokens | 2400 | 2400 |
| prompt_tokens | 11100 | 11103 |
| completion_tokens | 2399 | 2400 |
| finish_reason | length | length |
| 答复字符数 | 4912 | 4785 |
| 末尾 | AS014.argument_step 字符串中途 | AS014.purpose 字符串中途 |

第一次还有独立的 JSON 格式问题：`json.loads` 在字符位置 **481** 发现字符串内未转义换行；第二次在位置 **4770** 报未结束字符串。因此不能断言只提高输出上限就能恢复。

旧请求同时包含 7006 字符 original_text、6840 字符的 blocks 文本和任务提纲；同一正文被重复传入。旧输出则要求每节重复解释 purpose、required_content、argument_step、transition，并摘录 source_quote。两次都写到 AS014 时耗尽额度，后续产品和结尾尚未覆盖。重试仅在相同提示词后增加 `output_incomplete`，上限和协议均不变。

另一个风险是旧的无标题 fallback 只保留前 40 个段落，本原文有 84 个；本次真实运行的执行器及时停止，没有将它用于成稿。新执行链不把这种降级结果签发为 ready。

这些证据足以说明 **2400 无法容纳这两次实际冗长输出**，但无法从截断记录精确反推出原协议完整输出究竟需要多少 tokens。保存的 usage 和 API 状态表明顶层 max_tokens 形式曾被接受；未保存完整 HTTP 响应头，供应商完整参数文档和最大能力本轮没有外查，明确保留为未验证。

完整证据见 `linux-final/logs/historical-root-cause-linux.json` 及 `history/rank01/article/writer/structure_calls/attempt-0/`、`attempt-1/`。

## 2. 协议和执行链的实际变化

| 旧协议 | 新协议 |
| --- | --- |
| 整文一次返回冗长章节解释、必要事实清单和摘录 | 唯一精简 Schema；仅 article_topic/article_purpose/genre，以及章节 section_id、role、role_status、topic、purpose、moves、after、anchors |
| 模型自行输出 AS001 等顺序号 | 程序按原文锚点分配 AS-Oxxxx，模型必须逐项照用，顺序与依赖严格核对 |
| 同样协议、2400 上限再试一次 | 首次按自然边界最多 3 个原文区域一块；已知失败后每个完整区域用 minimal 更短字段恢复，提示词/模式/任务集合均有变化 |
| 原文与事实可能充斥结构输出 | 结构仅存来源位置与摘要；完整原文继续存独立 research，审稿时重新读取并核验摘要 |
| 降级结构可能被继续消费 | 所有分块及合并完整后才 structure_ready；失败为 structure_incomplete/technical_failure/needs_reanalysis/request_unknown，Worker、Compiler、直接 Writer 均有保护 |

新字段有字符和 moves 数量上限；段落范围由程序展开，模型只回传首尾锚点。产品区域原子化，不能为了凑输入预算按固定 N 段拆开。内部问答/小标题仍通过 subsection_anchors 保留。单个区域超过输入安全上限，或章节超过阶段上限，会在请求前明确停止。

实际修改：新增 `structure_protocol.py`；`structure_analyzer.py` 接入计划、恢复、来源核验与安全写作视图；`api_worker.py`、`section_writer.py` 增加不完整结构入口保护。另在 `consumer_prompts.py`、`article_logic.py`、`review_arbitration.py` 仅补充从独立研究资料读取完整原文，以免精简合同减少审稿证据。**事实、逻辑、仲裁的判定规则和质量标准未修改。** `review_quality.py`、`review_inputs.py`、`repair_router.py` 和所有真实预算/账本逻辑保持基线 SHA。

分块有输入指纹、请求记录、accepted 结果哈希和阶段锁。完成块在所有输入一致时复用；响应已完整保存但尚未发布 accepted 的进程中断可本地恢复，不重复预留/发送。任何未知发送在全阶段预扫描时阻断；变更来源、元数据、Schema 或阶段限制会失效旧缓存。旧 v2 执行和已耗尽尝试不能借新协议重置。

## 3. 保存真实输入的零调用重放

两份输入来自保存的排行01和测评02资料。**原文/知识库是真实历史资料；新结构响应由明确的本地协议模拟器注入，仅用于检验解析、校验、合并、绑定和恢复，不是新模型结构判断，更不是文章生成。** 历史截断答复另通过实际 DeepSeekClient 响应解析路径重放，仍被标为 INVALID_RESPONSE/output_incomplete，未签发完整结构。

排行01：84 个段落锚点全部覆盖，10 个原文产品介绍区域保留为 10 个；首个产品 O0003—O0033 保持完整，内部七个问答保留锚点。合并为 15 个自然区域，5 个初始分块。新文章自身名单仍由现有 Compiler 决定，11 个产品槽和全部 claim_ids 权限保持不变，自有产品绑定首个真实产品介绍位置，不绑定引言。

测评02：全部 55 个保存锚点均被覆盖，10 个原文产品区域保持；自有产品槽及声明权限不变。三品类、READY_WITH_LIMITS、NO_INSERT、B1 needs_check 与 B2 来源变更保护由原有回归继续验证。

完整结果、各区域锚点和逐产品绑定见 `linux-final/logs/saved-source-replay-linux.json`。新增保真测试和探针同时确认事实、逻辑、仲裁输入仍能取得完整原文。费用测量用到的 6000 字符上界占位文本仅为成本代理，未保存或宣称为真实文章。

## 4. 实际测试结果与失败记录

目标 Linux 6.8.0-138、Python 3.10.12，使用已有 venv，无新依赖。

| 测试组 | 执行/通过 | 失败/错误/跳过 |
| --- | ---: | --- |
| 新结构恢复专项 | 33/33 | 0/0/0 |
| 原 B1/B2 与补充验收 | 54/54 | 0/0/0 |
| 相关引擎回归 | 288/288 | 0/0/0 |
| 创作扩展回归 | 78/78 | 0/0/0 |
| 合计 | **453/453** | **0/0/0** |

专项覆盖真实截断解析、字段缺失/空列表/重复 ID/错序/错误锚点、产品跨段边界、合并完整性、未知请求、已保存块恢复、来源失效、并发互斥、预算发送前停止、实际 Budget.reserve 公式、不完整结构阻止 Compiler/Writer、完整原文审稿保真。原质量断言、两轮返修限制、预算保护和未知请求保护保留。

Windows 专项最终 33 项通过；早期已有 54 项旧专项和 288 项引擎通过。没有将 Windows 全套创作测试表述为通过。最终结论以 Linux 最终源码为准。

保留了两类开发阶段失败证据：`logs/windows-special-first.log` 是新模拟器未抛出 BaseException 的夹具问题，修复模拟器而非改断言；`logs/windows-engine-first.log` 是旧端到端 Mock 返回旧结构协议。该 Mock 仅增加新 Schema 答复分支，**整个 test_three_agent_quality.py 的全部 assert AST 与基线一致**，没有放宽期望。最初 Linux 451 项通过的中间版本与源码包也分别留在服务器旧维护目录和本地 first-pass，不冒充最终 453 项结果。

最终日志见 `linux-final/logs/linux-*.log`、`linux-final/linux-results.json`。测试和探针进程禁止外部 socket/未 Mock HTTP，外联尝试计数为 0；已有下载测试只允许本机回环夹具。

## 5. 阶段调用和费用上界

继续沿用现有 INPUT_MISS=2 元/百万、OUTPUT=8 元/百万，不假设缓存或分时折扣。每条请求按既有公式：

`((UTF8(json.dumps(messages, ensure_ascii=False))字节数+256)*2 + max_tokens*8)/1,000,000`

实际测试用临时账本调用原 Budget.reserve，逐条比对新计划预留，未修改真实预算。正式调用仍须先通过全结构阶段剩余保守上界检查，再由原客户端逐请求 reserve；不是跳过预算的新发送入口。

| 排行01结构阶段 | 调用数上界 | 输出 tokens 合计上界 | 费用上界 元 |
| --- | ---: | ---: | ---: |
| 正常初始分块 | 5 | 8043 | 0.140940 |
| 全部已知失败恢复额外分支 | 15 | 9203 | 0.194040 |
| 初始加所有可能恢复 | **20** | **17246** | **0.334980** |

本样本每个初始请求输出上限为 1605—1613 tokens；恢复请求为 607—615 tokens。协议没有依靠单次更大的 max_tokens 解决该样本。全局硬限制为最多 8 个初始块、每块最多 3 个原文区域、最多 32 次结构调用；单次输入预留上限 32768 UTF-8 字节、输出上限 4096 tokens，阶段输出绝对上限 131072 tokens。具体文章必须使用实际 plan 的更小上界，不按全局上限盲目发送。

如暂沿用原 Writer/事实/逻辑的条件字节预留，后续三部分上界 2.937520 元，新结构阶段加全部恢复后，首阶段条件上界为 **3.272500 元**。此为离线测算，**不是已完成预算预留、当前余额查询或新执行授权**。恢复完整原文后的审稿提示体积已用上界占位文本测量并落在旧条件输入范围内，但真实未来正文仍必须重新逐请求测量；仲裁须等真实意见出来后为所有批次单独预检。

当前仍保留真实累计费用及正常生产配置；旧 v2 验收脚本未自动切换到新计划。后续若获真实验收授权，必须明确加载本候选、消费新的全阶段 plan 并重新检查原 scope/单篇/日预算、输入版本及请求状态，不能直接重跑已耗尽的旧运行。

详见 `linux-final/logs/budget-plan-linux.json`，其中列有所有 20 条条件请求的提示字节数、输出上限和预留金额。

## 6. 保护与未验证事项

核对本地 466 份保护文件、服务器 399 份生产/冻结版本/旧原稿/控制/设置/真实失败记录。前后 SHA 均一致；规范费用账本保持 **2006 行及完整逻辑摘要一致**，两条原截断调用费用 0.0200742 元及三个历史未知预留未变。本轮新增费用 0。

尚未验证：真实模型能否遵循新精简 Schema、角色/主题/论证动作的语义质量、真实分块答复的实际长度、真实网络异常下的恢复、最终文章和审稿质量。Mock/合成协议输出不能证明这些事项。供应商完整参数能力本轮未外查，任何未来真实调用仍须实际验收。超过原子区域/阶段安全上限的文章会明确停止，不保证所有任意长原文自动一次成功。

本轮没有生产部署、服务重启、内容返修、真实文章生成、新计费任务、余额查询或预算变更。候选已停止在零调用验证阶段，等待下一次真实验收授权。

## 7. 新候选完整文件与 SHA256

以下是候选叠加文件完整清单；`manifest.json` 另列完整隔离执行环境全部 164 份 Python 源码 SHA。

| 文件 | 相对基线 | SHA256 |
| --- | --- | --- |
| creation/runtime.py | unchanged | `abba3c1084e0953740a00916c03987efab9d71e1d60afc7aee0a637772cbfb8d` |
| geo_source_cards/api_worker.py | modified | `d3fcdc544f9a81a7f296a321754221270186928ad053f5bf6cd2d6ca27b26c45` |
| geo_source_cards/article_logic.py | modified | `82994f4ef69f319899c90d0b1215bad72d604665c447e83006c39048d438dea5` |
| geo_source_cards/consumer_prompts.py | modified | `2920d28e61e74b50a9a7b42c59059d596f5cbbcf3f000422d659ea27a4c8bfb3` |
| geo_source_cards/daily_editorial.py | unchanged | `c98993370318ea24f0fdf2d72e7f62f64148503bd13570f43f5fbe7548d12c75` |
| geo_source_cards/repair_router.py | unchanged | `9cda2d0f1bdc9fb42881e16a48637efa74c4de08d9e0459914c5f5eb78bc3799` |
| geo_source_cards/review_arbitration.py | modified | `ad45f5629aad92a090e2c6d4bb11936aa81ae987eb83d19cda880b8ffd592e51` |
| geo_source_cards/review_inputs.py | unchanged | `c8ff98708204ef2ce176c6dd2eeb7c9702e4421e5ef583c05895f612ca80a5ec` |
| geo_source_cards/review_quality.py | unchanged | `5da64b2cd498a58c3dffc83eb89da1d39d0629f8c420317dfe190728815d8dcf` |
| geo_source_cards/section_writer.py | modified | `de3a32201b30279866b2a93fab4dbbf300e9f7bc67aedcf3db2079c71011bec1` |
| geo_source_cards/structure_analyzer.py | modified | `dd9d2b04f824b724492b71624fe2a6f7adc8a960aad965c92453e0daba132ade` |
| geo_source_cards/structure_protocol.py | added | `c121959b8ed9a0d448f8ee538ef6090008ae4043d93bdcf3569dc71a903d5dd0` |
| tests/test_arbitration_batches.py | unchanged | `6f0835d15c3b695f9f236e2650a00768b655cd72ef1935b8d3963c9f8dd61185` |
| tests/test_b1_b2_offline.py | unchanged | `be144ebe82a5e10dbda1b229a7da2851e5ecca6e06a3f9992e7cced1bc561267` |
| tests/test_b2_repair_entry.py | unchanged | `51308666531d8215f0ccb4b70664b08aee4ce5d5bf783b582b901c82916e99fd` |
| tests/test_section_budget_revision.py | unchanged | `a3a475c6dae2915772b5b24d968d9d0ac0c351e594c4e9b7e4c3e8edf81a7b7c` |
| tests/test_structure_recovery.py | added | `3f0a3cfd0882d529844f35ce511e433d4237e79f908705976b8dfcd5ebdd4bba` |
| tests/test_three_agent_quality.py | modified | `f2e42cd50fd156a64de6c0dc31f3c1b6c4cd41676a043e851330d509557a39af` |

完整差异：`candidate.diff`。最终 Linux 目录：`/opt/monitor/geo-capture/maintenance/20261023-structure-recovery-v3-final/`。本地目录：`C:/Users/78567/Desktop/隐身浏览器/maintenance/structure-recovery-20261023`。
