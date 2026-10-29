# GEO统一升级与长测工作记录

**2026-10-16 09:55 原长测收尾：** rowidfix12h固定窗口结束，failed，独立截止09:48:05执行。新DS批次不属于manifest，截止跳过并继续active；原监督器因此等待无关lane，保留raw status/metrics后按六原批次独立审计，仅09:53:32.469关闭到期监督记录器。1800唯一文字回执PG保真、待回传0；四条带入不冒充新发，原阻塞和6次已完成错误重试保留。记录器2151采样/最大21.897秒/sample_error0，墙钟43527.795秒，窗口仍43200秒。两次用户前端重建记入验收。最终证据 `reports/20261015/capture-12h-final/`，服务器原root/final_adjudication.json；不称监督器自行通过或六通道连续通过。创作验收此前已报告，两个报告均完成后按授权暂停heartbeat，geo/10保持PAUSED，今天的新DS不暂停。

**2026-10-16 09:21 用户指定前端变更：** 已在本地服务器移除GEO面板夸克展示，正式前端镜像no-quark-20261016/local；仅monitor-dashboard重建，其他10个运行容器未重启，采集队列与长测ID/截止不变。预览及正式3000真实API/界面、手机布局、六通道与创作加载均通过；39/39源码映射重新匹配。历史数据与统计计算规则保留。详见 `../20261016-no-quark/REPORT.md`，长测应如实记录这次已知前端重建。

**08:20新增保护阻塞：** 豆包1第761题08:00:23.771一次点击，08:15:26.770原请求900秒未完成而needs_attention；08:19只读原生与08:10同一首问/答案及106字hash一致、text finish=false。UI重新生成不当完成证明，已备份原任务/原生库/事件/UI，未点重试/生成/发送、未重启或改队列。此前760文字processed保真，片段不算正文成功或负样本。当前4处阻塞（两豆包/元宝/DS），仅文心/百度继续，296文字及274观测57唯一PG保真通过。原12h ID/09:48:05不变；08:10段首次点击时间已按epoch更正为08:00:23。本新增阻塞通知一次后相同状态安静。

**08:10访问恢复：** SSH首次连接恢复，原12h监督/截止定时器active，当前采样新鲜，原09:48:05不变。已完成豆包1文字760/文心293/百度270观测56唯一PG保真通过，三处既有阻塞不变。豆包1原761题08:00:23一次点击后，08:10正文106字且原生finish=false，仍在原900秒等待内（08:15:23截止）；备份原任务/原生SQLite/UI，仅只读，无按钮操作/重发，片段不算成功或负样本，下轮核。百度第15轮1题DNS失败已留观测，unavailable32=30卡片不完整+2DNS。08:04访问缺口保留，不伪造当轮核验，未重启或改队列。

**08:04轮访问缺口：** SSH三轮有限只读连接尝试未成功（TCP超时，末轮密钥交换No existing session），独立22端口测试可达；仅确认监测访问失败，不判断服务器/采集故障。最后实时成功证据为07:59轮，本轮未更新live-validation。原12h ID/09:48:05不变，未远端修改/重发/重启，下轮只读重试。详见可靠性报告及ssh-monitoring-gap-20261016-0804.json。

**06:05只读更新：** 豆包1第652题首次同类已完成错误答复后，既有worker退避并在新CID重试1次，06:03:14.605完成528字/11来源，原生身份/首问/完成标记一致。failed_attempts=6、重复点击任务=6（576/608/612/629/631/652），全部原失败保留；653文字processed/PG全字段保真通过、待回传0。百度unavailable25（24卡片不完整、1历史DNS），新增第12轮20题不算正文成功或负样本。三处阻塞及原12h截止不变，无手动发送/改队列/重启，同类恢复不反复通知。

**05:45只读复核：** 豆包1第631题既有新CID重试完成486字/11来源，首问、身份和完成标记一致。累计failed_attempts=5、重复点击任务=5（576/608/612/629/631），全部已获成功正文；635文字processed/PG全字段保真通过、待回传0。全部原失败保留且不算正文成功或负样本，三处阻塞与原12h截止不变，无手动补发/改队列/重启，同类恢复不重复通知。

