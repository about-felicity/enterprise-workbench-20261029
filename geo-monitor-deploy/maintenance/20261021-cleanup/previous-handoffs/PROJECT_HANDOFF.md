# 内容工作台：新会话交接文档

> **2026-10-16 00:40最新总交接：请优先完整阅读根目录[CURRENT_PROJECT_HANDOFF.md](CURRENT_PROJECT_HANDOFF.md)。** 本文件后续是历次历史现场。当前11容器、GEO六通道和新创作已上线；豆包2/元宝/DeepSeek三处阻塞，豆包1/文心/百度继续；原12h rowidfix至09:48:05、原6h创作至01:05:56，均未发布最终时长报告。旧批次、未登录/白屏、旧截止及旧启动命令不可直接沿用，以最新可靠性报告和服务器指针为准。当前heartbeat仍在旧线程运行，新对话不要重复建监测或并发恢复同一任务。

> 2026-10-15晚最新：元宝已登录，无头采集与三原生纯问题3次验收完成，投屏关闭；六通道12小时复测进行中。创作功能已独立迁入GEO `/opt/monitor/geo-content`，仅取GEO已有DeepSeek/文心/百度完整素材，保留原预算与审稿/Word门禁，原独立采集调度不恢复。公网入口 `/geo_monitor/#creation` 已通过实际鉴权/按钮/Word字节验证。先读[统一升级报告](geo-monitor-deploy/docs/reports/UNIFIED_UPGRADE_20261015.md)和[现场工作记录](geo-monitor-deploy/maintenance/20261015-unified/WORKLOG.md)，再查实时两个长测指针；下面的白屏/未登录/正在实施等描述均是历史现场，不是当前状态。

> 2026-10-15新增元宝独立无头Android：容器`yuanbao-hpe14-android13`、独立卷、回环5559→Windows15559，官网当前包2.88.0，系统／App已切简体中文，投屏窗口“Yuanbao - Login”。用户验证码后白屏，私有日志确认X5渲染子进程循环退出；已备份配置并尝试SDK内置系统WebView开关，尚待用户通过正常登录入口验证生效，不能称登录修复完成。自动审批拒绝直接唤起私有登录WebActivity的诊断命令，后续已改走可见首页登录入口；当前停在用户协议确认，未替用户确认或获取验证码。原生SQLite表已找到，只读发现／结构门禁3项Win与Linux测试通过；消息表仍空，尚未实现并验证完整元宝采集，不启用自动批次。原10容器保持运行，加元宝共11个；原五通道配置、队列、登录未变。继续先读[元宝说明](yuanbao-deploy/README.md)，当前脱敏证据[readiness](yuanbao-deploy/reports/readiness-20261015.json)，私有原始日志／偏好备份仅在服务器`/home/user/redroid-yuanbao/diagnostics/login-20261015/`。

> 2026-10-15 14:17最新维护：本地186个文件及服务器117个工具／历史脚本完成实际分类，稳定生产入口保留。10个运行容器、8个LAN常驻服务及看护timer、3个VPS服务均实际重启并验证；初次Android启动检查失败经有界就绪等待恢复，初次失败记录保留。百度原批次阻塞确认为桥接先取旧SQLite快照、后观察子进程退出的竞态，已修复并继续原批次；新增5条完整processed、1次不可用，当前89条完整观测／89processed／30唯一、8次不可用、8题待执行。391条唯一回执与数据库保真通过，所有原结果未变。两个豆包仍暂停116／119，旧105／105保留；文心126／126完成。DeepSeek真实登录过期，用户明确“先完成其他服务，稍后登录”，内容工作台保持原登录暂停。公网鉴权与控制链路验证通过，83项适用测试通过。完整分类、回退和脱敏证据见[重启恢复报告](geo-monitor-deploy/maintenance/20261015-reorganize/RESTART_REPORT.md)。下文状态均为历史快照，不能覆盖本条。

> 2026-10-15 已整理统一入口 [README.md](README.md)及[GEO运维入口](geo-monitor-deploy/README.md)，后续先读统一入口再查实时服务。本次按哈希清单清理旧镜像下载、重复OCI blobs、编译/构建缓存和安装包，完整压缩旧隧道日志；本地净减少约5.31GB、服务器实际空闲增加约3.50GB。10个运行容器、镜像/数据卷集合和正式业务服务未变。归档后退出针对10月9日且从未进入计时的旧验收观察器，关闭已完成双豆包测试记录器与deadline timer的开机项；没有标旧验收通过。队列、登录、成品及原生修复证据保留，详见[清理与恢复报告](geo-monitor-deploy/maintenance/20261015/CLEANUP_REPORT.md)。下文仍保留历次现场，旧的enabled或运行状态不代表清理后状态。

> 2026-10-15 13:17分析只读复查：当前374条独立回答370条ai_verified/4条ai_pending（豆包1 115/116、豆包2 119/119、文心109/111、百度27/28）。最近小时接受342条、无调用异常日志，但部分提取结果被校验拒绝，正文抓取仍有缺失。13:18面板实际analytics返回豆包235轮/待1、文心139轮/待3，与DB一致。不能继续把11:40的227条当前积压当实时状态，也不能宣称所有分析无误或所有信源正文完成。详见 [最新分析复查](geo-monitor-deploy/docs/reports/ANALYSIS_PROGRESS_20261015_1317.md)。本次未改服务、队列或发起额外AI调用。

> 2026-10-15 双豆包两小时长测已完成，test_id=doubao-soak2h-1792030883，10:21:23–12:21:23采集窗口，12:22:00排空暂停。豆包1/2分别116/119条完成、processed与数据库保真复核，最小间隔53.004/56.332秒，零重复请求/失败尝试/回传错误。两个模拟器和旧105/105保持，未重跑；详见 [DOUBAO_2H_REPORT_20261015.md](geo-monitor-deploy/docs/reports/DOUBAO_2H_REPORT_20261015.md)。仅前端按授权更新，其他核心容器和内容工作台未重启。最终复查百度12:17卡片不完整重试2次耗尽，failed_deferred证据保留，84完整processed/28唯一/56去重/6不可用，需单独排查，不盲目清队列重发。DeepSeek仍待登录，文心仍运行。最终汇报后暂停heartbeat automation；geo、10保持原暂停状态，不改其他采集。

