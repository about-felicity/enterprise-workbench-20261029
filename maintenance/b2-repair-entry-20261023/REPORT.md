# B2非仲裁返修入口：独立候选最小修复与零调用验证

时间：2026-10-23 11:32（北京时间）。新版本 `candidate-b2-repair-entry-v2-20261023`，基于 `candidate-b1-b2-v1-20261023`。

**本轮完成独立候选修复及离线验证，没有进行真实文章质量验收，也没有部署。** 真模型API、余额API、外部业务服务调用均为0；没有新增Agent或依赖，没有启动排行01/测评02，没有修改原任务、费用、预算或生产源码。

## 1. 修复范围与版本保护

- 仅修改候选运行源码 `geo_source_cards/repair_router.py`，新增 `tests/test_b2_repair_entry.py`。完整diff为运行源码37行增加/1行替换、测试114行增加；其他12份继承文件逐字不变。
- `review_quality.py`、`review_arbitration.py`、`review_inputs.py`仅核查和调用，源码没有修改；没有改审稿标准、篇幅要求、B1行为、预算或任务调度。
- v1完整目录438个文件SHA均保持；本轮保护清单828项及较早33项冻结证据全部核对无变化。原日志和上轮两个失败用例没有覆盖或改断言。
- 根仓库原有已跟踪修改状态不变。本轮新增均在本维护目录，不加入生产恢复源码映射。新候选14个文件完整SHA见manifest.json；差异见candidate.diff。

## 2. 修复前后的真实调用路径

原路径：`prepare → compile_article → route → if bound → if arbitration → enforce`。非仲裁审稿跳过来源核验，可以在来源变化后返回PATCH；正文不匹配导致bound=false时，也没有统一来源入口保护。

新路径：

1. `prepare`读取当前正文、knowledge/product和当前review/result，先执行 `verify_review_sources`，再做可写性分析，并进入route。
2. `route`在计算bound和消费任何审稿意见前，也执行同一校验。只要有quality_pipeline即校验，不依赖arbitration。
3. 从调用方显式提供的当前location读取snapshot；比对磁盘正文、知识库、产品与传入参数，防止调用方继续传旧正文/旧data。不能回退使用旧证书中的source_location来填补缺失的当前来源位置。
4. 复用verify_final，核对正文/产品/知识库、原始research_input/research_result、来源映射和合同的完整指纹；核对独立逻辑审稿的输入摘要和结果结构。有效的revise结果仍允许进入PATCH，未要求审稿先通过才能返修。
5. 再次读取当前输入指纹，核对校验过程中没有变更。原有仲裁证书enforce保留，专项也实际断言它仍被执行。
6. 已存在完整审稿缓存标记时，删掉传入结果的quality_pipeline字段也不能伪装成旧协议绕过校验。真正没有现代审稿记录的旧协议处理保持原有行为。

校验失败抛出 `StaleReviewSources(RepairBlocked)`，携带 `status=needs_reaudit`；有可用当前目录时写入 `repair_source_status.json`，标明需要重新审核、保留旧证据、没有开始新请求。不写新的PATCH、不改旧审稿/证书、不覆盖此前PATCH；调用方不能拿旧意见继续规划。缺失location时只返回明确阻断状态，不向旧证书指向的位置写文件。

## 3. 保存真实来源的前后离线探针

复用原排行01保存的真实research_input、research_result、产品知识库、knowledge及结构。探针正文是简短的方法说明夹具，独立审稿由Mock提供，**不是一次真实模型生成或真实文章审稿**；没有把原有失败文章称为已合格。

在隔离临时目录中修改真实研究资料副本的一条content，正文、knowledge和product均不变；执行的旧/新路由代码分别来自冻结baseline-source和新candidate-source。

| 输入状态/路径 | 冻结v1 | 新候选v2 |
| --- | --- | --- |
| 所有输入不变，route | 原合法行为保持 | PATCH |
| 所有输入不变，prepare | 原合法行为保持 | PATCH |
| 原始来源变化，route | PATCH | 拒绝，needs_reaudit |
| 原始来源变化，prepare | PATCH | 拒绝，needs_reaudit |
| 原始来源变化，旧verify_final | 拒绝 | 继续拒绝，没有降低要求 |

探针确认旧审稿和旧PATCH字节未改；来源变化后的调用没有新增Mock请求，更没有真实模型请求。来源SHA前后、逐入口返回值及错误保存在 `linux-final/probe-linux.json`，本机对应记录为probe-win32.json。没有修改原始历史资料，仅修改临时副本。

## 4. 新增专项与相关回归的实际结果

先运行新增专项，再执行旧专项、上轮失败用例、引擎和创作回归。最终目标Linux：6.8.0-138，Python3.10.12，复用已有虚拟环境，没有安装依赖。

| 测试组 | 执行 | 通过 | 失败/错误/跳过 |
| --- | ---: | ---: | ---: |
| 新增B2专项 | 24 | 24 | 0/0/0 |
| 原B1/B2专项 | 20 | 20 | 0/0/0 |
| 上轮补充测试，原样保留两条失败断言 | 10 | 10 | 0/0/0 |
| 相关引擎回归 | 288 | 288 | 0/0/0 |
| 创作扩展回归 | 78 | 78 | 0/0/0 |
| 合计 | **420** | **420** | **0/0/0** |