**05:40只读更新：** 豆包1第629题既有新CID重试完成410字/12来源，累计630文字processed与PG全字段保真通过、待回传0。第631题首次同类已完成12字错误/0来源已归档，05:39:46仍prepared/sending_once且快照未见第二次点击或成功正文，后续待核。failed_attempts=5、重复点击任务=4（576/608/612/629）；全部失败保留且不入正文成功/负样本。无手动补发/改队列/重启，三处阻塞与原12h截止不变，同类事件不重复通知。

**05:35只读更新：** 豆包1第629题首次返回已确认完成的同类12字错误答复/0来源，05:34:06归档第四条failed_attempt；既有worker安排90秒退避，05:35:01仍pending且只有一次点击，尚未恢复。重复点击任务仍3，628文字processed/PG全字段保真、待回传0；第四条错误不算成功或负样本。本轮未手动发送/改队列/重启，原三处阻塞及12h截止不变，下轮核对629后续。

**05:17只读更新：** 豆包1第612题同类已完成12字错误答复后，由既有worker退避90秒、在新CID重试一次，完成569字/12来源。原生身份、首问/完成标记及失败归档一致；累计3次失败、3题两次点击（576/608/612）均保留。累计612文字processed与PG全字段保真通过、待回传0，错误答复不计成功或负样本。本轮无手动发送/队列修改/重启，原三处阻塞与12h截止09:48:05不变；脱敏审计已更新，同类恢复事件不重复通知。

**05:11同类错误累计2题：** 豆包1第608题“推荐一款护手霜”首次05:08:21.620已完成12字错误答复/0来源；既有worker归档失败、90秒退避后05:10:26.147新CID重试一次，05:10:50.110完成511字/12来源。只读原生复核首问、身份、完成标记一致；failed_attempts=2、重复点击任务=2全部保留，不称零失败/每题一次点击。原三处阻塞和12h窗口/截止不变，本轮未手动发送或重启，同类恢复事件不反复提醒。

**10月16日04:36最新事件：** 豆包1原第576题“推荐一款造型喷雾”首次04:32:13.683点击收到原生已完成错误答复“出了点问题，请稍后重试。”（12字/0来源）。既有worker归档confirmed_transient_error并90秒退避，04:34:16.814在新CID重试一次，原题两次点击/两套request与answer均保留，后答536字/12来源已processed。只读原生与失败归档一致、04:36累计577文字回执PG全字段保真且零积压；不把错误答复当成功/负样本、不称零失败或每题一次发送。原任务库和两次原生结果备份在服务器doubao1-transient-retry目录，脱敏 `../20261015-reliability/doubao1-transient-retry-audit.json`。supervisor重复点击审计标记保留并解释；本轮未手动重发/清缓存/改队列/重启。原三处阻塞、12h ID和09:48:05不变，不重复通知创作完成；本事件通知一次后相同状态保持安静。

**10月16日01:12创作6h完成并报告：** 原rosterfix1792062355，01:06:05.139完成，21609.294秒/360采样/异常0/passed。9基线＋1实际新增，共10篇全部Word/Markdown/receipt哈希、独立审稿、完整媒体正文和GEO出处通过；其余窗口是idle可用性与证据监测，不能称6h持续付费生成。共享账本48次估算0.536386元，窗口1次0.013517元，未知/预留0，非服务商账单。独立deadline marker 01:05:57.040，只暂停原job，API/worker运行。最终脱敏报告在 `reports/20261015/creation-6h-final/`，本轮向用户仅报告一次。12h rowidfix/09:48:05与三处阻塞不变，heartbeat保持ACTIVE继续采集监测，geo/10仍PAUSED；两项都完成报告后才暂停heartbeat。

**23:52最新状态：** 豆包2第311题原23:36:15发送1次，首问/原答案身份确认，135字正文text_block.is_finish=false，首次UI“消息加载失败”。只读打开原历史会话后正文hash及原身份不变，完成标记仍false，未点击重试或重新生成，原900秒保护保留；不以UI重新生成按钮推断答案完整。原任务/原生SQLite备份与历史回查证据服务器 `maintenance/20261015-reliability/pending-doubao2/`，本地 `../20261015-reliability/doubao2-pending-audit.json`。不重发/清缓存/改队列/重启worker或Android；此前310processed保真记录保留，本条不入库、不算成功或负样本。当前豆包1、文心、百度及创作继续，元宝/DS仍旧阻塞。原12h rowidfix09:48:05和6h01:05:56均不变，不重置或称六通道连续通过；相同阻塞不重复通知。