> 2026-10-15 11:55–11:57 已保证公网 [1any.top/geo_monitor](https://1any.top/geo_monitor/#capture/doubao1) 可操作五通道采集控制。VPS新建保持原auth_request且禁缓存的专属控制location，经原13000→LAN3000隧道；前端支持子路径、HTTPS来源校验、Secure前缀Cookie及同源API。真实公网浏览器验证（含写鉴权、跨站拒绝、不同客户端会话隔离、桌面手机）通过，没有实际启停/重建生产任务。只更新前端和平滑reload VPS nginx；采集、内容工作台、SSH隧道及其他容器未重启。详见 [VPS_GEO_ACCESS_20261015.md](geo-monitor-deploy/docs/guides/VPS_GEO_ACCESS_20261015.md)。当前源码包dashboard-vps-prefix-20261015.zip，旧内网集成包不能覆盖。两小时豆包长测继续，产品分析积压仍属另一个问题，参见11:40分析核查报告。

> 2026-10-15 采集控制台已接入[GEO大面板“采集控制”](http://192.168.31.106:3000/#capture/doubao1)，复用8803既有五通道任务服务与状态，支持全部原控制能力。新增同源白名单网关，独立cookie、CSRF/Origin和操作防重保留，桌面/手机浏览器验证通过；测试没有实际暂停或重建生产任务。仅前端容器切换，其他核心容器、内容工作台与采集进程不重启。发布备份 /opt/monitor/geo-capture/backups/dashboard-integration-1792034762，原镜像 monitor-dashboard:before-capture-1792034762。详见 [集成部署记录](geo-monitor-deploy/docs/guides/DASHBOARD_INTEGRATION_20261015.md)。双豆包两小时长测及其截止计时器继续运行，不将此次前端发布误报为模拟器/worker重启。

> 2026-10-15 一小时长测已于11:05:08完成3600.38秒、61次采样。稳定性未通过：文心10:41导航ERR_NETWORK_CHANGED中断，10:57已备份修复并恢复原批次；文心窗口新增22条、百度36次完整观测/11条唯一入库，合计含双豆包重叠结果114条保真核验通过。DeepSeek仍登录阻塞。原核心容器、内容工作台、模拟器未重启；旧豆包105/105保持。实际报告与脱敏证据见 [GEO_1H_REPORT_20261015.md](geo-monitor-deploy/docs/reports/GEO_1H_REPORT_20261015.md)。一小时heartbeat geo汇报后暂停，双豆包两小时heartbeat automation继续，不能误停采集或其他自动化。

> 2026-10-15 10:54 一小时长测heartbeat发现文心于10:41:28停在39/126（39条全部processed）。已确认百度首页Page.goto报ERR_NETWORK_CHANGED，发生在本题搜索导航之前；10:57备份后向独立GEO SearchRecovery补充明确导航错误分类，归档唯一失败任务并恢复原批次，原39条逐项未变。详见 [导航故障记录](geo-monitor-deploy/docs/reports/WENXIN_NETWORK_CHANGE_20261015.md)。一小时记录器的异常必须保留，不可宣称连续通过；其他采集未重启，双豆包两小时长测继续。恢复验收需查实际新增processed，不能只看running。

> 2026-10-15 10:21:23 用户要求两台豆包开始两小时真实采集长测，已新建独立批次并启动，12:21:23自动请求排空暂停。详见 [双豆包两小时长测](geo-monitor-deploy/docs/reports/DOUBAO_2H_SOAK_20261015.md)。test_id=doubao-soak2h-1792030883，服务器指针 /opt/monitor/geo-capture/native_soak_current.json；不覆盖此前网页一小时长测指针。两新批次21题/20轮容量/45秒间隔，面板下次设置已恢复5轮/45秒；旧105/105任务未重跑。heartbeat id=automation，最终报告后暂停自身；geo、10保持各自原状态。两台均已取得首条processed并与数据库核对完整内容；尚非两小时通过。

> 2026-10-15 控制面板已上线：[GEO采集控制台](http://192.168.31.106:8803/)，指南见 [CONTROL_PANEL_GUIDE.md](geo-monitor-deploy/docs/guides/CONTROL_PANEL_GUIDE.md)。五个通道可独立保存下次任务问题/轮数/间隔、新建任务、排空暂停、继续、停止；豆包/DeepSeek可校验登录，百度/文心不需要。文心暂停/继续已真实浏览器验证；新建任务只做隔离验证，没有额外生产提问。两台豆包原105/105保留；DeepSeek仍待登录。已于北京时间10:05:07启动一小时长测，预计11:05:07结束，test_id=soak1h-1792029907；当前状态在服务器 /opt/monitor/geo-capture/soak_current.json，后续报告路径在该文件中。heartbeat automation id=geo 用于复查与最终汇总，完成后应暂停，原内容创作自动化10保持原状态。短时间 recorder-smoke 不能作为1小时通过证据。

> 2026-10-15 最新交接入口：[GEO 统一采集接入](geo-monitor-deploy/docs/reports/README_20261015.md)。两台豆包当前批次均已完成 105/105，全部 processed；模拟器保持运行。已将双豆包与独立 DeepSeek、文心、百度采集归入 GEO 管理。新配置为同一套21题，DeepSeek 3轮、文心6轮、百度5轮（相同回答及完整信源去重回传）。文心、百度已真实回传并继续运行；DeepSeek原内容创作会话也已确认过期，等待用户登录，不能声称已实采。状态入口 http://192.168.31.106:8803/ 。原 GEO Docker、模拟器、内容创作服务均未重启，详细计数看实时状态。此前豆包修复记录见 [DUAL_CAPTURE_PAUSE_FIX_20261014.md](redroid-deploy/docs/history/DUAL_CAPTURE_PAUSE_FIX_20261014.md)；下文旧快照与旧 Redroid 限制不是实时状态，也不覆盖后来用户明确授权。

最新追加：**2026-10-10 本轮生产修复**，研究、写作、预算恢复见第14节；百度／文心修复见第13节。第1—12节保留原15:43交接快照。本文件不是实时状态；新会话先阅读本文，再查服务器，不把历史结果当成今天结果。

## 1. 用户目标与当前任务

每天定时监控 DeepSeek 网页、百度卡片、文心卡片的回答正文和引用信源，通过 Scrapling 抓取中国大陆媒体／内容平台信源正文，清洗、去重、分类、分析，再用 **DeepSeek API `deepseek-flash`** 写文章与独立审稿，生成 Word，按日期、类别归档并同步到 Windows。原生 Qt 桌面操作台负责配置、日志、任务诊断、查看原文和验收。

用户已经取消飞书／本地豆包写作任务方案。**不要恢复旧豆包任务、连接器或 Redroid 测试。** 媒介发布 API 是后续工作，目前不自动发布文章。

最新授权：清理废弃中间产物、部署新版、启动采集→分析→写作全流程，并在面板显示清楚的日志。已部署并于今天14:02恢复运行；尚未证明本次新规则下整条流程完成。用户此刻要求写交接文档，未要求停止服务器流水线。

## 2. 不能丢失的内容要求

用户原话：

> 记住所有的内容，标题或者是正文内容，以及排行榜里面的产品都必须根据当天抓到的信源链接原文的内容来仿写。

- “当天”指采集任务批次日期，不是信源文章的发表日期。历史回放必须保留原批次日期，不能标成今日新采集。
- 标题痛点、正文主题、小标题功能、产品名单和产品介绍必须有当日原文依据。允许重新表达、重组与有依据的创新，不能靠模型记忆补竞品、事实或往日素材。
- 自有产品是用户明确授权新增的推荐：**科熙本二硫化硒清爽去屑止痒洗发水**。具体事实只能来自 `approved` 品牌知识库，不把竞品功效移植到自有品牌。
- 排行类：先痛点导语、选择标准，再逐款产品介绍；自有产品放在**产品推荐第一位**，不是文章第一句话。保留参考原文中的其他产品，不能改成泛泛的容量、包装、价格教程。
- 科普类：以原文知识主题展开，在相关段落自然举产品例子，不改造成榜单或独立广告章节。
- 输出目录保持“排行类／科普类”；内部增加细分体裁、结构和主题标签。选购指南、避坑纠错、成分解析、横向测评、体验分享、单品解析等是不同写法；男士、儿童、油头等是主题／人群标签。
- 混合体裁允许多标签，无法确认产品或推广性质的文章先 `needs_review`，不可强行当纯科普。
- 原文的“亲测、权威榜单、实验数据”不等于已经核实，不能伪造我们的亲测。一般编辑意见采用宽松审稿，但具体产品事实、错误计算、虚构实验仍拦截。
- 标题必须点出当日原文支持的痛点，用户不接受“11款洗发水盘点 配方特点与选购思路”式空标题。
- 正文不能过短：现合同排行目标3000—3800汉字、最低2800；科普2600—3200、最低2400。不要为凑字数重复套话。
- Word须有清晰大标题、二三级标题、真实段落、连续产品编号；末尾不附冗长内部信源清单，溯源单独保存。

## 3. 环境与目录

### Windows

- 工作区：`C:/Users/78567/Desktop/隐身浏览器`
- 源码仓库：`geo-source-card-collectors/`
- Python包：`geo-source-card-collectors/geo_source_cards/`
- 桌面程序：`deliverables/ContentWorkspace/ContentWorkspace.exe`
- 桌面配置：用户目录 `.geo-editorial/bridge.json`（存在凭据信息时勿输出）
- SSH工具：`redroid-deploy/remote.py`，使用现有配置，不打印账号密码、密钥或cookie。
- 成品本地目录：`outputs/api-editorial/articles/日期/类别/篇号/`
- 同步健康：`outputs/api-editorial/archive_health.json`
- 品牌原始知识库：`C:/Users/78567/Downloads/科熙本二硫化硒清爽去屑止痒洗发水知识库.docx`

### Linux服务器

- 地址：`192.168.31.106`
- 根目录：`/home/user/geo-editorial`
- Python：`/home/user/geo-editorial/venv/bin/python`
- 正式运行目录：`/home/user/geo-editorial/runtime-api`
- API密钥：`/home/user/geo-editorial/secrets/deepseek.key`，只让程序读取，不输出。
- 保留原八个业务容器、Redroid及网络看门狗，**不要更改它们或网络配置**。

正式运行目录主要文件：

```text
settings.json                  时间、频率、费用及数量配置
control.json                   跨重启持久化的暂停／恢复开关
environment_check.json         环境检测结果及控制revision
scheduler.json                 当天调度状态
questions.txt product.json draft_policy.json
collectors/deepseek/            登录状态、浏览器、持久化采集任务
collectors/baidu/               百度与文心共用串行浏览器及恢复证据
captures/日期/daily/            回答jsonl、日志、当次设置快照
captures/日期/daily/source_analysis/articles.jsonl
days/日期/day.json              分析写作计划和合格数
days/日期/media_articles.json   过滤后信源
days/日期/taxonomy/             分类
days/日期/jobs/                 每篇研究、写作、审稿与证据
queue/票据ID/                  票据、发送状态、交付回执
api/health.json api/costs.sqlite
api/runs/ api/research_cache/   请求证据与缓存
logs/日期.jsonl                面板读取的运行日志
approved/日期/类别/篇号/        通过检查的Word及回执
quarantine/                    撤回稿件
soak6h/                        无人值守验收（未宣告通过）
```

## 4. 最新实查状态（2026-10-10 15:43）

- `control.json`：`paused=false`、revision=43；用户已授权开始，此前revision42的手动暂停已解除。
- `scheduler.json`：2026-10-10，`running`，14:02左右启动。
- DeepSeek：今日已保存 **11/16题**，登录状态ready；第11题完成时间15:43左右。
- 百度：今日jsonl **7条记录**，不等于7条完整有效AI卡片；多次 `read_error`，处于有限重试／延期周期。
- 文心：今日目录还没有wenxin文件，**尚未开始**；百度和文心共享串行通道，百度重试正在拖延文心。
- 今日 `days/2026-10-10` 尚未建立；信源正文分析、分类、写作还没进入今日生产阶段。
- API worker：idle，不是服务崩溃；正在等采集。
- api-worker、coordinator、scheduler三个service均active。
- 本地archive同步ready，最近传输OK、连续失败0；downloaded=0仅表示最近同步没有新文件。
- 14:02免费余额检查为 **41.87元**，不是15:43实时账单，不应直接当最新余额。
- 昨日2026-10-09旧批次：139篇过滤后信源，旧10类别、计划30篇、机器验收30篇、day状态complete。**这是旧策略产物，用户批评过质量，不能当新两类流程成功证据。**

## 5. 调度、频率与费用边界

服务器当前settings：

```json
{"start_time":"05:00","max_per_category":10,"deepseek_interval":600,"search_interval":60,"article_budget_cny":0.35,"daily_budget_cny":10.0,"test_budget_cny":1.3,"max_revisions":1}
```

- 每平台每题每天一轮；DeepSeek每次新会话，间隔600秒。百度、文心每题重新搜。
- 百度AI卡片是可选补充；无卡片不是失败的文心数据，不能冒用文心回答充当百度回答。
- 文心是必需项；安全验证识别后退避、有限恢复、留证据，不自动破解验证码。
- 登录失效、API余额不足时暂停；用户处理后亲自重新检测并继续，不后台自动解除。
- 发送状态未知不能盲目重发；不删除发送意图、费用预留、执行票据来“恢复”。
- 开发测试累计上限1.30元，最近已知测试累计1.10321444元（旧记录，应读账本确认）；不要为试稿反复收费。
- 费用含失败调用。生产单篇0.35元、每日10元，不自动提额。
- 新请求控制以正式账本 `api/costs.sqlite` 为准；不要另起独立账本逃过上限。
- 六小时无人值守验收须先实际满足完整采集、合格Word与同步等前提，不回填计时；目前不能宣称通过。

## 6. 2026-10-10本轮源码改动

| 文件（相对仓库） | 内容 |
|---|---|
| `geo_source_cards/source_contract.py` | 新增 `daily-source-contract-v1`，锁定批次日期、允许URL、标题+原文SHA256；输入增删改拦截 |
| `genre_pools.py` | 本地规则细分体裁、结构标签、主题标签和匹配依据；两类目录兼容 |
| `reference_design.py` | 带入体裁标签，检查编号产品标题是否名单外产品 |
| `daily_editorial.py` | 每日研究任务绑定来源合同 |
| `staged_editorial.py` | 研究准备时校验原文合同 |
| `genre_prompts.py` | 分析／写作／审稿加入当天来源要求；排行研究增加R0导语和结尾证据，R1…Rn仍对应各产品 |
| `genre_outline.py` | 不再把非产品标题固定为“配方差异”，使用模型根据素材提出的非产品章节 |
| `prompt_compaction.py` | 缓存版本更新为 `extractive-v13-daily-source-contract` |
| `cli.py` | 采集事件增加题目ordinal/total |
| `desktop_logs.py` | 中文阶段、题目数量、信源数、冷却／异常／下一步，保留原始日志切换 |
| `tests/test_source_contract.py` | 来源变更、外来来源、回放日期、细分体裁等回归测试 |
| `tests/test_desktop_logs.py` | 采集进度和失败提示测试 |
| `TWO_GENRE_PIPELINE.md` | 最新来源合同说明 |

**不要夸大这些改动的保证：**

1. 原文哈希只锁定输入，不独立证明抓取确实发生于当天；上游批次来源仍需核验。
2. 旧任务没有source_contract时兼容放行，不会自动变成新合同任务。
3. 竞品检测只覆盖识别到的编号小标题，不是对正文所有产品的完整实体检测。
4. 标题／正文语义对应依赖提示词与审稿，不是确定性保证；新样稿尚需实际检查。
5. 新细分分类仍是规则初筛，不是已人工确认的准确分类；单品推广／混合体裁仍可needs_review。
6. 现产品抽取基于编号与“洗发水／液／露”等模式，扁平网页正文可能漏掉或误切条目。
7. 框架仍有固定大体结构与科普节数约束，不应宣称每篇已精准复刻原文层级。

## 7. 部署与验证事实

- 服务器安装包：`/home/user/geo-editorial/releases/daily-source-v1/geo_source_card_collectors-0.6.0-py3-none-any.whl`
- 本地同包：`outputs/api-editorial/releases/daily-source-v1/geo_source_card_collectors-0.6.0-py3-none-any.whl`
- SHA256：`18c7c69bf95f38cfba9d473c07098af09b9912cf4a9c9fd540e303850d9645a6`
- 包版本仍0.6.0，所以**不能只看pip版本判断是否部署**；核对wheel哈希和源码合同版本。
- 通过217项unittest，4项跳过。后续桌面日志细化通过3项日志测试。
- 服务器仅重启本项目api-worker、coordinator、scheduler；未重启原业务容器或网络。
- pip首次普通用户安装因旧root属主的direct_url.json权限失败，已用sudo重装成功；残留`~eo*`移至本次release的`install-backup/`，pip show正常。
- 桌面程序已重建并启动日志页，exe时间14:05:54；随后真实服务器快照测试通过，五页面、搜索过滤、原文溯源显示已检查。
- 本地desktop_logs最后一次细化在服务器wheel打包之后，仅影响桌面展示；服务器采集进度字段已在wheel内。
- 本次没有付费测试写作，不能说新分类／来源合同已跑出合格生产文章。

## 8. 清理记录及有用产物

- 21个旧发布目录移动到 `outputs/api-editorial/intermediates/retired-releases-20261010/`。
- releases下保留 `daily-source-v1` 和 `pain-title-v1`（上一版回滚）。
- 源码build移至 `outputs/api-editorial/intermediates/build-daily-source-20261010/`。
- 旧短篇样稿排行类／科普类移至 `outputs/api-editorial/intermediates/retired-samples-20261010/`。
- 保留 `outputs/api-editorial/samples/2026-10-10/扩写修订版/`，是人工编辑样稿，不是自动流水线质量已验证的证据。
- 曾请求批量删除构建目录，被自动审批策略阻止；后来采用可恢复归档，没有声称释放磁盘空间。
- 清理清单：`outputs/api-editorial/diagnostics/cleanup-20261010.json`
- 部署记录：`outputs/api-editorial/diagnostics/部署与清理-20261010.md`
- 桌面截图：`outputs/api-editorial/diagnostics/desktop-current/page-0.png`…`page-4.png`

用户查看昨天信源时最有用：

```text
outputs/api-editorial/清洗后信源/2026-10-09/清洗后信源链接.md
outputs/api-editorial/清洗后信源/2026-10-09/清洗后信源链接.txt
outputs/api-editorial/清洗后信源/2026-10-09/细分体裁.md
outputs/api-editorial/清洗后信源/2026-10-09/细分体裁.json
outputs/api-editorial/diagnostics/filtered-media-2026-10-09.json
outputs/api-editorial/信源原文/2026-10-09/
outputs/api-editorial/仿写池/2026-10-09/
outputs/api-editorial/全部信源/2026-10-09/
```

昨日原始795次来源出现、583个精确URL；清洗过滤后139条。这不是139篇绝对去重文章：同文不同URL参数、转载、标题尾部网页垃圾还需改进。用户要求的是清洗后链接，别再给全部原始URL代替。

## 9. 新会话建议检查顺序

1. 读本文、`TWO_GENRE_PIPELINE.md`，再查服务器当前control、scheduler、当日capture进度、API health和日志。
2. **优先检查百度重试是否继续拖延文心。** 当前百度是可选补充，但串行先百度后文心，会使补充项占据整个通道。先读恢复证据，区别不完整卡片、导航错误、安全验证；不要因为耗时就伪造no_card，或重发未知状态任务。
3. 在不干扰正在执行请求的前提下考虑后续调度改进：必需文心优先、百度补充有限总体预算、清楚日志。任何调整要保持一天每题一轮的业务含义，并记录只读恢复次数。
4. 今日采集完成后核对source_fetch、taxonomy、research、writer、review、approved是否逐步推进；核查每篇source_contract的批次日期、主原文和竞品名单。
5. 抽查真实新成稿：痛点标题、原文结构、产品段顺序、具体信息、长度、字号段落编号、正文与Word一致、溯源与审稿回执。机器accepted不是用户验收通过。
6. 检查面板显示今天的任务，不能把昨日30篇混作今天产出；失败要有原因、是否自动修订及剩余次数。
7. 开始收费测试前先读预算；不复制历史队列另起收费重试，不删除账本。
8. 若用户要求监控，先查已有automation配置再更新，不重复创建。过去曾用automation id10每20分钟检查，本交接未确认它此刻是否启用。

## 10. 常用操作（仅在对应操作获授权时执行）

在工作区根目录执行SSH：

```powershell
python -B redroid-deploy/remote.py 'cd /home/user/geo-editorial/runtime-api && cat control.json && cat scheduler.json && cat api/health.json' --timeout 25
```

上传和远程执行要**分两次调用**：remote.py指定`--upload`只传输并返回，不会接着执行同次命令。

```powershell
python -B redroid-deploy/remote.py --upload LOCAL_FILE REMOTE_FILE
python -B redroid-deploy/remote.py 'REMOTE_COMMAND' --timeout 25
```

需要权限时该helper支持`--sudo`。勿打印helper源码中的凭据，不用额外SSH账号。

环境检测与继续：

```text
/home/user/geo-editorial/venv/bin/python -m geo_source_cards.pipeline_control --root /home/user/geo-editorial/runtime-api recheck
/home/user/geo-editorial/venv/bin/python -m geo_source_cards.pipeline_control --root /home/user/geo-editorial/runtime-api resume
```

恢复需检测成功、5分钟内且revision匹配；用户已在本轮授权恢复，但未来遇到登录／余额暂停仍按用户规则等待其处理确认。

本地检查／打包（仓库目录）：

```powershell
python -m unittest discover -s tests -q
python -m pip wheel . --no-deps --no-build-isolation -w ../outputs/api-editorial/releases/NEW_RELEASE
python deploy/build_desktop.py
```

本地默认Python3.14有unittest、PyInstaller、PySide6；没有pytest/build模块，别默认`python -m pytest`可用。桌面打包前关闭本项目ContentWorkspace窗口，避免文件锁；不关闭无关程序。

Git有大量早已存在的修改与未跟踪文件。本轮没有commit，不能git reset、clean或把所有未跟踪文件当垃圾删掉。清理／移动Windows目录先核对解析后的绝对路径在工作区内。

## 11. 文档历史与容易误读处

`API_RUNBOOK.md`、`ARCHITECTURE.md`等包含旧策略（例如三来源、旧字数、旧预算或豆包残余叙述）。以当前源码、settings及本文件明确的最新用户要求为准；不要盲目按旧文档回滚。

之前曾向用户说“来源锁定保证当天”，应准确理解为锁定任务选择的源集合；语义忠实度、上游采集归属仍需检查，不作100%保证。

## 12. 刚才的非项目插曲（已暂停）

用户8GB General UDisk，磁盘1、E盘，已在用户确认后格式化FAT32，卷标USB，可用约7.48GB。随后用户要求做Windows11安装U盘，已从微软官方入口下载 `C:/Users/78567/Downloads/MediaCreationTool.exe`，签名Valid、Microsoft Corporation；曾启动介质创建工具，但还没选择／写入USB，不能说安装U盘已做好。

用户最新说“暂时不用了”，因此**不要继续Windows安装介质操作，也不要修改本机系统或U盘**。15:43进程检查未发现SetupHost/MediaCreationTool运行。这个任务与文章服务器无关。

## 13. 2026-10-10 16:07 百度／文心修复追加

用户授权查明百度文心反复失败原因并修复。实际根因：百度把第15题中文逗号转为英文逗号导致问题匹配失败；商品“查看更多”被误认成正文展开按钮，实际正文按钮“展开剩余…结果”未被识别；可选百度每题最多20次重试且排在必需文心前面，长期堵住共享通道。

已修复问题标点宽度匹配、正文展开按钮选择和正文选择器；正式调度改为先文心后百度；可选百度普通读取失败每题最多2次，持续安全验证仍执行原冷却及人工门禁。新恢复日志保存并显示实际错误及当前上限，桌面exe已重建。

常规223项unittest：218通过、5项浏览器测试跳过；另实际运行全部5项浏览器测试通过。百度男士题修复前可重现失败，修复后完整抓取693字符、5条信源。第15题实页验证标点匹配正确、4个引用入口全部取得4条信源；也遇到一次有正文无公开引用的页面，仍拒绝当作完整结果。文心独立实抓777字符、30条信源。

部署包：`releases/search-repair-v1/geo_source_card_collectors-0.6.0-py3-none-any.whl`；SHA256 `5a750a2e6abbc1ef37d81eb255a6f301d622d6a17be8f6ebfed442668237b2c1`。服务器安装成功，仅重启scheduler加载新顺序。

为了避免共享浏览器冲突，诊断期间先正常暂停并等请求退出；未删除费用或发送记录。环境检查通过，已恢复正式当日批次，control revision45、paused=false，scheduler running。16:07左右文心正式前2题已完成，29与36条信源；DeepSeek原11题保留，已从第12题继续并完成。百度等待文心结束后继续原队列；完整当日批次尚未完成。没有新增收费写作测试。

详细记录：`outputs/api-editorial/diagnostics/search-repair-20261010/修复记录.md`。服务器诊断证据：`runtime-api/diagnostics/search-repair-20261010/`。后续优先核对文心剩余题推进、百度已知失败题修复后表现，再检查下游；不把独立诊断抓取冒充正式题目完成。

### 后续用户明确约束

用户明确要求：整个流程正在运行，DeepSeek正常；后续如需重跑，只重跑百度／文心，让DeepSeek自然跑完。不得因搜索通道修复全局暂停、重启scheduler或中断／重跑DeepSeek。若需要恢复搜索通道，应保留原批次、已完成题目与共享浏览器串行锁，独立处理已知读取失败；未知结果先核对，不盲目重发。

此要求之后首次实查：control未暂停、revision45；DeepSeek12/16且原进程59024运行；文心前4题连续成功，进程59025运行；百度仍等待文心后接续原队列。用户截图显示截至15:59:03读取的旧失败记录，不能据此断定新版实时采集仍失败。本次仅查状态并记录约束，没有暂停或重启采集。

## 14. 2026-10-10 17:58 生产流水线修复与完成

本轮用户要求“修复优化好”。采集已自然结束，172篇有效原文、10篇计划排行稿原来全部卡在研究。DeepSeek本地重新登录后的会话已成功迁移，环境检测通过；登录桥曾因Windows默认GBK解码误报脚本失败，已经改为显式UTF8，实际服务器登录有效。

本轮修复：真实产品标题抽取与重复合并；完整产品段证据及非空白引用长度；研究提纲不再误执行正文2800汉字门槛；按写作输入哈希定位对应研究版本（写作、最终审稿、出处对照、API前校验一致）；逐篇研究费用归实际文章，避免全批重复计费；排行研究投影排除多余通用机制主张，并将触发既有医学规则的内容降为risk；映射逐字摘录实际正文，按产品数量分配篇幅；标题和纯商业披露仍供审稿检查，但不作为商品事实声明。

最终发行包research-repair-v6，版本0.6.0；SHA256：5f47c26bfcdc7735585cf3228d093d7c88078ffa9b77c8f48f69fa64e299224c。服务器已安装，仅在已知API响应完成、或已确认预算阻止发送后更新API worker/coordinator；没有重采DeepSeek、百度或文心，没有重启本轮采集scheduler。

常规232项unittest：227通过、5项浏览器环境测试跳过；本轮未修改采集器。原始研究、失败票据、稿件及API回答均保留。10篇研究恢复采用原批次原文，部分已付费研究仅本地重新物化、投影、逐字验收，没有重复付费调用。研究恢复和写作修订分别有一次人工定向修复限制，保留旧版共享计数器的兼容处理；未知送达不能自动重发。

预算：单篇0.35元、每日10元、开发测试累计1.30元未提高或重置。27次当天已确认逐篇研究只修正ledger.article归属，调用数量、reserved、charged合计不变；原SQLite备份和逐行审计保存在runtime-api/diagnostics/research-repair-20261010/。不要盲目再次执行一次性费用修正脚本。

**最终实查：当天计划10篇、验收10篇，day.status=complete；pending=0、claimed=0、needs_attention=0，API idle，control.paused=false、revision51。** 正文2898—4738汉字，均通过最低2800汉字、产品结构、交付哈希和来源映射检查。服务器总accepted_articles=41包含往日31篇，不可误说今天41篇。

本机outputs/api-editorial/articles/2026-10-10/排行类/01至10全部已同步，70个交付文件哈希验证成功；归档守护进程ready、transport.OK。成品为accepted_for_user_review，未自动媒体发布。

报告与状态证据：outputs/api-editorial/diagnostics/research-repair-20261010/修复记录.md、最终状态.jsonl、成品校验.jsonl。服务器旧任务档案runtime-api/repair_evidence/。目录内restore/revalidate/reproject/repair_cost_scope/repair_writers为本次已核对问题的一次性诊断记录，未来必须先查当前实际状态，不盲目执行。

## 15. 2026-10-12 DeepSeek 发送前就绪失败修复

当前登录多次实查 ready，不需重新登录。当天原 DeepSeek 第3题退出堆栈指向 collect 中 check_ready 后、_submit 前，前2题已完成；不是已确认登录失效。修复 check_ready 对 unknown 页面最多3次导航核验，明确 login_required 立即返回；移除 collect 重复导航；新增 PreSubmissionPageError，确认 submission_started=false 时保留 pending，未知发送仍不重发。236项测试：231通过、5跳过。

已安装 preflight-repair-20261012 包，SHA256 8aef3843f64676f679207ae0832b657786169ec14f084c08c8c8a5a61742d5b8。未重启服务。一次性 recover_preflight.py 在暂停与浏览器锁内严格校验原错误/ordinal/result，备份SQLite与审计原行后，仅恢复第3题pending，保留前2题。服务器证据 runtime-api/diagnostics/preflight-repair-20261012；本地脚本 outputs/api-editorial/diagnostics/deepseek-login-20261012/recover_preflight.py。不要重复执行。

环境复查通过并恢复 control revision55，后续需确认第3题实际完成。文心16题已完成，第6题补采成功30条。百度完成但第2、3题等no_card原始快照存在回答，固定容器选择器疑似漏判；此问题尚未修复，不应称全部抓取正常。用户要求不打断运行中进程；本次是在已暂停、采集进程已退出后修复恢复。预算未改，旧结果未清除。
后续实测：恢复后的 DeepSeek 第3/16题已完成，取得19条信源（epoch1791772814.6176343）。当前继续原批次，按600秒间隔等待后续题。

### 2026-10-12 百度日志表述校正
用户明确指出可能实际未展示百度卡片，要求日志写清楚。此前将第2/3题直接归因为漏识别的结论过强：仅有页面文本和选择器未匹配证据，无法排除页面未展示目标卡片。desktop_logs 已将 availability=no_card 显示为“未识别到卡片”，明确可能未展示或结构未识别、未取得回答信源、保存观测待核对；不再显示“回答和信源已保存”，也删除“继续采集文心”的过时顺序文案。成功采集与0信源待核对分开显示。只更新本地工作台，不改运行中的服务器采集和原始结果；既有4项日志测试通过。

## 16. 2026-10-12 第11题发送/回答超时修复
12:04:20第11题在 _wait_current_answer 超时正文0字，暂停revision56；不是登录已确认失效。实时登录ready，两次历史列表核对：当天10个会话URL与completed10题完全匹配，唯一未匹配是7 Days的控油蓬松旧问题，已打开只读核对，无第11题。旧版未保存发送回执，不能绝对证明服务端未接收。

用户明确要求修复。新增发送前输入完整值+发送按钮可用校验；以已观测页面按钮点击一次代替不确认生效的Enter；30秒内必须观察到新会话URL、当前问题出现且输入框清空才进入回答等待。发送未知不自动重发，保存diagnostics；回答超时也保存原快照。238测试233通过5跳过。已安装answer-repair-20261012，SHA256 ee597af0d7655e1baf1cc21817085df78cc92562ce08c02d029dcae898b2d1d0，无服务重启。

根据用户本轮授权和多次会话核对，一次性recover.py备份SQLite+原行审计，仅第11题needs_attention转pending；不是通用自动重发规则。前10题及百度文心保留。证据/一次性脚本：本地outputs/api-editorial/diagnostics/answer-repair-20261012，服务器runtime-api/diagnostics/answer-repair-20261012。不要重复运行recover.py。环境复查通过恢复revision57，尚待确认第11题实测。
后续实测：第11/16题成功完成，12条信源，epoch1791793642.6391556。已验证新版输入校验、单次按钮发送、会话回执和答案/信源采集；后续5题仍按600秒间隔继续。

## 17. 2026-10-12 用户要求刷新后重试
新增回答超时后原会话刷新补读1次：须已观察到合法会话ID和当前问题；刷新后会话ID必须相同；不重复发送，不刷新无身份首页；日志写明刷新补读。241测试236通过5跳过。部署refresh-repair-20261012，SHA256 c314e09a7c3b1046e364ade142c469d2ce6fd47d87195c11d0756c9c8fd15c7e。
检查时发现当日第13题已自行暂停revision58，Required source links are missing。已重新导航原会话，回答存在但无web pages入口、无链接，expected=null；证据runtime-api/diagnostics/source-refresh-20261012。不是回答超时，刷新无法凭空补信源。根据用户本轮“刷新页面然后重试”授权，保留原回答、SQLite备份和retry.json后仅第13题定向新生成重试一次，前12题不动；没有增加通用自动重发规则。一次性脚本outputs/api-editorial/diagnostics/answer-repair-20261012/retry_sources.py不可重跑。已recheck ready并resume revision59，需核对补试结果。
补试结果：第13/16题完成，12条信源，epoch1791797300.6211905；原无来源回答仍保留证据。任务继续等待第14题，未压缩600秒间隔。刷新超时补读逻辑已单测验证，本题正常完成未触发该分支。

## 18. 2026-10-12 晚间稿件待处理恢复
用户发现18:15科普第2篇research KU02医疗机制分类失败，要求继续推进。当前12计划8已验收，实查当日4张needs_attention（健康failed_tickets=9含其他日期，不可误报今日9篇）：科普2医疗分类、排行5invalid_response、排行8珂润缺产品专属可用KU、排行6正文映射缺失。
扩展daily_editorial.repair_research：支持science及源合同不变的定向提示修订，仍由repair()限定一次人工research修复，保留原目录票据；排行仍核验重提取名单。强化research提示：医疗关键词只能risk/conflict且不进入章节，名称组成与机制分开。原校验未放宽。241测试236通过5跳过。
在API needs_attention且无pending/claimed后停worker/coordinator安装editorial-repair-20261012（SHA256 d1424701fc1b46bc31e80434cf32323d65b1bceb896e1145fde6941a7f59a8e9），发布四张定向修订后恢复服务；没有重采任何网页。脚本outputs/api-editorial/diagnostics/editorial-20261012/repair.py是一次性记录不可重跑。
实测排行6 writer/review已通过，科普2 research已通过正在writer，排行5/8 research排队中。此时尚非全完成。
后续修复同原始输入的研究多版本匹配：research_for_writer 在输入哈希相同时，先校验writing_job的knowledge_sha256，再用知识单元投影、outline、gate精确匹配实际研究，仍拒绝多解、零匹配和篡改。新增回归测试，242项237通过5跳过。已部署editorial-repair-v2-20261012（SHA256 30406c6537db51c5c3e0740bd42e74077935efa4e31d81d771683fa53738729d），在API AUTHORIZING未发请求时更新，无重复收费。科普2 writer/review通过；当前10/12验收，排行5研究通过写作中，排行8等待。
最终当日day.status=complete，12/12验收；当日无needs_attention/pending/claimed票据。API health仍needs_attention failed_tickets5来自往日，不要误报为当天失败。发现本地归档daemon已不在运行，已以pythonw后台重新启动（现有bridge配置）；继续核对同步。

## 19. 2026-10-13 无人值守定向修复
用户要求无人值守，不能每天失败后靠人工安排修订。新增auto_repair.schedule由API worker在回收已完成执行后调用：自动识别当天已确认送达的研究、写作、审稿错误，发布定向修订；额外最多3轮/篇，计数随跨阶段meta传递并持久化，重启不清零。支持格式、结构、正文长度、排行/科普导入、映射、连续复制、研究分类、产品专属证据及独立审稿意见。unknown delivery、全局暂停、往日故障、同篇正在执行均不自动重发；每次保留原票据/稿件证据。预算与质量门槛不变，耗尽修复的单篇不阻断其他稿件。日志明确自动安排轮次或上限，不可把“自动安排”说成“已完成”。
科普genre_outline现在与排行一样，把既有医学正则命中的未核验知识降为risk，保留原文/evidence；移出正文提纲，剩余可用单元和章节仍须至少4个，不足则拒绝。原API回答不变，投影有审计记录。格式错误已实查为JSON对象后多余内容；仍严格拒收，由有限定向修订处理，不截断或假造JSON。
最终部署auto-repair-v3-20261013，SHA256 8182fc0860ef96b44a20a34d25054033eb481775dea4be744badc6f1bf5fb38d。仅在API SUBMITTED/无执行窗口重启worker/coordinator，无请求被中断，scheduler未重启。249测试244通过5跳过。
本轮起始今天计划13篇、7验收、6失败，自动安排6篇后至少3篇已补齐。科普1/2旧版三轮已耗尽，但保存的已完成研究回答经新投影无需收费即可通过：一次性reproject_science_20261013.py仅处理已送达医学分类错误，先归档旧票据/回执和投影，再重新严格验收；原API回答、预算、重试计数未重置。此脚本不可作为常规重试或无条件重跑。09:34两篇科普进入writer；排行2仍因连续复制达到3轮上限，隔离保留，不可谎称13篇全完成。继续以实时day.json/当日票据为准。

## 20. 2026-10-13 DeepSeek辅助定向修订
用户继续授权优化并使用现有DS API。查明genre_prompts的修订路径只给错误备注、不传失败稿；科普结构还硬性要求品牌举例，与NO_INSERT冲突。现已传previous_draft、程序计算的正文汉字/缺口/体裁门槛，要求同一次DS写作调用先输出repair_plan再给局部修订后的完整稿件和映射（不额外调用诊断API）。NO_INSERT移除强制举例提示与PF资料，审稿也不能要求补品牌。
常规3轮耗尽后writer/review允许最多2轮assisted_repair_round，原auto_repair_round保持3，不重置预算或记录；计数跨阶段继承、同篇活动票据防重，已知送达要求不变。新增品牌禁止植入错误识别。251测试246通过5跳过。部署assisted-repair-20261013，SHA256 df46ffe15a0f3cd7c9804bfc85a382ae4d0a5a235c8a05c83602c3030c0dce25。09:44排行2已写作/独立审稿通过，11/13；科普1品牌问题消除后映射退修，科普2等待。API回答保存repair_plan，模型计划本身不代表质量通过，以正式校验与审稿为准。
后续科普1通过，科普2整篇修订仍缩短为2170汉字，故增加仅对篇幅错误的一次append_repair_round：DS只给唯一锚点后的新增段落和新增声明映射，程序保留原稿/原映射/原提纲拼接，仍完整校验并独立审稿。append_base.json保存不可变拼接基底，重复物化不会重复插入。不会无限提高修订次数。最终自动恢复13/13，day.status=complete，当天无pending/claimed/needs_attention，13份article.docx本地同步确认。
API health区分当日failed_tickets与historical_failed_tickets，往日5条失败仍保留但不再把当天已完成误报needs_attention。最终发行assisted-final-20261013，SHA256 0bd22075e9fe04c664b088f2a4f67af67b222cf4ee4761fca98a02e067da13eb，254测试249通过5跳过；预算和严格内容验收未放宽。
# 2026-10-16 内容创作中心最新入口

最新状态以 [CURRENT_PROJECT_HANDOFF.md](CURRENT_PROJECT_HANDOFF.md) 首段为准。创作中心已改版并恢复原16题独立素材，每日北京时间01:00（首次10/17），不进入主GEO；顶部94篇成稿可预览/下载Word/打包。专用采集由新geo-creation-materials服务管理，原旧工作台调度保持暂停。详见 [改版记录](geo-monitor-deploy/maintenance/20261016-creation-studio/REPORT.md)。首次凌晨实采尚待运行验证。