新增24项覆盖：原始来源/research_input变化；原始来源映射、writer来源映射、claim_map变化；writer_done/compilation合同变化；正文、knowledge、product磁盘变化但调用方仍传旧参数；bound=false不能绕过；缺少location/指纹/quality_pipeline/独立审稿证据；删除字段不能降级；仲裁校验保留；合法PATCH与合法revise；过期后不产生新PATCH且保留旧文件；旧终验/旧仲裁批次不能恢复；未知请求不重发；预算与执行锁；两轮修订耗尽仍停止。

Windows额外24项专项通过，本轮没有把Windows全套回归记成通过。既有4项Windows平台错误没有在本轮修改；目标Linux创作78项实际通过。

最初新增测试复用了已消耗一次Mock调用的helper，再委托原“未知请求调用数必须为0”断言时失败。已保留windows-special-first.log，改为使用独立fresh fixture；原断言和旧测试源码完全没有改变。此前23项完整通过的中间源码SHA/diff保存在first-pass，Linux初轮日志在linux/；最终新增“删字段不能降级”用例后，重新执行全部420项，最终证据在linux-final/。不把中间记录冒充最终版本验证。

## 5. 新候选完整SHA

| 文件 | 状态 | SHA256 |
| --- | --- | --- |
| creation/runtime.py | unchanged | `abba3c1084e0953740a00916c03987efab9d71e1d60afc7aee0a637772cbfb8d` |
| geo_source_cards/consumer_prompts.py | unchanged | `d4f906ade8e9850ed7c7b5e4da388d25159867b00a15b7541904debd1871d2b0` |
| geo_source_cards/daily_editorial.py | unchanged | `c98993370318ea24f0fdf2d72e7f62f64148503bd13570f43f5fbe7548d12c75` |
| geo_source_cards/repair_router.py | modified | `9cda2d0f1bdc9fb42881e16a48637efa74c4de08d9e0459914c5f5eb78bc3799` |
| geo_source_cards/review_arbitration.py | unchanged | `03aed7119d9d8cac26937e620c3c6710656b85dcddd875c517ec870aea6cdf7e` |
| geo_source_cards/review_inputs.py | unchanged | `c8ff98708204ef2ce176c6dd2eeb7c9702e4421e5ef583c05895f612ca80a5ec` |
| geo_source_cards/review_quality.py | unchanged | `5da64b2cd498a58c3dffc83eb89da1d39d0629f8c420317dfe190728815d8dcf` |
| geo_source_cards/section_writer.py | unchanged | `c96957d1b2c6e82487841f487ac079df0b7c68fbbc6ac45f43debe189599d22c` |
| geo_source_cards/structure_analyzer.py | unchanged | `f4f213e49d18bc7f99855e1cc545779d3fa42db61c04043d569ee8605915eede` |
| tests/test_arbitration_batches.py | unchanged | `6f0835d15c3b695f9f236e2650a00768b655cd72ef1935b8d3963c9f8dd61185` |
| tests/test_b1_b2_offline.py | unchanged | `be144ebe82a5e10dbda1b229a7da2851e5ecca6e06a3f9992e7cced1bc561267` |
| tests/test_b2_repair_entry.py | added | `51308666531d8215f0ccb4b70664b08aee4ce5d5bf783b582b901c82916e99fd` |
| tests/test_section_budget_revision.py | unchanged | `a3a475c6dae2915772b5b24d968d9d0ac0c351e594c4e9b7e4c3e8edf81a7b7c` |
| tests/test_three_agent_quality.py | unchanged | `7c4bb8ece75ce4a68aa77213a5403d91337eba1eac8d6cd62aa49a99caeee83e` |

## 6. 生产、费用与请求保护

- 目标Linux仅通过SSH传输/执行离线副本。测试进程在导入业务代码前禁止外联socket及未Mock HTTP；已有下载测试仅允许本进程127.0.0.1回环夹具，不调用外部业务服务。未使用模型、余额、搜索、浏览器或数据库网络服务。
- 生产核验使用文件SHA和只读SQLite：161份生产源码/原稿/控制/预算文件前后相同，费用账本2004行及完整逻辑摘要前后相同。没有清账、释放未知预留、提高预算、重建任务或恢复旧任务。
- 无任何新增真实模型/余额请求；探针来源失效后连Mock请求也没有新增。未知请求保护、预算预检、执行互斥和两轮内容修订限制均在相关测试中保留。
- Linux候选位于独立维护目录 `/opt/monitor/geo-capture/maintenance/20261023-b2-repair-entry-v2-final/`，没有覆盖engine或creation生产目录，没有重启服务，没有把候选安装到生产。

## 7. 未完成与验证边界

最终运行的420项没有未通过、错误或跳过；本轮B2入口来源版本阻断已在离线代码路径和保存资料探针中修复。有限用例不能证明所有未来输入均无缺陷。

**真实文章质量验收未执行，历史真实结果仍为0/2。** Mock只验证来源版本、路由、缓存和保护行为，没有证明事实判断、逻辑语义或写作质量。排行01/测评02未启动新API轮次；预算未变、无新增可用费用。

**生产未部署**，现有生产入口不会因本目录候选通过测试而自动获得修复。是否真实验收或部署需后续明确授权，本阶段停止在独立候选与零调用验证。