**23:41最新状态：** 元宝第322题一次发送点击后，服务端完整历史出现同CID、同原始client request ID、同问题的两组问答（1/2与3/4）；第一答1412字19来源，第二答1699字48来源，两次稳定读取一致。当前原生读取器只暴露第二组，首问门禁拒绝，900秒保护停；两组未入库／未当成功或负样本。内部重复原因未证实，不能将一次点击宣称一次服务端生成，serverIndex3也不是第三条用户消息。原SQLite／事件／基线／原生及render快照／完整历史备份保留，脱敏证据 `../20261015-reliability/yuanbao-duplicate-request-audit.json`。未放宽门禁、未重发／清缓存／改队列／重启worker或Android／开投屏；320条已入库文字与1条非文字审计PG保真仍通过。其余四采集通道与创作继续；DS仍原登录阻塞不反复提醒。两个测试原指针与09:48:05／01:05:56不变，不借历史累计或重置窗口称六通道12h通过。后续仅可严格读取原首问第一答，不盲目恢复或发送；相同阻塞保持安静。

**22:10最新状态：** DeepSeek下一题check_ready发现授权失效，GEO与原内容工作台两个原profile只读核对均跳转官方/sign_in，complete＋Log in、两次观察一致。21条已完成均processed，399题pending，没有未知发送或积压，不重发、不清缓存、不重启服务顶替授权修复；需用户原内容工作台登录后再同步校验恢复原任务。其他五通道及创作正常。rowidfix12h指针／09:48:05与创作6h／01:05:56均保持，窗口内DeepSeek新增1条，不能把这次窗口称六通道连续12h通过。证据 `../20261015-reliability/deepseek-auth-audit.json`，相同阻塞只通知一次；heartbeat继续其他通道与创作，不因已知登录问题反复提醒。原profile与所有任务证据保留。

21:50补充：历史消息rowid误判修复后，两台豆包连续3题新增processed及PG保真通过，累计191／203，原188题点击1次不变；修复后最小间隔60.99／57.88秒。正式公网六采集控制／创作／Word／鉴权CSRF／mobile再验通过，无JS错误。9项关联回归、39源码SHA匹配。脱敏报告 `../20261015-reliability/history-row-fix/REPORT.md`；后续只读 `/tmp/validate_history_fix.py` 可复核。当前采集新12h rowidfix1792072084至次日09:48:05；原6h创作至01:05:56，heartbeat仍跟进二者，未完成最终时长验收。

**21:48最新覆盖下方采集窗口：** 豆包1第188题因旧第167题相同原生请求被SQLite重新插入、rowid增大而误判existing conversation；本题新CID／唯一首问／一次点击均已证实。基线新增原消息身份指纹，并以只读事务一致冻结；忽略严格相同旧请求，旧会话新消息仍禁止。原188题两次稳定完整读取、不重发，processed188。两台豆包安全排空换core/adapters后恢复原批次；其余四通道、核心、Android、创作保持运行。9项纯问题回归含新增3项通过，39源码映射SHA一致。新12h `question-only-soak12h-rowidfix-1792072084` 21:48:04.675→次日09:48:05，同名supervisor/独立deadline timer；旧videofix1792066775 interrupted且timer关闭，不能按08:19截止或称通过。创作6h原ID／01:05:56不变。证据服务器 `maintenance/20261015-reliability/doubao-history-row-fix/`；`/tmp/recover_doubao_history_row.py`、`/tmp/retest_history_window.py` 已执行的一次性修复禁止重跑。原任务SQLite／旧baseline／模块／失败事件完整保留；连续新题实采验收进行中。heartbeat已更新新ID及截止，仍ACTIVE。

20:24复验补充：元宝修复后连续7条正常文字processed，累计126文字回执全部PG保真；1条非文字原生观察的两组7项视频原始数据独立审计回执及PG一致，原题点击仍1。103项回归、正式公网六通道/创作/Word/CSRF/mobile及丢响应同ID重试均通过。最新39映射SHA全部匹配，当前source.zip已更新；脱敏validation/tests/public报告在 `../20261015-reliability/video-fix/`。当前12h videofix1792066775及其08:19:36timer active，6h原timer01:05:56 active，无新异常。下段“将重新核SHA”已完成。

**20:19最新，覆盖下方所有采集窗口：** 元宝第120题眼霜问题原生EOF是videoBoxV2占位，最终render另含同ID videoBoxStream轮播，共两组7项。旧NativeClient在parse成功后才更新最终render，parse又要求SEARCH_GUIDE，导致纯视频回答一直required_sources_pending、900s保护停。已修复先读取最终render、严格原CID/msg/首问、两次稳定快照、全部主卡和轮播元数据，原任务完成为completed_nontext；原题只有1次点击，没有重发/重登/清队列。专用非文字outbox/回执经原8791回传，PG完整审计事件run_id空、预期quarantined，不计完整文字成功或产品负样本；native等待审计processed再开始下一题。已真实PG核对全部7项，之后4条正常文字processed与正文信源保真通过，最小50.07s。103项回归通过。详见 `../20261015-reliability/video-fix/REPORT.md`，服务器同目录yuanbao-video-fix/原SQLite、原快照、两次最终读取及proof齐全。只重载元宝worker与控制服务，其他通道/核心/Android/创作worker未重启。新12h `question-only-soak12h-videofix-1792066775` 从20:19:35.527→次日08:19:36；reliability1792064712短窗口归档interrupted并停旧timer，不按07:45旧截止暂停。创作6h仍原ID到01:05:56，不新增付费任务。39映射源码将重新核SHA；自动跟进已更新新ID，helper /tmp/probe_reliability_heartbeat.py 和 /tmp/validate_yuanbao_video_fix.py 可只读复查。仍不宣称12h/6h最终通过。

**19:45最新覆盖下方采集窗口：** 用户授权进一步全链路可靠性升级，详见 `../20261015-reliability/REPORT.md`。12个当前源码组件已部署：native EOF两次稳定快照、元宝实体/信源临时不齐在原请求内限时复核、30秒读超时/最多5次只读重连、耐重启同RID回传退避与鉴权/参数错误区分、网页回传背压/3秒协作排空、DeepSeek短段保留与系统alert区分、采集/创作面板离线禁止写入及同操作ID重试。95项回归及真实Chrome故障注入通过，公网鉴权/六通道/创作/Word/mobile再验通过；39映射SHA全部匹配。六个18:18批次先排空至豆包82/80、元宝98、DS8、文心30、百度39观测/16唯一，再同批次恢复；未重发未知，没有核心/Android/创作worker重启。部署控制服务重启后首个请求遇尚未监听的readiness race，已补有限就绪等待后恢复，无模型重发。新12h `question-only-soak12h-reliability-1792064712` 从19:45:12.910→次日07:45:13；旧fencefix窗口归档interrupted，旧timer停止，不能按07:19旧时间暂停。创作6h仍19:05:55→01:05:56。最新只读分析审计795正文、5873产品证据无差异，pending不当负样本。长测仍未完成，不提前称通过；实时看指针和reliability报告。

## 最新状态（2026-10-15约19:00，接手先看这里）

**19:19最终最新，覆盖后文12h窗口：** 新指针 `question-only-soak12h-fencefix-1792063163`，19:19:23→次日07:19:24，supervisor `geo-question-only-soak12h-fencefix-1792063163.service`、独立同前缀deadline.timer。18:53窗口发现百度journal starts最短58.870655s，原slot在准备前记录，启动／fsync延迟不恒定导致低于配置60s；geo_source_cards/cli.py新增collect_with_completion_fence，每次观测完成或失败后写last_search/last_prompt时间，下一次从结束后等待配置间隔，保守保障请求下限，不复发输入/不加话术。38项网页可靠性／轮序／纯问题／屏障回归通过。豆包2短暂stale之后继续processed，45秒lease小于允许75秒ready，150秒有限lease修复；三原生通过控制API排空已发题、全部回执且无needs_review后换代码同批次继续，不杀Android不清队列。升级证据native-lease-upgrade/report.json。旧窗口原异常/暂停过程完整归档interrupted，旧timer已停，不记通过。all_channel_soak.queue_metrics(since=manifest.started_at)区分当前窗口最小间隔与整批次历史batch_min_send_interval，7项soak记录器回归通过；window_baseline.verified_unique_receipts以当时unique_processed初始化，不把历史全部回执当新窗口新增。恢复包增至33映射文件（多了cli.py），重新核SHA。GEO核心容器在升级中未新增重启，只有三个采集worker安全排空重新载入。创作6h仍是19:05:55→01:05:56，不受影响。

**19:06最新覆盖后文旧6h信息：** 最后一篇研究因原reference_design.py把“• 二硫化硒洗发水”功能说明误当品牌、切断LBR证据，已修复v3 bullet/category guard，9项解析回归通过；仅新GEO engine快照更新，原内容项目安装包不改。对ticket81fa80180b782980a738fd05已回执失败保存原稿/合同哈希后定向repair_research，5个真实品牌取代6项含假产品的名单，原预算不变；最终10/10 accepted，原验收另2篇。创作窗口再次归档interrupted后改为 `creation-soak6h-rosterfix-1792062355`，19:05:55→次日01:05:56；同原付费job，manifest.approved_before有9篇，第10篇是窗口内实际新增，其后固定队列idle期间继续审计，不能称6h持续生成。当前指针正确，旧retest1792061692 timer已停。网页Journal.plan改round,ordinal，先遍历21问题再下轮，原任务ID及完成状态不变、无需重启、后续子进程载入；36项网页可靠性／纯问题／顺序回归通过。主12h窗口不变，最新源码包将增至32映射文件（原30是前一版），重新核对manifest。

19:10补充：32当前映射文件与服务器SHA全部匹配，打包完成；公网复验新增对已完成验收任务真实pause/resume后恢复，2篇成稿及真实长测队列未变，CSRF/Origin/Word/mobile仍通过。成本只读审计 `maintenance/.../audit_creation_costs.py`（服务器/tmp同名）：同原付费批次48次已结算、保守估算0.536386元，无未知用量/费用预留；新6h窗口内1次收尾调用0.013517元，其余窗口前，最终报告须分列，不当服务商发票。原始新6h `approved_in_window`应为1，总10；其他9及另2验收不冒充新增。自动跟进读取同名creation-cost-audit.json或重跑该只读工具。

此前本文“尚未部署／尚未启动”均为历史工作快照。现在六通道运行，元宝投屏关闭，创作已经集成公网；**12h／6h复测进行中，没有最终时长通过结论**。

- 新采集12h：`question-only-soak12h-retest-1792061584`，指针 `/opt/monitor/geo-capture/soak12h_current.json`，18:53:04→次日06:53:05。服务 `geo-question-only-soak12h-retest-1792061584.service`，独立同前缀deadline.timer；六批次仍是18:18的原批次，没有重新创建/重发历史。manifest.window_baseline与status.window_counts区分批次累计／复测新增。
- 创作6h：`creation-soak6h-retest-1792061692`，指针 `/opt/monitor/geo-capture/creation_soak_current.json`，18:54:52→次日00:54:53。服务 `geo-creation-soak6h-retest-1792061692.service`，独立deadline.timer。付费任务仍 `creation-1792060761-3c2baae0`，当前计划10篇，固定队列、原预算和门禁。manifest.approved_before的复测前2篇不计新增；验收另一个任务2篇也不计。必须报告真实生产及空闲时段，不能称6h持续付费生成。
- 原question-only12h短窗口、原creation6h短窗口均归档interrupted，旧timer/记录器已disable；旧all-channel2h也中止保存，不当通过。旧105/105与116/119从未重跑。
- 最终现场计数随时变化：约18:58六通道豆包38/40、元宝44条processed，DS3、文心10，百度21完整观测/3唯一/18去重；创作新队列3篇已审稿，另2篇验收保留。之后只看实时状态，不把此计数当当前值。
- 纯问题native三台各3题验收全部成功，各3个新会话、3processed和PG保真；本地报告 `reports/20261015/QUESTION_ONLY_ACCEPTANCE_20261015.json`。ACK临时CID和XP.q修复已最终部署，Linux最新协议6项+控制14项+soak6项共26通过。
- 创作生产源码 `/opt/monitor/geo-content/creation`，引擎是原已安装包的固定快照engine/geo_source_cards；API回环8804，`geo-content-api/worker.service`，已加到geo-monitor.target Wants。原四内容服务仍按原暂停状态，**不恢复独立抓取调度**。产品事实仍原产品JSON，key仍读原私有文件；Budget继承只将root设为任务，ledger_root保持原 `/home/user/geo-editorial/runtime-api`，0.35/篇、10/日不重置提高。素材只读GEO PG+完整source_content SQLite，长度hash及高/中质量、允许国内媒体与出处核对。
- 原验收任务 `creation-1792060415-1e4e3a8d`：37篇完整素材（8观测/73唯一来源），排行和科普各1篇通过原独立审稿、Word与receipt/hash；旧82篇原成稿保留。新队列目前原引擎有限auto_repair在处理已回执的字数／章节／名单问题，不降低门槛。
- 创作修复：只读balance GET transient原来直接暂停，加有限3次重试；付费complete原函数不增加未知重发。worker最初在首个needs_attention结果就暂停，会阻断原auto_repair；改为只在blocked_unknown_execution或最终含failed_tickets的needs_attention时保护停。已对SUBMITTED原回执恢复，实际修订后通过。原失败和短窗口完整保留。
- 文心旧第9题嵌套load-state Timeout丢失Page.goto前缀，没进入有限只读恢复；修复wenxin_monitor/controller.py保留导航来源、保存原队列备份并调用原SearchRecovery.failure，恢复原题后processed。DeepSeek旧第3题页面点击未确认，保留保护停；只读启动原登录profile读取官方fetch_page，最新五会话均为GEO已完成旧会话且更新时间全部早于原点击，覆盖该时间窗口；失败时首页输入仍为原问题，没有本次服务端会话。严格证明后写submission_reconciliations和完整proof，恢复为已确认未提交。证据服务器maintenance/.../web-recovery/deepseek-unsubmitted-proof.json，原日志／原SQLite备份／权威history哈希保留。**禁止把此特定证明当通用未知重发许可**。发送前稳定1秒重读坐标，只点一次等60秒；之后3/3processed。35项网页可靠性／单次点击位置回归通过。
- 分析修复：移除PG模式先返回无版本磁盘缓存的路径；cache读之前取版本，防并发入库后给旧cache误贴新版本；current/refreshing元数据和前端生成时间提示。回答审计展示原answer而非recommendation_body清理片段，分析口径独立；全局sequence标签改采集记录。分析接口18:53受控重启一次，其他核心/Android未重启；新12h基线在其后。5项真实函数缓存／原文显示回归通过。审计5386产品证据／608回传正文无差异；13日API/PG同口径DS58豆包153Quark42文心211元宝207完全一致。待分析不当负样本，不宣称语义永远无误。
- 大面板前端正式版本 `monitor-dashboard:creation-20261015` (861e7f3a7b9e)，生产源码同步完成。恢复旧tag `monitor-dashboard:before-creation-1792060830`，备份 `/opt/monitor/geo-capture/backups/creation-frontend-1792060830`。VPS新 `/geo_monitor/api/geo-creation/` 显式鉴权、不共享缓存、可信前缀，Nginx -t及auth/fallback不重启验证。公网真实浏览器通过登录、CSRF/Origin、真实无效POST后端校验、三素材通道、新建按钮隔离、六采集通道、390px、Word下载字节SHA；报告 `reports/20261015/unified/creation-public-qa.json`。LAN HTTP UUID不支持已改getRandomValues。
- 当前非凭据源码恢复包 `releases/20261015/unified-current/source.zip` 和manifest，30个映射文件与服务器全部SHA一致。初始question-only-runtime.zip和中间creation zip不是最终版，不盲目重跑现场脚本。源码分类/使用入口见 `docs/reports/UNIFIED_UPGRADE_20261015.md`、`creation/README.md`。
- 清理仅删本轮6个可再生pyc共48017字节，逐文件清单；移除已验收无挂载的本次前端preview容器，builder prune回收0B。未删任何数据、登录、outbox、队列、失败证据或Word。之前8.8GB是另一轮不可重复累计。
- heartbeat id automation（名称GEO十二小时采集与创作验收）已更新上述两个retest ID，每5分钟静默复查，故障安全修复/复测、到期只排空测试所属批次；报告时长和新增量、费用、质量、正文信源/Word保真，下载脱敏报告分别汇报。两项完成后才暂停自身；geo、10保持原暂停。不要用老timer提前暂停新窗口。

用户最新要求：所有模型每题新会话／页面，仅发送问题原文，不能追加编号或提示词；检查模型完整正文和全部信源、13/14/15日豆包差异、GEO分析正确性；合并原内容项目的创作功能，直接复用GEO中DeepSeek／文心／百度数据并集成大面板与公网子路径；元宝验收后12小时采集长测、创作6小时长测，故障修复后复测；清理确定无用中间产物，保留数据与失败证据。

2026-10-15 17:43：已通过控制API对旧all-channel-soak2h-1792056244六个批次请求排空暂停，旧heartbeat暂时PAUSED以免按旧规则恢复。旧测试不记通过，配置变更记录位于服务器该测试的user_requirement_change.json。App与核心GEO／内容服务不停止。正在完整性审计和question-only安全关联改造，尚未启动12h／6h。

实施顺序：
1. 排空确认；截图对应记录和原生数据／UI／接收入库／分析四层对照，找出实际截断或模型差异。
2. 原生发送改为纯问题；使用仅本地保存的原生请求／新会话身份关联，未知发送不得重试；Web检查新会话和纯问题。
3. 受控连续样本，完整性门禁与GEO分析审计／修复，启动复测并安排12h。
4. 创作读取GEO数据适配与现有预算／独立审稿／Word流程；集成同源前缀API及公网鉴权，验收后6h实际业务长测。
5. 依赖扫描、删除可再生无用项清单、稳定分类入口与运维文档；核对服务。

凭据仅用既有配置读取，不写报告。旧105/105批次、116/119历史、原生所有失败日志／outbox／receipts／登录profile保留。没有用户授权自动发布文章。

## 已完成／现场续查（约18:10以后）

- 原六通道已排空：旧DS3/3，文心10/10，百度10完整观测、2唯一+8去重；旧豆包及元宝均保留。旧2h supervisor/timer尚未停，仍只跟旧manifest，heartbeat automation已PAUSED，后续应归档interrupted并停旧记录器/定时器，不当通过。
- 截图run_no 42810实际run_id doubao-b296be6c80e10dd9d3cd/account2，385字；42941 run_id doubao-53b725db277198dacb02/account1，121字。原生SQLite各2块、1正文块，全部is_finish=true；拼接原生正文与monitor_runs.answer完全相同，未发现截断。两条真实发出的问题都含原UUID采集后缀。最近150条monitor_ingest_events原正文与monitor_runs.answer全部一致。13日混DESKTOP-1H7ILU2和native来源，同日桌面眉毛平均530字/native188字，不能归因日期；不宣称UUID已证明为短答唯一原因。只读证据服务器 /opt/monitor/geo-capture/maintenance/20261015-unified/{native-body-layer-audit.json,native-blocks-42810.json,native-blocks-42941.json,ingest-normalized-layers.json,doubao-history-summary.json,screenshot-raw-runs.json}。尚需下载脱敏报告并审计所有模型／产品grounding／统计API。
- 已下载23个GEO生产Python源码（非配置）至 geo-monitor-deploy/server-source/，以及 doubao_source_content_worker.py。这是主GEO源代码快照，server-source/monitor_core/{ingestion,analytics,database,product_analysis}.py 等真实代码。无AGENTS.md发现。
- 新纯问题native协议已部署：redroid-deploy/question_only_core.py、question_only_adapters.py、question_only_delivery.py、question_only_worker.py。部署于 /home/user/redroid-doubao/geo-batch-code/。旧worker/core未改。纯Queue允许wire_question重复，UUID只在本地；新会话基线+native requestID关联，不在原地改旧队列。只绑定服务端确认后的新CID、首个用户问题；未知点击不重发，全部原始块保留。Doubao和YB使用原接收协议/processed。复用原设备锁。delivery按完成ID缓存，避免12h逐轮重复加载全部大结果JSON。
- control_panel/native_entry/panel.html升级：新native批次prompt_mode=question_only；旧有UUID提示批次禁止resume（可新建）；native最大200轮以容纳12h，web仍20。面板动态rounds.max。前端尚未更新“第42941轮”误导标签，也尚无创作入口。
- 部署备份 /opt/monitor/geo-capture/backups/question-only-1792058297，只有geo-monitor-status服务重启，核心Docker/Android未重启。安装脚本 maintenance/.../install_question_only.py 是一次性现场部署，不盲目重跑（其中初始zip已落后于后续ack修复，最终需重打包）。本地纯问题6项测试通过（新增同一native请求local->server CID转正），控制面板14项通过；服务器最初4项纯问题测试通过，最新6项尚需上传重跑。
- 三台native实测每台同一问题“推荐一款睫毛增长液”连续3次，验证重复问题必须3个新会话：指针 /opt/monitor/geo-capture/question_only_acceptance_current.json；目录 /opt/monitor/geo-capture/maintenance/20261015-unified/question-only-acceptance。
  - doubao1批次 geo-panel-doubao1-20261015-175827-7cb020bc；首题曾临时CID main_...-local 转为38447402849913602，因早绑定一直等待；补齐服务端确认门禁及canonical_binding。原发送只发生1次，临时绑定另存.local-before-ack.json，ledger promotions保留。没有重发/清队列。首题481字11来源已processed；为安全载入新代码，先API排空到1/3，再运行 /tmp/resume_canonical_acceptance.py 恢复原任务，剩2题正在跑。
  - doubao2 geo-panel-doubao2-20261015-175827-76e30eae，3/3 processed，第三题同临时CID转正只读修复，524字9来源；complete。
  - yuanbao geo-panel-yuanbao-20261015-175828-60d0d3fc，3/3 processed，complete。首题native createTime为XP.q unsigned wrapper {text:"1792058317"}，最初float(dict)导致worker安全重启；已加native_timestamp精确处理XP.q，无重发，原题取得回执。
- /tmp/inspect_acceptance.py 查看上述三队列健康/状态/事件；/tmp/read_pending_binding.py 是单条诊断勿直接当通用恢复；/tmp/promote_pending_bindings.py 已执行。当前源code ack修复已安装，但首次Zip需重包。

## 内容创作接入调查（未实施）

原生产 root=/home/user/geo-editorial/runtime-api，venv=/home/user/geo-editorial/venv，package /home/user/geo-editorial/venv/lib/python3.10/site-packages/geo_source_cards。原4服务仍运行但control paused/login_required/revision60，api.health paused；不要resume旧采集调度来实现新功能。
原settings单篇0.35元、每日10元、每类10篇、05:00。原有writer accepted93/research accepted85/review accepted82，成品目录在 root/approved/*/*/*/receipt.json（不是root/articles，最初inventory算0不代表无成品）。
GEO已有文章正文SQLite：/opt/monitor/doubao_source_content.db，source_content表：url PK,final_url,status,fetched_at,content_type,http_status,extraction_method,extraction_quality,title,content_text,text_length,content_hash,error,attempts。另JSON index /opt/monitor/doubao_source_content_index.json 102959条（86761 ok等），只是excerpt，不能拿其节选代替全文；必须只读SQLite完整content_text、核对hash/length，仅high/medium和原国内媒体允许名单，保留原GEO run/model/question/source provenance。GEO PG monitor_sources(model_id,run_id,url,canonical_url,title,source_type,media,payload...) 与 monitor_runs(day,question,answer,payload...)，原始回传在monitor_ingest_events(record,envelope,request_id,run_id,model_id...)。百度卡片与文心model_id都wenxin，原record.capture_mode/source_device区分。
原创作引擎可复用 daily_editorial.prepare_day(root,articles_jsonl,product_file,date,max_per_category)，输入row model/question/sources，每source带article{status:fetched,text完整,...}；它只选DEFAULT_MEDIA认可域名并用原genre_pools排行/科普分类，来源引文严格子串验证。API worker Worker.once/tick可直接跑已准备资料，不需要再抓平台。将新入口放GEO独立组件，读GEO数据，不启动原scheduler/session_watch/采集；旧队列/账号/成品保留。API recheck只需要DeepSeek API balance和GEO素材，不要复用pipeline_control.recheck的网页登录门禁。
需共享原预算ledger，不能通过新runtime重置每日限额，也不能用SQLite文件跨目录symlink（WAL风险）；可给Budget新增显式ledger_root参数，canonical路径 /home/user/geo-editorial/runtime-api，原设置预算保持。API key只读原 /home/user/geo-editorial/secrets/deepseek.key，不复制到报告/前端。
新GEO内容控制API应独立回环服务，通过GEO大面板同源白名单网关，公网/geo_monitor prefix+鉴权/CSRF/idempotency，支持创作任务设置、新建/暂停/继续、状态、成稿Markdown/Word下载、原出处与费用。不要自动发布文章。原有Word完整性校验writer_handoff.word_matches_draft已存在。
尚未启动12h采集或6h创作测试，尚未做清理。需完成全部实施、实际运行验收、长测启动与heartbeat跟进再汇报，不夸大通过。
