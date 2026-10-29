2026-10-19 13:37 heartbeat: Baidu TODAY collection ended complete_with_unavailable. 105/105 observations with actual receipts =92 full-source +13 body_only (not 105 full-source); no pending delivery. PG verified21 questions each5. Wenxin TODAY automatically started original daily batch geo-panel-wenxin-card-20261019-131934-a7ec85f4 and already10/168 processed, no pending receipts. New handoff notification sent; do not repeat unchanged completion. Browser DeepSeek ready 7/63 with7 matching receipt pairs, next permit13:39:49.401 Beijing. Both Doubao today complete105 each. No manual mutation or new duplicate batch. Audit geo-monitor-deploy/maintenance/20261019-heartbeat/check-1336.json.

2026-10-19 13:17 heartbeat: BOTH Doubao lanes TODAY are complete, 105/105 each, 210 total. True PG task-date counts verified 21 distinct questions, min=max=5 for each, no pending receipts. Doubao2 completion is new; user notified. Do not rerun authorized ordinal13 recovery script or create additional Doubao batches. Browser DeepSeek ready, captured/processed 6/63 with six identical local/upstream receipt pairs; next permit 13:17:40.09 Beijing. Baidu104/105, Wenxin today waiting_for_baidu, do not launch prematurely. Old Yuanbao October18 completion is not a new October19 task completion. No mutation. Audit geo-monitor-deploy/maintenance/20261019-heartbeat/check-1316.json.

2026-10-19 12:17 heartbeat: browser DeepSeek ready, captured/processed 4/63, four receipt pairs equal, next permit 12:27:44 Beijing. Doubao2 today 48/105 continues. Baidu 79/105; formerly blocked exact toner task 5fd2ddf1508bea09debb8cd88d1a7f495b60597d85a79eb5dad346b66aec86f3 now completed as body_only (534 chars, 0 sources, source_capture_complete=false), not full provenance success. Recovery status ready. Wenxin today still waiting_for_baidu. Recovery notification sent, do not repeat unchanged; do not claim missing references resolved. Audit: geo-monitor-deploy/maintenance/20261019-heartbeat/check-1216.json. No mutations.

# 豆包今日任务核对与单题授权恢复

11:35收尾：豆包2授权重试第13题已于11:34:35完成，正文470字、11条信源，真实processed回执确认13/105，无待回传，worker已准备第14题。新增attempt1仅有一次send_click_intent_committed/send_tap_returned；原attempt0记录保留。准备恢复期间uiautomator出现RemoteDisconnected，自动重连和有限准备退避后恢复；不能把App当前页面正常误说成整个先前准备过程没有异常。原请求最初未确认的根因仍不能仅凭点击日志确定。新增受控preparation_failed日志已部署，仅重启豆包2；既有准备/发送只点击一次规则保持。

用户要求昨天未完成不再补作今天目标，今天任务须跑完。实际查明豆包1今天原批次geo-panel-doubao1-20261019-090810-41d5da92的105条为21题各5轮、09:08:30–11:08:26实际发送，已回执入库105。另1条来自10月18日批次，旧database_counts仅按入库run.day统计，将它混入今天任务进度（106）。不能将这一条历史回传当作今天目标完成；也不能把105条今天真实采集说成昨天补采。

daily_tasks.database_counts现在按来源和批次分组，豆包1/2再核对明确daily_date（旧批次回退服务器批次日期）；昨天回传不抵扣今天任务，历史数据仍保留，未改monitor_runs或删除记录。其他模型计数暂保持原语义，不在本次擅自改DeepSeek跨日任务。4项新增日期归属测试、44既有控制/每日回归通过，源码包117/117一致。备份服务器 /opt/monitor/geo-capture/maintenance/20261019-task-date/daily_tasks.before.py。

豆包2今天批次geo-panel-doubao2-20261019-090003-88e4f45b此前12/105，13题“推荐一款防脱精华液”点击已记录但无确认。用户本轮明确回复“允许本题重新发送一次，继续跑完今天任务”。仅该题归档旧尝试至failed_attempts、capture_retries从0变1，保持纯问题原文和同一task_id、同一批次；新增operator_interrupted_send_recovery_scheduled作为授权边界。旧baseline未改，后续新baseline使用attempt1；不清队列、不批量重问。完整SQLite备份 before-user-authorized-retry-1792380378.sqlite。

一次性恢复脚本deepseek-browser-deploy/retry_doubao2_authorized_once.py只作审计，不可重跑（已设原状态/attempt0/无授权事件断言）。先暂停daily actor避免抢占，只停止豆包2worker，锁定设备并复核原请求仍absent后事务更新，再启动原worker和daily actor。重试一度处于preparing/preparation_backoff，正在检查App新对话准备故障，未据此声称第13题或今天任务已完成。


**2026-10-19 11:09 巡检：** DeepSeek浏览器ready、running，真实捕获/入库2/63，两条冻结outbox与真实回执一致，第二问约11:07发送，下一许可11:33:35，无待回传。豆包1本批105/105已完成（今日PG106含额外历史回传，不覆盖原目标）；百度62/105、元宝今日134/168继续推进，文心今日waiting_for_baidu。豆包2仍12/105、原第13题awaiting_original_result，属于同一已通知异常，即使外层status显示running也不能当已恢复；不重复告警、不重问。未改任务/配置或重启。核查证据geo-monitor-deploy/maintenance/20261019-heartbeat/check-1109.json；本轮仅通知豆包1新完成。

# 2026-10-19 10:52 北京时间巡检

DeepSeek浏览器登录ready、状态新鲜、插件running/cursor1，inFlight第二题preparing；当前捕获1/入库1/目标63。冻结outbox与本地、上游真实processed回执相同，下一发送许可11:07:24，属于正常间隔，不发起额外问题或重启。

服务器每日09:00配置、daily actor及浏览器/receiver/bridge均active，按用户保存当天配置运行；未把daily_plan旧默认轮数覆盖当天105次豆包计划。检查时真实PG豆包1=88、豆包2=12、百度58、元宝116、浏览器DeepSeek1；元宝当前原批次是10月18日的续采，今日PG单独计数。文心今日waiting_for_baidu正常，面板current.complete来自昨天历史批次，不是今天文心完成。旧DeepSeek模拟器waiting_login已知，不通知为浏览器掉线。

新发现持续故障：豆包2今天批次geo-panel-doubao2-20261019-090003-88e4f45b停在第13题“推荐一款防脱精华液”，09:12:39记录send_click_intent_committed，09:12:42记录send_tap_returned；至10:52约100分钟仍未找到可绑定的原请求，reader.lookup=absent。发送后数据库14条新增记录均非本题已确认用户请求（可见的是历史补同步）；只读UI当前只显示本题文字。不能凭“没找到请求/界面有文字”证明点击绝对未提交；按用户明确不重发未知题要求，保留prepared、原baseline和30秒补读，不清队列、不重复点击，不伪造完成。现有worker存活但running_recovery没有实际推进，应告知用户该通道异常，不能宣称全部正常。

只读诊断脚本check_doubao2_original.py、check_doubao2_ui.py在deepseek-browser-deploy，服务器临时同名geo-check前缀；不打印登录凭据、不注入UI文字。未改生产代码、任务、配置、暂停、原生数据库或重复建批次。本次已通知豆包2持续无进展；后续若状态不变不重复提醒，恢复推进或新变化再通知。


**2026-10-19 10:48 DeepSeek浏览器正式执行、每20分钟巡检已启用：** 用户登录并授权按原配置启动。唯一可用deepseek2切换browser_extension，21题×3轮、随机20–30分钟、思考关/智能搜索开；主09:00及创作01:00不变。批次geo-panel-deepseek2-20261019-103338-38eaf48a，插件run be23d600-e3c2-49fa-ba7b-acb1a3f2f6ca，当前1/63已真实入库（1051字、12/12信源、未隔离、stored_run_id d387b3a97920ae8dabdc），下一许可约11:07:24。首条回执适配曾错读save.run_id导致bridge重启，已改stored_run_id并复测，无重复提问；冻结outbox/真实processed回执一致。browser/receiver已enable，登录两次重开仍ready；不保证长期不掉线。现有内网/公网 login/deepseek2/ui/state/frame已代理浏览器且均200，CSRF/认证保留，本地18820仍可用。44控制器/每日+2桥接+6认证/输入隔离验证，源码117/117一致。geo-2 automation ACTIVE每20分钟，只在新异常/完成时通知，正常静默、不重建批次、不恢复用户暂停/旧Android；实际读取browser state/plugin_job.inFlight/permit/data/outbox/receipts。其他模型未改配置/批次，PG当时豆包1=86、豆包2=12、百度58、元宝113，文心waiting_for_baidu正常。63次可能跨日，先续原任务，不能凭20分钟内无新增误判卡住。详细deepseek-browser-deploy/REPORT.md；activate_production.py/install_test.py不可重跑。下条待登录试验记录已过时。


**2026-10-19 10:22 DeepSeek插件无头独立测试已就绪，等待用户手动登录：** 私有仓库about-felicity/deepseek-chrome-monitor commit6ec0a88，references原样/project独立适配。服务器/opt/monitor/geo-deepseek-browser-test，Chromium153真实headless+MV3加载成功；UI通过WindowsSSH隧道PID19360 http://127.0.0.1:18820/ 已打开，真实frame是DeepSeek手机号/验证码/微信扫码。测试服务browser-test/receiver active未启用每日，未改变正式DeepSeek模拟器/backend/队列或其他模型。测试20–30min/默认daily false/rounds1，send_intent先保存、未知不重发、思考关/搜索开门禁；主GEO每题3轮仍保留。接收器7测试、72项HTML+门禁通过，真实问答与主回传尚未验证，测试零发送。用户反馈不能直打/高延迟，login.html已热更新键盘/IME/粘贴、输入排队不丢、未知不重放、ACK即取帧；真实frame129–170ms，隔离输入QA全过，不重启远端页面。请用户刷新控制页。等用户登录后，先核无风险/模式，刷新远端聊天页加载后修core（域名误认标题bug已修），尊重已存slot（一开始真限速自测占用了nextAllowedSendAt）做单题1轮验证再接正式调度；不得直接启用上游6min/42次/24h循环。详细deepseek-browser-deploy/REPORT.md，服务限内存1.2GB+128MB、独立profile和localdata，不输出凭据。

**2026-10-19 09:12 用户授权修复非DeepSeek采集，已恢复真实入库：** 豆包1旧68题原生正文完整360字/商品卡/无网页信源，被worker/Queue/envelope零信源硬门禁误判未完成；新增question-only严格原生status21/全部EOF/raw正文一致/无搜索或citation/source_availability=not_provided证明才允许来源0，保留商品raw，两次完整快照仍必需。元宝App无进程，先reader基线pidof后ready启动的顺序死循环；改基线前ensure_open+app_wait20s。28回归通过、102/102映射匹配。元宝连续恢复3条真实入库、下一题生成；豆包1今日新批geo-panel-doubao1-20261019-090810-41d5da92已3条、下一题生成，豆包2=11、百度=9，文心waiting_for_baidu。豆包旧68题固定binding只读补回receipt，单次点击不变，旧批68完成但原105未跑满，不能伪称昨日完成；该补读10/19入库。部署安全排空时跨日actor新建今批，旧service曾设备锁失败（无发送）现已stop且今日锁唯一，不要启动旧service争锁。DeepSeek未动，09:00/01:00及其他设置不改。备份maintenance/20261019-native-recovery/backup-1792372087，报告同目录REPORT.md/validation.json；deploy/recover_bound硬编码一次性脚本不可重复日常使用。

**2026-10-19 05:18 heartbeat只读发现新持续阻塞，已通知：** 实际主GEO09:00，timer next10/19 09:00、last10/18 09:00；当前05:18未到期，当日无daily row/status正常。daily/status/auth timer active。昨天真实PG回执：豆包1=67/105（第68题prepared，send_click_intent+send_tap_returned已提交，awaiting_original_result自10/18上午，active/running_recovery无新增），豆包2=105/105，百度105/105，文心168/168，元宝0/168（168pending、首题prepare_failed/CalledProcessError连续重试，最新events2568，active/preparation_backoff，无发送证据）。两项持续无进展属于新需处理异常，底层原因尚未确定，不伪称登录或网络。DS1原risk_blocked、DS2原login_required incident_id/changed_at不变，不重复告警。只读检查PG/任务SQLite/journal，不清队列、不重发未知题、不重启或改配置。原始检查工具本地maintenance/20261017-deepseek-interval/heartbeat_20261019.py及heartbeat_events_20261019.py，运行于服务器/tmp同名。

**2026-10-18 05:17 heartbeat只读核查：** 主GEO实际09:00（非旧heartbeat所写05:00），timer next=10/18 09:00，北京05:17尚未到期，无当天daily row/status正常未启动，不建批不改暂停。daily-control/status/auth timer active。发现第二路DeepSeek新变化：auth-monitor changed_at=10/17 19:34:36，login_required（不是已证禁言），服务exit77，原分组4/18完成、日合计真实PG回执19/63剩44，无pending_delivery/needs_review。用户需第二路scrcpy重新登录，通知入口/geo_monitor/api/geo-capture/login/deepseek2/ui；第一路原risk_blocked不重复报。10/17其他真实入库豆包1/2=105/105、文心168/168、百度105/105、元宝168/168，均完成。未操作生产队列/服务/账号。

**2026-10-17 17:55 主GEO每日时间已改09:00（北京时间）：** 用户要求所有主监测模型含DeepSeek两路统一每天09:00；经schedule_control.save持久保存revision2并更新systemd 30-schedule.conf，next_run=2026-10-18T09:00:00+08:00。内容创作独立采集01:00配置逐字节未变，两个creation服务active。各模型settings/current_batch逐项比较不变，未改轮数/问题/20–30分钟间隔/暂停。百度完成后文心启动顺序保留。timer restart触发了一次当天幂等dispatch并成功结束，无需再手动启动批次。生产备份maintenance/20261017-daily-0900-1792230920含before/verified，脚本本地maintenance/20261017-deepseek-interval/set_daily_0900.py仅本次操作不可重复。此前交接的05:00均为旧设置，不可据此改回。

**2026-10-17 17:54 DeepSeek两路已改随机20–30分钟：** 今日daily与settings默认1200，面板1200–1800；旧批次兼容但future send下限1200。59测试通过，100/100映射匹配。第二路新登录ready、15/63剩余48，安全排空后daily按入库剩余分组续接，当前批geo-panel-deepseek2-20261017-175338-69d8c43f active/rate_wait，下一问18:10:25（1292秒）。当前批18是分组不是日目标；日目标仍63。第一路risk_blocked/23完成/1prepared未知保留，未恢复。其他模型/05:00定时不变。报告maintenance/20261017-deepseek-interval/REPORT.md，服务器同目录backup-1792230767；apply_interval.py仅一次部署不可重复运行。

**2026-10-17 17:45 双号时序复核及临时文件清理：** 第一路09:59首次发送，第二路13:47:45首次发送；此前第一路15次意图；14:46:13首次exit77，17:10:37再次exit77，第二路17:16:54 exit77，17:26手动登录后看到禁言。双号后59分钟出现首次明确登录失效是相关而非定因，不把检测时刻/登录失效/平台禁言混同。未停第二路或改任务。服务器按plan逐文件复验进程/FD/systemd引用、/tmp直接普通文件、inode/mtime/size/hash，删除77个无引用中间文件54,848,869字节约52.3MiB。所有Docker无标签层都有当前/停止容器或回退链引用，删镜像0；容器/卷/队列/账号/证据/回退/当前源包保留。100/100映射及status/daily-control/auth-check.timer active通过。源码检查脚本已迁/opt/monitor/geo-capture/maintenance/20261017-scrcpy-public/check_mapping.py，此前许多/tmp/geo-input|risk|test-channel|scrcpy|ban上传副本已删，未来测试需从工作区重传；/tmp/vps_geo_access.py等其他工具保留。Windows本地递归缓存清理及缩小四个ZIP逐文件删除均被自动审批blocked by policy拦截，本地未删除，不要换工具绕过。详见maintenance/20261017-ban-audit/CLEANUP_AND_CONCURRENCY.md；服务器maintenance/20261017-cleanup含plan/result/concurrency及清理脚本。

**2026-10-17 17:34 DeepSeek新注册账号禁言底层审计完成（只读）：** 用户确认今天本人首次注册。最新第一路手动登录显示临时禁言至2026-10-20 09:09（界面未标时区，不换算），17:26:27这次登录后0新增采集发送。两正式通道审计发送点击意图24/14、入库23/14；最短间隔667.17/714.88秒，<600及<660均0，同题多次点击意图0，故没有单号降频失守或程序重发证据。第一路第24题仅意图无App用户回合，prepared保留不要重发；第二路有1send_uncertain但无重复意图。通道历史不等于当前新登录账号全部历史，不能据此断言新号处罚前问了多少次。两路不同账号、合并最短间隔63.91秒，11对跨账号<10min，无平台阈值不能定因。所有六台DS/豆包/元宝完全同镜像sha18244、Android13 x86/Houdini userdebug/test-keys privileged，AndroidID6个各异，3DS当前账号ID不重叠；都bridge无系统/环境代理，按配置共享出口；DS生产容器restart0/oomfalse、持久卷/token缓存在。DS正常UI提问+只读本地WCDB，豆包UI+本地会话，元宝Frida读取App对象；不能把其他模型暂稳定当成同环境对DS安全的证明。官方隐私政策列设备/IP/进程/操作记录；用户协议3.5(3)约束自动采集，属需要平台核实的原因范畴，不能声称查到具体脚本/Root命中规则。报告maintenance/20261017-ban-audit/REPORT.md及聚合audit/network.json；SUPPORT_REQUEST.md草稿未发送。没有改任务/频率/设备身份/网络/检测组件或尝试绕过限制。生产恢复源包仍100项，本次仅审计工具和证据；不导出token/手机号/原始AndroidID。

**2026-10-17 17:23 scrcpy输入延迟优化上线及正式账号登录失效：** 短点击单请求注入down/up，连续文本合并、drag仅保留最新未发move、每批16事件、队列有界，失败不重放。TCP_NODELAY、ffmpeg解码单线程/逐帧flush、multipart即时boundary；支持浏览器fetch解析JPEG画canvas只保留最新帧，旧浏览器img回退，断流自动重连；公网状态查询旧5秒超时改15秒，临时断网不覆盖风险提示，真实公网禁言验收复测通过。真实公网旧点击2请求6.1/8.4s→新1请求3.4/4.3s（仅2样本，公网物理延迟仍明显）；服务器本地入口ACK8–16ms，含App动画像素回显约484–539ms→358–442ms。101键→2请求、572拖动→1请求，前端8检查、Python2+5、桌面/手机隔离控制/真实视频风险验证/ready关闭通过，100/100源码映射。仅更新status/测试投屏，正式worker未被部署重启；发布记录第一路本已PID0，第二路46395保持。收尾发现两正式账号分别17:10:37和17:16:54自行exit77，实际只读auth均login_required，进度23/63和14/63、无待回传，已通知用户重新登录；勿沿用前条两路ready。其他当天通道均完成，保留原队列暂停不重发。报告geo-monitor-deploy/maintenance/20261017-input-latency/REPORT.md，服务器同维护目录有备份/多轮性能/验收/final-health；首次旧fixture预期touch及旧固定PID断言失败已查因修复。测试投屏原账号/禁言保持。

**2026-10-17 17:07 真实DeepSeek禁言账号优化已上线：** 测试机首页明确账号禁言至2026-10-24 14:04，旧auth_policy漏禁言只返回unknown；现两正式runtime策略补禁言/禁聊/封号/account muted，risk_blocked+account_muted+原界面截止时间（未指定时区），不能把token/欢迎语当可用，也不按日期自动放行。保留composer/弹窗上下文保护，正常回答引用禁言不误报。测试投屏state增加deepseek_test_auth.py只读十秒缓存/锁，风险信息显示但投屏及手动输入保留，不采集不提问不统计。7风险+5测试通道回归、真实公网禁言状态/日期/视频/控件验收通过，100/100源码映射；正式两号外部auth均ready、PID30871/46395未变，队列调度不变。报告deepseek-deploy/test-channel/REPORT_RISK.md，服务器maintenance/20261017-deepseek-risk含私有UI快照/备份/QA截图。通用违规提示不能推断处罚因脚本/网络/设备等具体原因；勿编造。

**2026-10-17 新建独立 DeepSeek 手动测试模拟器：** 容器deepseek-manual-test/独立卷同名-data/私有ADB5562，固定scrcpy模型deepseek_test、投屏端口8817、独立锁，用户自助手动测试，未加入MODELS/每日任务/认证巡检/正式回传或分析，无自动提问。入口 /api/geo-capture/login/deepseek_test/ui，公网保留/geo_monitor前缀；采集控制登录巡检区新增手动测试链接。点击打开/重开投屏，一小时会话，登录不自动关闭，持久账号保留。系统persist.sys.locale=zh-CN已仅重启测试容器验证，App条款尚待用户同意。静止视频20秒超时已修为继续等待并2秒缓存帧保活，测试机重启后独立ADB重连/失败状态已补，最终公网中文欢迎页已验证。正式两个worker PID30871/46395更新前后未变。5新增隔离+28网关测试，真实公网桌面/手机scrcpy视频无溢出JS错，0自动问题，99/99源码映射。恢复源包99项已更新；报告deepseek-deploy/test-channel/REPORT.md，服务器维护目录maintenance/20261017-deepseek-test有备份/release/构建日志/QA截图。创建与语言修正脚本一次性用，不加入定时，不盲重建已有测试卷。

**2026-10-17 16:47 DeepSeek 公网 scrcpy 登录投屏已发布：** 两账号新增五分钟服务器只读认证巡检，正常按钮灰色，确认掉线/验证/限制时亮起，当前访问设备浏览器承载官方 scrcpy-server 5.0 实时视频及控制（H264经ffmpeg连续转MJPEG，非截图轮询，不是启动远端设备桌面exe）。手机触摸/输入支持；仅连续正常账号+输入界面+无可见风险/验证码并完成模式校验才关闭，风险/未知阻断弹窗不判成功，原任务锁与暂停语义保留。unknown网络读取不直接判掉线，真实异常通过drain停止新题。第二DS父页面导航白名单已补。面板提醒和用户授权浏览器通知仅页面打开有效，无闭浏览器推送。两台真实只读视频、桌面/手机隔离输入和状态转换、预览/正式内网/公网浏览器验收通过；58 Python+28 Node测试、99/99源码映射。未强退正常账号或向生产App注入测试输入，完整生产重新登录待下次实际掉线验证。16:47 DS1 22/63 PID30871、DS2 12/63 PID46395均ready/running间隔等待且无待回传，采集进程未重启；其他通道当天完成。只更新status/daily actor/dashboard，问题轮数间隔调度队列不改。报告 geo-monitor-deploy/maintenance/20261017-scrcpy-public/REPORT.md；服务器同维护目录有备份/QA/截图/回退镜像记录。新timer为geo-deepseek-auth-check.timer，恢复包当前99项，不得覆盖用户新配置。

**2026-10-17 15:58 第一台DeepSeek重新登录已恢复、投屏已关闭：** 用户确认登录并要求关闭投屏。auth ready，daily actor自动启动同一原批次，PID30871，19/63真实processed（新第19题1162字/12来源），无待回传；第二台9/63持续running。仅验证serial后关闭scrcpy18920和15560→5560专用隧道，模拟器/ADB/第二台不动。掉登录原因核查：容器09:37起持续running、RestartCount0/OOMfalse，原/data持久卷在；14:35–14:55内核无OOM；Android窗口2838行无可证HTTP401/403/过期/踢出原因。exit-info的ISOLATED NOT NEEDED只是隔离进程回收，不能称主App崩溃。采集代码无退出账号/清数据动作。能证明App真的回到登录首页并触发77，不能确定服务端为什么让会话失效，勿编造风控/异地登录或保证永久不掉。只读脱敏诊断见maintenance/20261017-deepseek-health/logout-diagnostics.json和REPORT.md，无生产代码/间隔变更。旧等待登录记录由本条覆盖。


**2026-10-17 15:55 双DeepSeek健康检查：** 第一台18/63 waiting_login，App真实截图是验证码/密码登录首页、auth确认login_required；容器正常无容器OOM，不是冻结，未强行重启或重置原队列。第二台检查期间8→9/63、心跳/回执正常，无待回传，next16:07:44。已按既有偏好打开第一台scrcpy登录窗口DeepSeek - Login，PID18920，15560→5560隧道，保留给用户登录。daily_tasks现有每30秒登录复核会在ready后继续原任务；尚待用户手动登录，不称已恢复。完成后需复核原任务续跑并关闭仅该投屏/隧道。报告maintenance/20261017-deepseek-health/REPORT.md及第一台真实截图。

**2026-10-17 15:53 产品看板紧凑版已上线（覆盖190/230px大卡片）：** 用户反馈卡片仍太大及平均提及率色块铺满。现桌面/笔记本五卡统一110px高、小屏140px、极窄320px160px；月度产品/问题/天数/平均率/样本收成紧凑一排，细分隔线对齐，直接子small涨跌条改inline-flex文字宽度，不再撑满。核心推荐率/样本/涨跌常显，Wenxin/Baidu有效日期/最后检测日/原始次数/重复次数字段完整移到产品信息栏采样明细，可展开；不删除数据不改口径。预览/正式内网/正式公网Chrome各11尺寸2560至320px、24产品五卡宽高/文字/无溢出/数据不变通过；1366与1920明确卡高110、单产品月度块低于280；采样明细展开/关闭、元宝4/8=50%、无JS错/生产POST通过。首轮320px撑高已单独160px预留并重建复测，未增加桌面卡高。只改Dashboard/CSS、仅重建dashboard，其余Docker StartedAt不变，不改采集/API/数据/登录/定时/队列。91/91源码映射，正式验收后预览清理；报告maintenance/20261017-compact-board/REPORT.md及服务器同目录QA/截图/备份。下方190/230px历史设计不再适用。


**2026-10-17 15:45 五通道卡片统一尺寸已上线：** 用户反馈上一版文心/百度过宽且高度参差。现文心卡片、百度卡片拆为独立平级列，与DeepSeek/豆包/元宝同宽同高；标题/内边距/圆角统一，涨跌提示底部对齐，月度/每日都190px高、小屏230px预留长说明；五列/三列/两列自动换行，末行不拉宽，单模型筛选占满可用宽度。宽屏表格表头/列数同步五通道，数据仍原Wenxin双surface，不改后台统计。预览/正式内网/正式公网各11尺寸2560至320px，逐24产品五卡宽高测量一致（小于1px舍入）、数据/文字无裁切无横向溢出；元宝4/8=50%筛选、无JS错/生产POST通过。首轮320px和1280px高度差失败已修，重新构建全量通过。只重建dashboard，其他Docker StartedAt不变，不改采集/API/队列/定时/登录。91/91源码映射，正式验收后清理预览；报告maintenance/20261017-uniform-cards/REPORT.md，服务器同目录有release/backup/三份QA/截图。

**2026-10-17 15:36 产品看板小屏自适应已上线：** 用户截图月度汇总/每日明细右侧模型需要横向滚动。两表旧inline minWidth+固定列宽为原因，新增data-label/模型列class及容器宽度自适应，空间不足用完整产品卡片并自动换行，文心/百度并排，长文本/百分比/样本/日期/涨跌全部保留，不隐藏列不缩放整页。宽屏放开内容区至2000px、足够宽仍用表格；小屏保留正常纵向滚动。820px绩效卡片旧min260溢出一并修复。预览/正式内网/正式公网Chrome分别11尺寸2560至320px，两个区域24行全部内容/模型及双卡片可见、无页面或单元格横向溢出、窗口变化数据不变；元宝筛选4/8=50%、无JS错误/生产测试写入通过。最初测试权限/CORS失败和820px失败保留，修复后重新构建复测；未把失败轮记通过。仅更新Dashboard.tsx/globals.css，发布只重建monitor-dashboard，其他Docker StartedAt全不变；不改采集/数据/队列/定时/登录。91/91当前源码映射一致，预览容器已在正式验收后清理。详见geo-monitor-deploy/maintenance/20261017-responsive-board/REPORT.md，服务器同维护目录有release.json/backup/qa-preview|production|public.json及截图。

**2026-10-17 15:21 元宝正文与错误0%修复验收完成：** 用户指出元宝#48197富文本内标记及眉毛精华液0/8。原因是原生@mark_underline/@replace/商品/小程序控制未解码，隔断品牌产品导致漏识别；pending被默认brand_analysis_ready误作确定负结果；提取与否定校验还把选购提醒当产品/把避开致敏成分误作排除产品。新增monitor_core/native_text统一接收/分析/自有产品匹配，保留可见标签及citation，未知控制保留标记；answer_raw及原始ingest web_body/native/来源/run_id不动。修复632条元宝（三天359/105/168），补充115条小程序/媒体；原有模型复核两阶段32批调用、原120次/小时限额，所有受影响复核完成，普通product worker已恢复。今天初始快照其他500条正文不变，无同类控制/替换乱码/证实的负建议伪产品。今天眉毛精华液已核对4/8=50.0%，8条已复核；这是样本推荐率。20测试（含632历史夹具）、逐条原始正文/来源数量/身份/citation核对通过，真实LAN+公网Chrome50%及#48197正文/18来源、手机布局无错无生产POST通过。首轮公网旧正文失败保留，最终复测通过。采集worker未重启，配置/暂停/队列未改；收尾15:20发现第一路DS已在14:46自行退出77/waiting_login，18/63，device.auth只读确认login_required需用户人工验证（未强行恢复）；第二路PID46395 active、6/63。接收/API/普通分析Docker均running；91/91源码映射一致。详见geo-monitor-deploy/maintenance/20261017-yuanbao-text-audit/REPORT.md及evidence。DB备份database-before-1792217517.jsonl和database-before-mini-program-fix-1792218240.jsonl在服务器同维护目录，仅逐条追溯不能整库覆盖新数据；一次性repair/reanalysis脚本不要加入每日调度。

**2026-10-17 13:51 DeepSeek第二路已正式采集，1/63真实入库：** 用户明确要求按另一账号问题配置开始。复制第一路当天保存21题/3轮/interval600（policy随机660–1140秒），第二路独立63次；账号ID仅比较确认不同，独立deepseek2_account.lock/deepseek2_last_send.json、任务SQLite和回执，原主队列不动。新增control MODELS/fleet第7项deepseek2/DeepSeek 2，source_device=deepseek-hpe14-account2、receiver模型仍deepseek，daily DEVICES计数独立，不抵扣第一路。面板独立配置/暂停继续/Logo/随机说明、重新校验已接入；登录失效时第二账号用open-deepseek2.ps1投屏，不能调用主账号登录页面。daily_plan加入deepseek2、当天running任务及target批次已启用，每日05:00继续。批次geo-panel-deepseek2-20261017-134730-bf1a1e9e，PID46395；第一PID44432/15完成保持，其他采集器未重启。首条1090字/12来源与native/processed逐字段一致、首次用户回合、thinking=false/search=true、发送仅1次；当前1/63，next14:06:36（1131秒）。61测试及LAN Chrome七通道/桌面手机/无JS错无生产测试写入通过，公网首轮网络超时保留，随后真实公网Chrome七通道/第二路桌面手机复查通过（started-qa.json public_seven_channels=true）。85/85源码映射一致，reader/android/policy源均同步两runtime，专用profile在deepseek-deploy/account2。备份deepseek-second-lane-1792216050；报告maintenance/20261017-deepseek-account2/REPORT.md。start_lane.py仅一次登记，不可重复建批；不要恢复旧DB覆盖现有采集。

**2026-10-17 13:42 DeepSeek第二账号登录已验证并关闭投屏：** 用户说登录完成。第二设备auth ready、持久卷内单个有效账号token已保存，账号与第一账号不同（只记录比较结果，无凭据输出）。智能搜索true/深度思考false。仅对空闲第二App force-stop后冷启动并再次验证ready/模式，证明App重开持久登录；零提问。device.json现state=ready/scheduled=false，第二账号尚未分配任务，不得称双路已采集。scrcpy第二窗口PID39300及专用本地15561→服务器5561隧道已关闭，第二模拟器仍running；原主worker PID44432/14已入库正常等待，未重启。检查脚本maintenance/20261017-deepseek-account2/check_login.py仅独立进程覆盖设备选择，不改生产主模块。报告同目录REPORT.md已追加。

**2026-10-17 13:39 用户新增DeepSeek第二模拟器并投屏待登录：** deepseek-hpe14-account2，独立卷deepseek-hpe14-account2-data:/data、2CPU/2GiB/含swap3GiB、原HPE镜像、官方APK2.6.2/v281 SHA一致；仅复制APK，不复制原账号/队列。AndroidID已验证不同，简体中文已设。ADB服务器回环5561，WindowsSSH隧道15561→5561；新启动器deepseek-deploy/open-deepseek2.ps1与artifacts-account2目录，scrcpy窗口DeepSeek 2 - Login/PID39300已打开且真实截图确认手机验证码/密码登录入口，保留给用户操作。服务器/home/user/redroid-deepseek-account2/device.json标记awaiting_manual_login/scheduled=false，未启动第二路采集；用户登录后需先验证再接入，不能误用原device.py硬编码主设备。原DeepSeek worker PID44432/模拟器/队列不变。报告maintenance/20261017-deepseek-account2/REPORT.md，provision.py一次性不可删卷重跑。

**2026-10-17 12:12 DeepSeek第八题空来源标题卡住已恢复：** 7/63并非正常等待：原答FINISHED、1035字/12来源，其中两条原生title空导致reader无限DataError回读，App登录ready。reader改真实URL显示标签，native_title原值/缺失标记/title_origin=url_fallback保留，raw_answer_blocks不变、source_metadata_complete=false/缺失数2明确记录；不丢来源、不伪造标题，URL/首问/完成/模式门槛保留。worker受控错误原因写progress.reason。15测试通过。原题prepared且唯一点击/唯一绑定原答验证后重载DS worker，前后7完成55待发1prepared无重置，其他采集器/App不重启；PID44432，备份deepseek-source-title-1792210220。第八题12:11:27补读入库、原文/片段/12来源回执一致，发送点击仍1次；第九题12:11:47也完成。当前9/63、54待发，next12:30:13；两回执相距20秒是旧答补读非重发，故障实际等待超20分钟保留事实。79/79源码一致。报告maintenance/20261017-deepseek-source-title/REPORT.md。一次性recover.py不可日常重复执行。

**2026-10-17 11:03 采集面板“连接中断”残留提示已修：** 用户截图红条不等于后台停止。API无重启、约1.506GiB/8GiB，8803状态200/0.086秒，DS4/63/文心115/168继续。refresh catch写共用notice，但恢复成功从不清理，确认显示缺陷；截图原始失败的网络/HTTP/渲染原因没有浏览器记录，不能臆测。panel.html改独立connectionNotice并成功自动清除，失败禁写/旧数据/5秒重连保留，不清理其他操作提示。真实Chrome503自动恢复、网络/畸形JSON恢复与公网iframe新版/6模型/无JS错误测试通过，无生产写入、无服务重启。79/79源码一致，报告maintenance/20261017-panel-reconnect/REPORT.md。现有浏览器刷新一次加载新HTML。

**2026-10-17 10:43 DeepSeek登录正常、第三题恢复入库；API上限8GiB：** 检查发现随机第三种欢迎语造成2/63准备重试，非掉登录。android.py改按空新对话布局/正向账号与模式证据判断，不再枚举欢迎语；13测试通过。证明无prepared/未知发送后同批队列安全重载worker（现PID3907），无重置/重发，其他采集器未重启。第三题10:42:13真实553字/12来源，首问、thinking=false/search=true及processed已核对；3/63、60待发，next10:53:37，692秒。第二→第三实际1237.74秒，超20分钟37.74秒，保留异常不可称全程合规。用户授权提高内存，API在线6→8GiB、含swap7→9GiB，compose持久化且配置校验，API无重启；当前约1.412GiB。Android原2GiB与其他限额不动。备份deepseek-layout-memory-1792204871，79/79源码一致。报告geo-monitor-deploy/maintenance/20261017-memory-and-deepseek/REPORT.md。

**2026-10-17 10:39 面板 API OOM 根因已修复：** 内核多次memory cgroup OOM均为monitor-dashboard-api超过6GiB（最新10:27），不是DS模拟器。py-spy定位activity轮询并发整份解析319MB豆包信源索引，lru_cache两代且无singleflight。新增monitor_core/source_activity_index.py分块精简状态/保留既有产品标签，单代缓存+锁；API activity现有JSON缓存3秒/10秒合并重复请求。10:36:30仅重启API，采集PID DS19635/文心14824未变，配置/队列/历史不动。5项单测、真实106107条索引1.67秒/峰值73.6MiB、48并发、真实公网activity验证通过；正常请求后API约0.9–1.0GiB，12次/56秒采样无新OOM/重启，短观察未替代整日验证。限额仍6GiB，未通过放宽额度掩盖问题。79/79源码映射一致。报告geo-monitor-deploy/maintenance/20261017-api-oom/REPORT.md；备份服务器同目录before/，健康采样observation.json。

# 整个项目当前交接：GEO采集、分析、创作与运行维护

**2026-10-17 10:22 第二题问候语误判已修复，账号未掉，真实2/63：** 用户要求检查及截图。服务器App登录探针ready、容器running、原worker29680 active但preparation_backoff一直1/63；真实新对话第二种问候语“你好，我能帮什么忙吗？”被只识别“嗨！今天想聊些什么？”的准备门禁拒绝，非登录失效。新增LANDING_GREETINGS共用两种已观察文案并回归两者、不发题；准备错误保留具体受控reason。先证明没有prepared/未知发送，再同一批次/原SQLite无重置安全更新DeepSeek三个模块并续跑（PID19635），其他采集器未重启；backup `deepseek-greeting-1792203640`。第二题“推荐一款护发素”已processed，正文938字/12来源、first_user_turn=true、thinking_enabled=false/search_enabled=true；共2/63、61待发、rate_wait，下一题北京时间10:34:06左右。首次两点击实际间隔1342.65秒（22分22.65秒），此异常导致超出用户20分钟上限，已明确告知并保留事实，不称全程合规；下一次计划759秒。新回归12测试通过（含随机问候语两子例），前面的截图和当前恢复截图分别为maintenance/20261017-deepseek-native/deepseek-live-status.png及deepseek-after-greeting-fix.png。无需再登录/重发旧题/打开投屏。用户截图只是中途查看，不取消采集及修复。


**2026-10-17 10:05 DeepSeek改为独立无头安卓App，已完成首条实采：** 用户放弃网页版，要求scrcpy登录、简体中文、每题3轮、每次>10分钟且<20分钟、只智能搜索且不深度思考。新独立容器`deepseek-hpe14-android13`、固定卷`deepseek-hpe14-android13-data:/data`、回环ADB5560，官方App2.6.2/version281；Windows `deepseek-deploy/open-deepseek.ps1`复用原SSH工具投屏15560，用户已手动登录，已只关闭DeepSeek scrcpy窗口。当前主批`geo-panel-deepseek-app-20261017-094524`真实1/63、62待发、running/rate_wait；首题只点击一次，原生首问首答824字/12来源/FINISHED/thinking_enabled=0与真实processed逐字段一致，SHA93329737d4b2bc26150eed4df907f0733197f34852a588794b15d8d356f78710。随机11–19分钟，第一次已持久化703秒，下一题计划10:10:48左右；共用`deepseek_account.lock`及`deepseek_last_send.json`，重启不重抽提前发送。安卓WCDB原文/信源/引用读取、稳定快照、原接收回执，未知点击补读不重发。旧网页44/63和19待发保留且归档未重发，当前改native服务；旧常驻服务加ConditionPathExists保护、capture_bridge禁旧网页入口，避免重启复活网页采集。scrcpy和Windows专用登录隧道均已关闭。创作01:00专用DS已接同一App的private_capture，私库/进度单独保存，不构建GEO receiver，原错峰等待及费用禁自动写作保留。控制20+每日24+原生/私库/停用网页13及创作素材7测试及真实公网桌面手机无JS错、无测试生产POST通过，面板显示App/随机间隔/模式。其余采集服务/前端Docker/原安卓未重启；最新双豆包105/105、百度105/105、元宝168/168，文心87/168继续。**本次只验收首条及计时，尚未跑完63或完成整夜稳定性验证；当前collector为保留连续运行未做重启测试，磁盘后续增强校验在下一批自动加载。** 报告`geo-monitor-deploy/maintenance/20261017-deepseek-native/REPORT.md`，代码`deepseek-deploy/`；备份`/opt/monitor/geo-capture/backups/deepseek-android-1792201524`。不能清除Android卷/队列/bindings/outbox/receipts/全局时钟。

**2026-10-17 09:20 公网旧界面根因及修复：** 用户用1any.top/geo_monitor，不是内网3000。3000镜像ecb5660d96fe/creation-workflow-20261016及13000隧道都为新版Dashboard-uloUm694.js，但公网HTML缓存仍引用旧Dashboard-828cJjD3.js，导致带夸克旧工作台。VPS Nginx根location共享缓存（固定v3 key+stale/background+ignore上游cache-control）仍启用，对浏览器却no-store。只在GEO根location关闭proxy_cache，保留鉴权/API缓存/隧道和offline fallback，nginx-t后仅平滑reload，无本地服务/采集重启。公网资源已与LAN一致；真实Chrome六通道/每日卡/05:00/去夸克及创作Word知识库/任务配置/94篇可见。备份`/root/geo-monitor-access-backups/20261017-frontend-cache-1792199866`；报告`geo-monitor-deploy/maintenance/20261017-public-entry/REPORT.md`。后续必须验证公网，不能只凭内网验收；旧缓存配置不可再覆盖回来。

**2026-10-17 09:04 首次01:00创作专用采集失败已查明并修复权限：** 凌晨01:00:01实际启动CLI后被父目录权限挡住，DS/百度/文心均0，不能称已采集。B=/opt/monitor/geo-content原root:root0700及materials/days原root0700（UMask0077隐式父目录）导致user虽拥有collector子目录也不能进入。新增materials.collector_directory校正所有私有祖先user0700，对B仅root:user0710赋组穿越，不给列目录/其他用户权限；保留runtime私有和凭据限制、拒绝越界/symlink。真实uid1000隔离及生产三路径写读探针通过，16素材/编排回归通过，主六通道/原创作worker PID未变，仅空闲私有素材daemon安全重启。当前waiting_for_geo按规则等文心主采集结束，尚未真正补采成功。主GEO DS昨天44/63剩19因登录失效，今天0/63；私有DS0/16除权限已修复外仍需用户登录。报告`geo-monitor-deploy/maintenance/20261017-creation-permissions/REPORT.md`，源码67项。以后必须核真实collector用户与所有父目录，不能只看root/API测试。

**2026-10-17 05:18 geo-2每日只读核查：** timer实际北京时间05:00触发、dispatch成功，daily_control心跳新鲜，持久状态在`daily/2026-10-17/status.json`（不是daily/status.json）。按当日保存配置：双豆包各21×5/45秒、百度21×5/60秒、文心21×8/60秒、元宝21×8/45秒、DS21×3/600秒。双豆包16/15、百度14、元宝21均逐项与当天PG成功回执一致、active且无回传积压/needs_review，计数仍增长；文心waiting_for_baidu正常，不告警不抢跑。**DeepSeek旧批次44/63后明确退出77，collector/deepseek_session.json=login_required（检测到登录入口），今日0/63且未建新批，需用户重新登录；本次已通知该阻塞并给采集控制台入口，下次同一登录阻塞未变保持安静。** 没有改轮数、建批、恢复暂停、重启服务或复活旧测试/内容工作台。只读脚本`geo-monitor-deploy/maintenance/20261017-daily-heartbeat/audit.py`。

**2026-10-16 18:04 创作中心主流程已按用户纠正重做：** Word产品知识库→问题/模型/轮数/首次日期/采集+分析仿写时间→每日自动任务→Word成稿。新增studio.py/studio.service，产品/版本/imports/每日plan账本均私有；原手动素材复用/老队列收进高级操作。当天视图产品日期筛选、任务数/运行/完成/需处理、模型采集进度、分析写作/审稿/成稿、异常原因、暂停/继续、查看下次任务均已上线。24Python+24Node/构建和隔离真实API全流程及正式Chrome手机/iframe通过，无生产测试Word/新任务/付费调用。原94成稿/2任务/16题01:00采集保留；**迁移计划自动付费写作未启用，04:00仅表单可编辑初值，用户确认知识库和分析时间后点击保存并启用才自动创作**，不能误称已跑自动写作。首次原采集10/17 01:00尚待实跑。多产品独立素材、共用账号锁/主GEO优先、DS600秒、百度后文心；跨天原任务续跑、采集时快照冻结、暂停不被入队回写覆盖、每日任务+问题固定幂等号，未知API不重发、原预算/事实/审稿门槛不放宽。主采集和原创作worker PID未变；原专用素材服务当时空闲后重启以加载新功能，启用新studio服务。源码67项，私有知识库Word/运行计划不进包。报告`geo-monitor-deploy/maintenance/20261016-creation-workflow/REPORT.md`。

**2026-10-16 17:34 创作中心产品/日期筛选已上线：** 成稿区增加产品、任务日期、今天、清除筛选，产品日期同步过滤下方创作任务；数量卡片和ZIP跟随全部成稿筛选，空结果禁用打包，刷新保持选择及列表滚动。按任务所属素材日归档；产品读历史daily product快照，旧历史缺快照不套用现配置而显示未标注。后端bundle筛选参数校验，条件摘要隔离导出文件名，Word原字节不改。15单测+预览/正式Chrome交叉筛选/ZIP哈希/任务联动/手机布局通过，无真实POST或额外收费调用。仅重启创作API，主采集、创作worker和独立素材worker PID未变，定时配置未改。报告`geo-monitor-deploy/maintenance/20261016-creation-filters/REPORT.md`。

**2026-10-16 17:25 内容创作中心改版已上线：** 用户选择专用采集每天北京时间01:00，首次10/17；原16个去屑/止痒问题恢复，历史294条可读。新`geo-creation-materials.service`已enabled/active，独立存`/opt/monitor/geo-content/materials/`，直接CLI且不接GEO bridge/receiver，今天主库专用问题0条。主GEO全部空闲才发送专用题；临近主05:00窗口安全让出，共用flock/DS全局600秒发送时钟，百度后文心，各16题1轮，采集不自动启动付费写作。界面顶部94篇成稿（原82+新12）搜索/预览/Word/Markdown/ZIP，表单普通产品事实保留证据元数据，默认独立素材，可显式只读复用GEO，底部保存时间/专用问题、暂停/继续。原预算和独立审稿/Word门槛沿用，原队列未续跑。14创作+13Linux桥接+3时钟+23Node测试和构建通过；预览/正式Chrome94个Word与原回执哈希一致、ZIP188项、桌面手机/iframe通过，所有测试POST隔离，无真实新增付费任务。主采集PID/启动时间未变，DS原任务继续；首次01:00尚待实际运行，不称整夜已验证。64/64源码同步，预览已清理，生产镜像creation-studio-20261016、回滚before-creation-studio-20261016。详见`geo-monitor-deploy/maintenance/20261016-creation-studio/REPORT.md`。原工作台旧抓取调度继续暂停，不要与新素材服务双开；本文下方历史“仅复用GEO素材”已由本条覆盖。

**2026-10-16 16:31 每日定时编辑和Logo已上线：** 每日任务下方新增全局启用/每天北京时间/下次启动/保存；新同源CSRF control/schedule接口版本与幂等校验，保存daily_plan及`/etc/systemd/system/geo-daily-dispatch.timer.d/30-schedule.conf`，只操作timer，不停采集。due()已从写死05点改为读取小时分钟，未来预配置行scheduled未到点/关闭定时不提前运行。55Python+22Node测试及构建通过，正式/预览1600/1280/390px与保存/丢响应原编号重试通过；真实按原值05:00启用保存一次，next_run=2026-10-17T05:00+08:00，systemd已核对，所有采集PID/启动时间与发布前相同。6通道任务卡、切换栏、标题Logo均本地内嵌，复用主面板SVG和百度官方favicon。真实主面板iframe桌面手机无溢出/JS错误，源码60/60一致，预览已清理。用户此前把豆包1/2改5轮及豆包2手动暂停是用户现有配置，保留勿改回10轮。报告`geo-monitor-deploy/maintenance/20261016-schedule-logos/REPORT.md`。每日核查先读取用户保存时间和enabled；未到时间/关闭定时不能误报。

**2026-10-16 16:17 纠正运行中校验红字误导：** 用户截图任务running/rate_wait但登录check红字。实时会话ready、桥接active，确无再次掉登录；5分钟启动前校验到期被通用提示误写为“登录尚未通过或校验过期”。已改控制提示区分运行中/空闲校验过期/实际登录未通过，保留开始和继续的严格校验；运行中login和idle两项用中性提示、隐藏无用登录按钮、说明无需重复登录或继续。20控制测试、真实Chrome运行中校验过期夹具通过（无真实POST），生产API运行中，未重启采集器。58/58源码一致。用户刷新旧控制页加载新版，不能说会话永久不会过期。

**2026-10-16 16:13 用户已登录，持久化生产验证及原任务恢复完成：** 新flow770b58d1于16:07:22自动ready，已真实关闭登录Chrome并重开校验；geo-session.json权限600 user:user，39个localStorage项、1个sessionStorage项及3个session Cookie已私密保存。进一步鲜活校验全5项通过后，按用户原授权继续原63次batch，不建新批。当前32 processed/63、31 pending、active/rate_wait、pending_delivery=0，bridge PID24470；新CLI已经自然关开浏览器成功采下一题并再次保存会话。状态截图暴露旧waiting_login健康快照未被登录复核替换，已修控制API响应：ready_to_resume/正在启动、每日卡片同步，真正新登录失效仍覆盖；前端登录检测消息+跨页storage事件+1秒轻量状态检测，最终ready自动刷新。20项控制测试及真实Chrome隔离自动刷新测试通过，无真实测试POST；正式API current和daily均running。仅重启status，采集PID未变；58/58源码映射一致。用户刷新旧控制页加载新版即可。下方“待登录/未恢复”记录均已被本条覆盖。

**2026-10-16 16:02 登录页卡顿已优化：** 用户反馈登录页卡顿，实测原GET panel初始化4052ms、截图43–55ms；旧页串行读六通道面板、状态+帧并等待900ms。已改fleet_status登录UI自行建立原内网控制会话（HttpOnly/SameSite/CSRF保留），login/state仅附当前csrf，无需昂贵全量panel；HTML帧循环独立160ms、状态1秒、输入完成立即拉帧、快速文字60ms合并且保序，不重试输入。bootstrap权限测试及真实Chrome隔离输入夹具通过（11字符+退格仅3POST含点击，无panel调用），正式初始UI5.5ms+state10.7ms/frame43.6ms。仅重启status服务，手动登录浏览器和采集器均未重启；原flow仍waiting_login，用户需刷新登录页面加载新版，远端输入保留。源码58/58已同步。登录持久化的生产账号校验仍待用户完成登录，勿误称已恢复采集。

**2026-10-16 15:50 DeepSeek登录持久化已部署，真实账号待用户重新登录验证：** 旧流程15:45再次login_required/退出77，31/63、32待发；并非本轮主动停止。查明本地薄弱点：每题max-new-captures=1关闭Chrome但3个关键Cookie为session Cookie、无专门保存；profile跟随批次导致新日不继承。新增web_collectors/session_store.py，ready周期/关前私密保存、启动恢复缺失Cookie和local/sessionStorage、只限DeepSeek origin、不覆盖刷新值/不恢复过期或明确失效备份；state0600、profile0700且沿用user属主。共享profile路径`/opt/monitor/geo-capture/profiles/deepseek`目前symlink到原今日batch profile，不得清理该目标。48测试和隔离真实Chrome重开恢复验证通过，源码58/58一致。旧有效会话在部署前已失效，生产user只读重开仍login_required；已通过login_open打开 http://192.168.31.106:3000/api/geo-capture/login/ui 并向用户发登录请求，等待完成后检查自动checkpoint/关页/重开校验、继续原63次，不建新批次不重发未知题。无法从旧日志证明下午失效的服务端原因，不能称永久不掉登录或生产重开已验收。报告`geo-monitor-deploy/maintenance/20261016-deepseek-session/REPORT.md`。

**2026-10-16 15:36 用户要求全量数据审计，已只读完成：** 今天快照989成功观测（D1=449、D2=0、DS=30、文心212、百度193、元宝105）；原始SQLite1016条=989入库+27百度明确不可用旧结果，逐任务正文/来源/问题保真无不符、日期/来源数量/请求唯一性无异常。2981条monitor_products子表证据全部能在各自正文找到，统计24产品/21问题的分母、百度去重和百分比独立核对无误。仍有46条产品识别积压（元宝42、文心2、豆包2），已重试3–4次、部分延期明天；模型返回不扎实证据被校验拒绝，未强制标通过。15:35新增DS第31条retry0属新分析，不混入积压。D2今天0/210，元宝原105/105完成但新168目标差63；DS仍采集中。百度10条body_only不能称完整信源，162次相同正文观测已按日/题去重。此次没有修改配置/数据、重发或启停采集。完整报告`geo-monitor-deploy/maintenance/20261016-all-data-audit/REPORT.md`。

**2026-10-16 15:28 每日任务控制已部署，优先于下方早期状态：** 正式3000六通道每日任务卡、日期切换、逐题进度、全部问题/轮数/间隔配置、手动暂停/继续及“保存并立即生效”已上线。当日保存安全收尾当前题后只补剩余；手动暂停持久化且保存不解除暂停；未来日期配置可独立修改，历史只读。`daily_tasks.py`和`geo-daily-control.service`持久执行，daily_plan.daily_control_enabled=true；05:00日调度与先百度后文心保留。今天6行observing仅接管原有任务，不自动补建今天差额；旧测试不恢复。用户点保存/继续后接管该日执行。登录校验和600秒跨批间隔保留。63项Python、21项Node测试及构建通过；正式UI六组场景及主面板1600/390px无溢出、page_errors=[]。源码映射56/56一致，source-current.zip已更新，预览容器已清理，回滚保留。报告见 `geo-monitor-deploy/maintenance/20261016-daily-controls/REPORT.md`。

最终真实进度：DeepSeek30/63、rate_wait、pending_delivery=0，PID41728。日志显示05:18UTC因登录退出77、05:30UTC重新启动，故不能说PID始终不变；本轮发布未主动重启采集器。百度193/105、文心212/168当天目标均覆盖，重复仍在原观测保存、分析按日去重。元宝原105已完成，新每日168目标还差63；豆包1当天449>=210，豆包2当天0/210，旧任务保持封存。不能宣称今天六通道都在跑。geo-2核查已改为读取用户保存的动态每日配置，尊重暂停和observing，不再用固定轮数覆盖。

**2026-10-16 11:47 最新验收，覆盖下方早期状态：** 今天百度21题每题至少5轮、文心21题每题至少8轮已全部入库。正式3000页面24产品、48个文心/百度单元格逐项验证通过，missing=[]、page_errors=[]，本地证据`geo-monitor-deploy/maintenance/20261016-daily-start/all-card-board-verified.json`及`all-cards-live.png`。百度提前跨日去重导致122次今日观测沿用昨天回执，现已改为每轮独立持久化、当天分析去重；183条完整信源原始观测回放完成保真验证，另10条无公开引用的完整正文记录保留source_capture_complete=false。文心护发精油专项8/8完成，其他20题>=10。原因与GitHub同页展开对照见`DAILY_COVERAGE_FIX.md`，不要再用原始采集轮数代替当天面板验收。

用户最新要求**每日先百度后文心**已部署：北京时间05:00启动百度21×5，全部真实卡片完成且回执齐全后才启动文心21×8，其他模型独立运行。无卡片在日常模式保留未完成并持续安全重查，不算正常完成轮数；百度仍在采集时文心waiting_for_baidu是正常等待。2026-10-17首跑，豆包1/2各21×10、DS21×3/600秒、元宝21×8，服务器systemd执行；应用geo-2仅05:15核查且正常不通知，已同步顺序。普通异常持续恢复、确认登录/人工验证才等待、计划跑满正常结束。16模块167项测试通过，当前源码映射54/54一致。

DeepSeek今日63次原批次已10 processed、0 needs_review、active/rate_wait，下一题等待600秒间隔。恢复代码收尾局部变量遗漏及原页导航加载竞争已修正并补真实路径测试；第10题原会话只读补回967字/12来源，原任务和PG回执确认，无重复发送。桥接03:27旧代码异常后由新systemd策略自动重启一次，当前PID19602，不能再说本轮全程采集PID未变化；维护部署未主动停止它。元宝今日原105/105 complete且无回传积压，下一次每日8轮设置已保存。两豆包仍是旧12h封存批次paused/failed，各有旧未知题，不恢复旧测试或误称六通道当前全在跑。最新服务器证据`maintenance/20261016-daily-observations/final-runtime-audit.json`。

**2026-10-16 11:27 最新纠正，优先于下方“最终状态”：** 用户截图揭示旧核查遗漏。原百度桥接在入库前跨日复用相同内容的首个回执，造成今天原始采集已完成、PG当天缺行、面板0/5。现改为每轮原身份独立回传，重复仅作当天分类，产品分析仍按当天正文去重；12项桥接回归/总164项无人值守测试已通过，部署零采集进程重启。独立补回服务geo-repair-daily-observations-20261016正在从原SQLite回放今天183条完整信源观测（不重新搜索），历史outbox/回执/原任务保持原样；其余10条完整正文无公开引用已独立入库。尚须读取maintenance/20261016-daily-observations/{verified,board-verified}.json确认全部21题/24产品，不能只用原始采集>=5替代面板核验。文心当天20题>=10轮，护发精油0，已启动补采geo-panel-wenxin-card-20261016-112430-9f29da9d，1题×8/60秒，下次21题×8设置恢复。DS和元宝当前进程不变。原文心百度09:48确被旧12h deadline暂停，不能称从未停止。

每日计划与无人值守已部署：北京时间05:00，明日2026-10-17首跑，21题，豆包1/2各10轮、文心8、百度5后去重、DS3/600秒、元宝8；正常跑满结束。系统geo-daily-dispatch.timer+5分钟失败重试、原批次续读/指数退避/确认登录失效exit77，普通故障重启同服务15秒，不擅自重发未知题。现有DS63/元宝105批次参数不变。新版源码映射54/54一致。应用heartbeat geo-2仅05:15读状态，正常不通知。不要恢复旧12小时测试或重跑一次性启动/部署脚本。

**2026-10-16 本轮最终状态，覆盖下方10:02早期记录：** 百度今天三题专项已完成15/15（护发精油/卸妆油/防晒霜各5），连同已有18题，今天21题每题至少5次完整卡片正文观测。卸妆油/防晒霜同页对照GitHub参考项目：初始折叠、展开点击成功、最终有“收起”，上游无法再展开且双方全文逐字一致（711/592字）。缺口原因是原citationCount>0与完整信源回传门槛丢弃完整正文，另护发精油为换日缺额及原长测到点暂停。新`baidu_body_delivery.py`独立回传已证明正文，source_capture_complete=false保留；10条正文已PG回执与原始数据保真核对，产品表可见，引用KPI不计这些记录。不得再说这10条没回传，或将其称全部信源完整。重复轮次仍在SQLite/原观测中，面板合并相同有效样本。

DeepSeek今日原63次批次 `geo-panel-deepseek-20261016-094039-dc64b7e1`，最新5 processed、active，21题×3/600秒。10:05第四题发送前等待间隔发生CDP读取超时；确认3完成/60待发无未知后重新校验登录，经原resume继续，第四/第五题完整PG回执通过。元宝 `geo-panel-yuanbao-20261016-100013-89d43fdd` 最新41 processed、active，21题×5/45秒、105计划，旧歧义任务仍封存。不要恢复旧队列、重跑一次性启动/恢复脚本或中断当前服务。

用户要求的登录功能已正式部署：登录按钮、用户手动完成登录、检测后窗口/登录浏览器关闭、采集会话重新打开复核、设置/登录/旧题状态/回传/进程空闲全部通过才亮起开始或继续、重新校验、5分钟过期与设置变化失效。当前采集中按钮禁用正确。原Windows helper仍保留，但新网页登录入口通过面板同源鉴权转发到临时loopback8805，不公开CDP或登录token。正式镜像 `monitor-dashboard:manual-login-20261016`/local，仅控制服务及前端更新，部署未重启采集进程，其他10容器未变。预览与正式浏览器验收通过；当前恢复源码映射45/45一致，可按当前package_current打包，不再含未部署登录代码。证据与完整解释见 [10月16日本轮报告](geo-monitor-deploy/maintenance/20261016-daily-start/REPORT.md)。下方保留历史过程，不当作当前待办。

**2026-10-16 10:02 当前采集优先，登录功能暂缓部署：** 用户要求先跑完百度今天缺口并启动元宝，再继续登录按钮/校验功能。DeepSeek已于09:40启动今日新批次 `geo-panel-deepseek-20261016-094039-dc64b7e1`，21×3、600秒，10:00已有2条processed；勿恢复昨天420题或中断此服务。元宝10:00启动 `geo-panel-yuanbao-20261016-100013-89d43fdd`，同21题×5、45秒，首题已processed。昨天322题DTMP旧首答不可严格选取，未放宽parser或误标成功；经两次完整原历史/已完成末答/会话不busy核对，按用户明确“今天新任务”要求对该精确旧批次做一次封存换日：旧needs_attention原行逐字段不变、两组原答案未入库、未重发旧题，新105题独立身份。证据 `maintenance/20261016-daily-start/yuanbao-rollover/`；start_yuanbao_today.py为已完成一次性操作，不重跑。

百度原12h于09:48截止按原规则暂停（非新崩溃），当前专项补采 `geo-panel-baidu-ai-20261016-095851-ff407fd3`，3题×5、60秒，只补今天缺口：护发精油/卸妆油/防晒霜；其余18题今天已有至少5条完整记录。下次任务设置已恢复完整21题，当前15题配置锁定。实页防晒霜有592字卡片，但无公开引用，仅相关搜索及商品购买链接，不能拿这些当信源。已只部署CLI、wenxin_monitor/controller.py、capture_bridge.py三组件，零服务重启；新增body_only保留稳定完整卡片正文与来源状态，不作为完整信源成功、不回传GEO成功、不算负样本。补采首题7来源processed、第二题body_only已保留，剩余继续。参考项目commit8789ea2与上游HEAD一致，参考直接链接/资料抽屉路径但排除购买链接。旧卡片完整性/已知失败/所有原始队列保留。

本地登录功能代码正在开发（control_panel.py/fleet_status.py/panel.html/网关及新增manual_login.py/deepseek_login_ui.py/deepseek_login.html），**尚未部署**；不要把本地这些文件直接当当前生产或用全量package_current误包未部署代码。百度补采完成、元宝启动核验后再完成该需求：登录按钮、用户手动登录、检测登录关闭页面、全部校验后亮起开始/继续、重新校验。现有Windows登录helper已同步GEO成功并关闭，原内容工作台同步超时且未恢复其抓取调度。

**2026-10-16 09:55 原12h验收收尾：** `question-only-soak12h-rowidfix-1792072084`固定43200秒窗口已结束，结论failed，不能称六通道连续12h通过。独立deadline于09:48:05成功执行；原五个当前批次暂停，新DeepSeek `geo-panel-deepseek-20261016-094039-dc64b7e1`被跳过并继续active。原监督器把新lane的active错误纳入旧测试排空条件，原raw status仍draining且切换后DS计数混入新面板；已保留全部原始证据，按manifest旧批次SQLite/1800条唯一文字PG回执独立复核后，仅于09:53:32.469停止到期监督器，另存服务器原root/final_adjudication.json。记录器墙钟43527.795秒、2151采样（窗口内2135）、最大间隔21.897秒、sample_error0。两豆包/元宝原未完成阻塞保留；旧DS登录中断仍导致窗口仅1条，新DS不并入。窗口实际新发完整观测D1=571、D2=109、元宝=101、DS=1、文心=251、百度=221（38唯一/183重复）；processed增量另含4条基线带入。百度累计37次不可用=35卡片不完整+2DNS，元宝1非文字审计属基线；豆包1六条已完成错误及六次重试事实保留。09:21及09:33两次用户前端重建记入报告，不称全栈零重启。脱敏最终报告与哈希核验文件在 `geo-monitor-deploy/reports/20261015/capture-12h-final/`。创作6h已先前报告完成，两项现均完成验收报告；按原授权暂停heartbeat，geo/10保持PAUSED。今天的新DS和其他用户后续工作继续，勿恢复旧队列或重复报告。

**2026-10-16 09:33 表格布局修复：** 用户截图中的文心/元宝重叠已修复。原按nth-child序号分配模型列宽，夸克移除后文心双卡片落入单列；现由colgroup按模型类型分配列宽，汇总/每日表最小宽度随模型数量变化，月份控件窄屏换行。正式镜像 `monitor-dashboard:board-layout-20261016`/local，仅前端再次按用户要求重建，其他10个容器镜像/启动时间不变。预览与正式3000在1920/1600/1280/390px、左右滚动、文心/元宝/全部模型切换共11组布局检查通过。证据：`geo-monitor-deploy/maintenance/20261016-board-layout/`。今日采集请求仍未完成：元宝新建因旧322题needs_attention被API409阻止，未绕过；DeepSeek两原profile均login_required，用户要求打开登录入口，既有open_deepseek_login.py已以pythonw PID8932启动可见Chrome，状态文件在reports/20261015/deepseek-manual-login.json，09:31仍waiting_user_login。收到完成登录后复查同步并创建当日63题新任务（21×3，600秒），不恢复昨天420题队列；元宝设置21×5/45秒，旧未知记录不能重发或清除。

**2026-10-16 09:21 用户要求移除面板夸克：** 已在本地服务器192.168.31.106部署前端 `monitor-dashboard:no-quark-20261016`（同时更新local标签），移除侧栏、模型卡片、产品表列及旧控制区夸克展示；历史数据库与接收接口保留。仅monitor-dashboard按用户要求重建，其他10个运行容器启动时间/镜像均未变化，未修改采集批次、队列或原12h指针/截止。不要再宣称包括前端在内的全部容器从长测起始未重启，也不要把这次已知前端更新当未知漂移。预览/正式3000及手机布局、六通道/创作读取验证通过；恢复包39/39映射SHA重新核对一致。证据：[本轮报告](geo-monitor-deploy/maintenance/20261016-no-quark/REPORT.md)。

**08:20优先覆盖旧状态：** 豆包1第761题08:00:23.771一次点击，08:15:26.770因原请求900秒仍waiting进入needs_attention；08:19原生106字/原身份/hash与08:10一致，finish=false，未重发或点击重新生成。原任务/原生库/事件/UI备份服务器pending-doubao1/，脱敏doubao1-pending-audit.json。此前760文字processed保真保留，片段不算成功或负样本；现在4处阻塞（豆包1/豆包2/元宝/DS），仅文心与百度继续，原12h ID/09:48:05不变，不称六通道连续通过。旧08:10段首次点击时刻已按epoch更正为08:00:23，无队列修改/清缓存/重启。新增阻塞通知一次后相同状态安静。

**08:10优先：** SSH本轮恢复，原12h监督/截止定时器active、采样新鲜，原09:48:05不变；08:04客户端访问缺口证据保留。豆包1第761题08:00:23一次点击，08:10原生首问/答案确认但正文106字finish=false，仍原900秒等待（08:15:23截止），已备份原任务/原生库/UI，无重发或按钮操作；下轮只读核验，片段不算正文或负样本。此前760文字与PG保真通过，文心293/百度270观测56唯一保真通过。百度unavailable32=30卡片不完整+2DNS，新第15轮1题DNS失败单列；原三处阻塞不变，不称六通道连续通过。

**08:04轮优先注意：** 本轮SSH有限三轮连接尝试失败（TCP超时，末轮密钥交换No existing session），独立22端口可达；当前服务器/采集状态未取得新证据，不能宣称崩溃或通过。最后成功实时审计为07:59轮，原rowidfix12h/09:48:05不变、原独立定时器按已验证配置收尾，下轮只读核验。无远端改动/重发/重启；本地可靠性报告已记录访问缺口，尚未同步服务器。

**06:05最新：** 豆包1第652题同类已完成错误后，新CID重试1次已完成528字/11来源；累计failed_attempts=6、重复点击任务=6（576/608/612/629/631/652），原失败及点击事实保留，653文字processed/PG全字段保真、待回传0。百度unavailable25=24卡片不完整+1历史DNS，不当正文成功或负样本。原三处阻塞、12h ID/09:48:05不变，无手动补发/改队列/重启；相同恢复不反复通知。

**05:45最新：** 豆包1第631题新CID重试已完成486字/11来源，原生身份/首问/完成标记一致；failed_attempts=5、重复点击任务=5（576/608/612/629/631），均获成功正文，全部原失败及两次点击事实保留。累计635文字processed/PG全字段保真、待回传0。原三处阻塞、12h ID与09:48:05不变，无手动补发，不能称零失败或每题一次点击。

**05:40最新：** 豆包1第629题新CID重试完成410字/12来源；累计630文字processed与PG全字段保真、待回传0。第631题首次同类已完成错误答复已归档，05:39:46快照prepared/sending_once、尚未见第二次点击或成功正文，下一轮核实际后续。failed_attempts累计5，已有两次点击任务4题（576/608/612/629）；保留全部失败，不能称零失败/每题一次点击。三处阻塞与原12h ID/09:48:05不变，无手动补发。

**05:35最新计数：** 豆包1第629题同类已完成错误答复已归档，failed_attempts累计4；05:35:01仍在既有90秒退避后pending，只有一次点击，不能提前称恢复。已有两次点击任务仍3题（576/608/612），此前628文字processed与PG保真通过、待回传0。下一轮只读核对629实际后续，不手动补发；三处阻塞、原12h ID及09:48:05不变。

**05:17计数更新：** 豆包1同类已完成错误答复后重试累计3题（576、608、612），每题新CID重试1次；612重试后569字/12来源，累计612文字processed与PG全字段保真通过、待回传0。失败3条和各题两次点击均保留，不能称零失败/每题一次点击；详见可靠性报告及原脱敏审计。原三处阻塞、12h ID与09:48:05截止不变，同类恢复事件不反复通知。

**05:11计数更新：** 豆包1同类已完成错误答复后重试累计2题（576、608），各在新CID重试1次；608重试后511字/12来源完整采集。两次失败及各题两次点击均保留，详见可靠性报告最新首段及原脱敏审计；三处阻塞/12h截止不变。相同恢复事件不反复通知。

**04:36新增交接：** 豆包1第576题首次返回原生已完成错误答复“出了点问题，请稍后重试。”，既有worker归档失败、90秒退避后在新CID重试一次，得到536字/12来源并processed。两次点击、两套request/answer/CID及失败记录均保留；不称每题一次点击或零失败，也不把首次错误当成功或负样本。supervisor的duplicate_request_or_conversation标记保留，后续须结合证据解释，不能当未知发送重试或抹除异常。详情见可靠性报告最新首段及 [脱敏审计](geo-monitor-deploy/maintenance/20261015-reliability/doubao1-transient-retry-audit.json)。原三处阻塞/12h截止不变，本事件已通知一次；下方01:12创作完成结果不变。

更新时间：**2026-10-16 01:12，北京时间**。采集表动态计数仍为00:39:42左右快照，后续会变化；创作6h最终结果已更新。本文用于新Codex对话接手，不能代替服务器实时状态。

最新：**创作6h已完成并向用户报告一次**，实际21609.294秒、passed，9基线＋1窗口新增，共10篇全部证据验证通过；原job已由独立deadline暂停，API/worker继续运行。[创作最终报告](geo-monitor-deploy/reports/20261015/creation-6h-final/REPORT.md)。12h采集仍至09:48:05，三处阻塞仍保留，heartbeat继续，不重复报告创作结果。

## 1. 接手先读与当前结论

工作区：`C:/Users/78567/Desktop/隐身浏览器`。服务器：`192.168.31.106`。服务器系统时间显示UTC，业务时间统一按北京时间UTC+8理解。

先读本文，再读以下两个文件的**最新首段**，最后核实服务器两个当前指针：

1. [可靠性现场报告](geo-monitor-deploy/maintenance/20261015-reliability/REPORT.md)
2. [统一升级工作记录](geo-monitor-deploy/maintenance/20261015-unified/WORKLOG.md)
3. `/opt/monitor/geo-capture/soak12h_current.json`
4. `/opt/monitor/geo-capture/creation_soak_current.json`

**当前结论：系统已整合上线，但六通道12小时稳定性没有通过。** 豆包1、文心卡片、百度卡片继续采集；豆包2、元宝、DeepSeek分别有明确阻塞。创作6小时观察已完成并报告，窗口内只新增1篇，其余是idle期间可用性和证据检查；12h最终报告尚未发出。

历史`PROJECT_HANDOFF.md`、各README及旧报告含大量旧批次、旧版本、旧截止时间。旧文档中“5通道”“10容器”“元宝未登录”“不恢复Redroid”“07:19/08:19截止”等不代表当前状态。后来的GEO三原生采集已经得到授权；原独立内容工作台的抓取调度仍保持暂停，不能混为一谈。

## 2. 整个项目要做什么

目标是：多平台真实提问与回答采集 → 完整正文/全部引用信源入库 → GEO产品分析与信源正文抓取 → 使用有出处的完整素材研究、写作、独立审稿 → 生成可追溯的Markdown与Word，在统一面板操作。暂不自动发布文章。

业务分为四部分：

| 部分 | 当前职责与位置 |
| --- | --- |
| GEO核心 | `/opt/monitor`：接收器、PostgreSQL、产品分析、信源正文抓取、分析API、大面板 |
| GEO六采集通道 | 豆包1/2 Android、元宝Android、DeepSeek网页、文心卡片、百度卡片；统一任务/暂停/回传控制在`/opt/monitor/geo-capture` |
| GEO新创作 | `/opt/monitor/geo-content`：复用原研究/写作/审稿/Word/预算引擎，只取GEO已有素材，不另启平台抓取 |
| 原内容工作台 | `/home/user/geo-editorial/runtime-api`与Windows桌面程序；保留服务、历史成品、登录与共享账本，原抓取调度保持暂停 |

六通道是采集来源，数据库的统计模型分类未必一一对应：例如文心卡片与百度卡片可能同归`wenxin`，双豆包也要靠设备/批次区分。必须保留原始capture_mode、batch和设备信息。

`processed`只代表接收入库；产品分析完成看`ai_verified`，`ai_pending`单列；信源媒体正文抓取也有独立成功/失败/质量状态。三者不能互相替代。

## 3. 使用入口、架构和服务

入口：

- 公网大面板：<https://1any.top/geo_monitor/>
- 六通道控制：<https://1any.top/geo_monitor/#capture/doubao1>
- GEO创作：<https://1any.top/geo_monitor/#creation>
- 内网同功能：`http://192.168.31.106:3000/`
- 独立采集控制台：`http://192.168.31.106:8803/`
- 原桌面工作台：工作区`启动内容工作台.cmd`，程序`deliverables/ContentWorkspace/ContentWorkspace.exe`

沿用原网站登录。公网经VPS的鉴权Nginx、原SSH隧道进入LAN；前端必须支持`/geo_monitor/`子路径。控制与创作网关有独立cookie、CSRF/Origin、防重复操作ID、离线禁写和丢响应同ID核对重试。修改前后端后要复验正式公网，不能只测内网。

| 组件 | 服务/容器与主要位置 |
| --- | --- |
| 前端 | `monitor-dashboard`，3000；生产`/opt/monitor/yuanbao_monitor/dashboard` |
| 分析API | `monitor-dashboard-api`，8765；主源码`/opt/monitor/doubao_dashboard_server.py` |
| 豆包接收 | `monitor-doubao-receiver`，8790 |
| 多模型/元宝接收 | `monitor-result-receiver`，8791 |
| 产品分析 | `monitor-product-worker` |
| 媒体完整正文抓取 | `monitor-content-worker`，`/opt/monitor/doubao_source_content.db` |
| 数据库 | `monitor-postgres`、`monitor-redis` |
| 采集控制API | `geo-monitor-status.service`，8803；`/opt/monitor/geo-capture/panel/control.sqlite` |
| 原生当前任务 | `geo-native@批次ID.service`；代码`/home/user/redroid-doubao/geo-batch-code/` |
| 网页当前任务 | `geo-web@批次ID.service`；GEO独立venv与batch目录 |
| 创作API/执行器 | `geo-content-api.service`（127.0.0.1:8804）、`geo-content-worker.service` |
| 公网隧道 | `monitor-vps2-tunnel.service`，原13000→LAN3000、18765→LAN8765 |
| 元宝登录兼容 | `geo-yuanbao-wechat-qr-compat.service`，保持运行，不改登录/ART兼容层 |

本次只读核实：**11个运行容器＝8个GEO核心＋3个Android**。上述控制、创作、隧道、元宝兼容服务active；核心与Android未因本轮只读检查重启。

Compose：`/opt/monitor/deploy/local-server/docker-compose.yml`，项目名`local-server`。不要为修单个采集器运行整栈down、prune或批量重启。

三个Android均为Android13/Houdini14：

| 通道 | 容器 | 服务器回环ADB |
| --- | --- | --- |
| 豆包1 | `doubao-hpe14-13-test` | 5557 |
| 豆包2 | `doubao-hpe14-account2` | 5558 |
| 元宝 | `yuanbao-hpe14-android13` | 5559（Windows转发15559） |

豆包官方App15.2.0，versionCode15020040；元宝2.88.0，versionCode66517035，包`com.tencent.hunyuan.app.chat`。数据卷和登录独立。**元宝投屏保持关闭。**

## 4. 两项正在进行的长测：这是最优先的接手任务

### 六通道12小时

- 当前ID：`question-only-soak12h-rowidfix-1792072084`
- 起点：**2026-10-15 21:48:04.675**；截止：**2026-10-16 09:48:05**，43200秒。
- 指针：`/opt/monitor/geo-capture/soak12h_current.json`
- root：`/opt/monitor/geo-capture/soak/question-only-soak12h-rowidfix-1792072084`
- supervisor：`geo-question-only-soak12h-rowidfix-1792072084.service`
- 独立截止timer：`geo-question-only-soak12h-rowidfix-1792072084-deadline.timer`

六批次仍是10月15日18:18创建的原任务，**不能重新创建或重跑**：

| 通道 | 原批次ID | 00:39累计processed | 当前窗口新增完整采集/processed/唯一保真回执 |
| --- | --- | ---: | --- |
| 豆包1 | `geo-panel-doubao1-20261015-181820-3d82b024` | 351 | 162 / 162 / 162 |
| 豆包2 | `geo-panel-doubao2-20261015-181821-6fa7c803` | 310 | 110 / 110 / 110 |
| 元宝 | `geo-panel-yuanbao-20261015-181821-d56b0d20` | 320文字 | 102 / 102 / 102；另1条历史非文字审计 |
| DeepSeek | `geo-panel-deepseek-20261015-181821-879aca5d` | 21 | 1 / 1 / 1，登录阻塞 |
| 文心卡片 | `geo-panel-wenxin-card-20261015-181822-d5a69c59` | 134 | 61 / 61 / 61 |
| 百度卡片 | `geo-panel-baidu-ai-20261015-181822-d44632b8` | 132完整观测，32唯一入库 | 窗口55完整观测、6唯一、49去重 |

这是动态快照，审计取样之间有时间差。以实时manifest/status/metrics/verified/report为准。`new_captured_after_upgrade`用的是19:44升级基线，**不能拿它当21:48当前窗口新增**；使用`current_window_counts`/probe的`window_counts`。carry-in开始前已采集待回执须单列，不能用批次累计冒充窗口实采。

此前18:18、18:53、19:19 fencefix、19:45 reliability、20:19 videofix等短窗口均归档`interrupted`，旧timer已关闭。不能拼接时长或按旧07:19、07:45、08:19截止操作。

**本轮已出现三个通道阻塞，不能宣称六通道连续12小时实采通过。** 继续记录真实时长、其他通道进度、异常与保护暂停，不为了“通过”重置窗口或删除异常。

### 创作6小时

- 当前ID：`creation-soak6h-rosterfix-1792062355`
- **2026-10-15 19:05:55.845 → 2026-10-16 01:05:56**，21600秒。
- 指针：`/opt/monitor/geo-capture/creation_soak_current.json`
- root：`/opt/monitor/geo-capture/soak/creation-soak6h-rosterfix-1792062355`
- supervisor：`geo-creation-soak6h-rosterfix-1792062355.service`
- timer：`geo-creation-soak6h-rosterfix-1792062355-deadline.timer`
- 原付费job：`creation-1792060761-3c2baae0`，固定队列10篇已通过；基线9篇，第10篇才是本窗口新增，其后worker为idle。
- 另一个验收job：`creation-1792060415-1e4e3a8d`，2篇不计新增；原内容项目历史82篇也不计新增。
- 10篇Markdown/Word/receipt哈希、独立审稿、完整媒体正文和GEO出处反复审计通过，未知API调用0。
- 00:39只读共享账本：原job48次settled调用保守估算**0.536386元**；窗口内1次收尾调用**0.013517元**，未结算预留/未知用量0。**估算不是服务商账单**。
- 原共享预算单篇0.35元、每日10元，不能提高、重置或另开账本；不为保持忙碌额外付费生成。

到期读取真实report及独立deadline marker，允许当前API/题目和回执收尾，不强杀。只排空manifest所属且仍属于当前测试的任务，不影响用户后来新任务。最终报告保存到`geo-monitor-deploy/reports/20261015/`，分列实际新增、idle与费用；不得称6小时持续付费生成。

## 5. 三个当前阻塞：不能盲目恢复

### A. 豆包2第311题：原答案确实未完整结束

- task：`23c5d97d-f843-562c-82e5-c22a6b55b855`，问题“推荐一款爽肤水”。
- 23:36:15一次发送点击，原生首问server_index1/答案2；正文135字，正文块`is_finish=false`。
- 23:49页面实际显示“消息加载失败”。已备份原任务SQLite和原生SQLite，正常打开既有历史会话回查，正文hash及原请求/答案/CID不变，完成标记仍false。
- 页面重新出现“重新生成”不等于原答案完整。900秒后原worker保护停`needs_attention`，该条未作为成功正文入库。
- 保留此前310条processed。没有点击重试/重新生成、没有清缓存/修改完成标记/重发/重启Android。
- 本地证据：[doubao2-pending-audit.json](geo-monitor-deploy/maintenance/20261015-reliability/doubao2-pending-audit.json)；服务器`maintenance/20261015-reliability/pending-doubao2/`。
- 只能在严格证明原请求已完整结束后考虑恢复；不能为放行写入135字片段或补发。

### B. 元宝第322题：同原始请求ID出现两组服务端问答

- task：`2d668639-8b1c-5a6b-955b-566220026fea`；问题“推荐一款祛痘精华液”；CID`0RGfLig07CS`。
- 采集器发送点击1次，完整服务端历史有index1/2与3/4两组相同问答，均回显同一个原始client request ID。
- 第一答1412字/19来源；第二答1699字/48来源。两次完整SQLite读取稳定。
- serverIndex3是第二条用户消息，不是第三条；一次点击不能据此声称服务端只生成了一次。内部重复原因未证实。
- 当前DTMP只读接口只暴露第二组；首问门禁拒绝，900秒保护停。两组均未写任务result/outbox/回执，未计成功或负样本。
- 本地证据：[yuanbao-duplicate-request-audit.json](geo-monitor-deploy/maintenance/20261015-reliability/yuanbao-duplicate-request-audit.json)；服务器`maintenance/20261015-reliability/yuanbao-ack/`保存原队列、基线、原生/render快照、加载前后SQLite和四消息完整历史。
- 可继续只读研究如何严格选定原index1/2及其完整正文/所有来源，但不能把第二组当首问，不能直接换未经验证的parser或重发后覆盖。
- `native_models.js`的`readKnown(cid,messageId)`当前实际上先取当前last；不能假定传入旧messageId就一定读到旧答案。现有Python身份校验会拒绝不一致，不能去掉。

### C. DeepSeek网页登录失效

- 下一题发送前check_ready进入`waiting_login`；21completed/processed、399pending，当前窗口只新增1条。
- 已只读验证GEO9514和原工作台9414两个原profile，均官方`chat.deepseek.com/sign_in`、页面complete且Log in可见，连续两次一致，确认真实授权失效。
- 用户已收到一次“在原内容工作台完成登录后告知”的通知。**相同阻塞不重复探测原profile、不同步失效登录、不反复提醒**；收到用户登录完成或确证变化后再校验同步并恢复原任务。
- 没有未知题发送或待回执；网页登录失效与DeepSeek付费API创作是两回事。
- 证据：[deepseek-auth-audit.json](geo-monitor-deploy/maintenance/20261015-reliability/deepseek-auth-audit.json)。

## 6. 采集与分析的关键要求

1. 每题新会话/新页面，发送内容严格只有原问题；任务UUID只在本地，不附加提示词。
2. 必须核原生问题/答案/CID身份、平台完成标记、全部正文段落、全部信源与引用。EOF后两次相隔至少2秒稳定快照才提交。
3. 不能按字数短就判截断，也不能按字数长/末尾标点/有重新生成按钮就判完成。
4. 原始结果→冻结outbox→processed回执→PG逐条保真；正文、来源、引用、搜索词（平台真实暴露时）均核对。元宝未暴露搜索词，记录`search_queries_exposed=false`，不能编造。
5. 网络读取30秒、最多5次只读重连；发送未知绝不盲目重发。原请求900秒限时保护。
6. 回传同冻结RID持久化退避，5秒指数至300秒，尊重Retry-After；先核GET回执，不能重新生成新RID规避防重。积压时不开始下一题。
7. 百度完整观测、唯一processed、重复观测、`supplement_unavailable`分列。不要求每次搜索都有AI卡片，不把卡片不完整当完整正文/负样本，不拿文心内容替代。
8. 当前百度累计12条不可用：11条卡片未完整呈现、1条早前DNS失败；旧DNS记录保留，后续已恢复。新不可用仍要读具体原因。
9. 元宝原第120题纯视频已修复并单列`completed_nontext`：两组7视频资源卡经独立审计outbox/receipt进入PG raw事件，预期quarantined、stored_run_id空、answer/body/source_complete=false。不是文字成功或产品负样本，不编造转写/微信链接。
10. `ai_pending`不作负样本，信源抓取失败/受限/低质量不冒充完整可用素材。最新全量语义相关审计快照是795条正文、5873条产品证据无差异；这不是“模型语义永远正确”的保证。

用户曾追问豆包正文是否有错：23:08按实时SQLite和持久绑定复查两台各5条processed记录，正文/所有段落/来源/引用/搜索词、outbox、PG raw及monitor_runs.answer均一致，10条420–618字、9–12来源，未发现截断/漏段/串题。证据[recent-doubao-body-audit.json](geo-monitor-deploy/maintenance/20261015-reliability/recent-doubao-body-audit.json)。这个结论只针对已核样本的采集保真，不保证推荐功效事实，也不包括上述未完成311题。面板对豆包原文不裁切；canonical问题分类标签与原发问字符串可不同，不能误报成串题。

## 7. 已部署修复与验证边界

- 纯问题协议：首问与CID绑定、临时CID转正、唯一会话账本；三原生各3真实新会话/processed/保真验收。
- 网页轮序按round/ordinal，观测完成后再起间隔屏障；保留整批次旧58.87秒失败，窗口间隔独立计算。
- 150秒worker健康租期匹配75秒ready上限；暂停等待每3秒检查，已发送题收尾。
- 原生EOF双快照、元宝实体/来源短暂不同步限时复核、只读重连、持久回传退避、网页背压。
- DeepSeek保留短段，独立识别alert/toast，不把正文中的“服务繁忙”当系统报错。
- 面板离线禁写、丢响应同操作ID重试；公网鉴权、CSRF/Origin、移动端与Word字节验证通过。
- 元宝原第120题videoBoxV2/Stream最终render先于parse读取；103项回归通过；正文与非文字审计严格分离。
- 豆包原第188题旧167历史消息重新插入导致rowid越基线误判：同一只读事务冻结原消息身份指纹，仅忽略严格相同旧身份，真旧会话新增消息仍硬失败；原188题无重发恢复，后续两台各3条processed/保真。9项question_only回归（其中新增3项），不要说成全套106项重跑。
- 创作名单解析修复bullet/category误认产品，保留事实与来源门槛，原第10篇定向修订后通过。
- 分析缓存先验DB版本，面板显示原始全文、全局采集记录编号；不混淆模型分析清理文本与原文。

最新修复证据：`maintenance/20261015-reliability/video-fix/`、`history-row-fix/`。19:45的95项、20:24的103项、21:50的9项关联回归是不同范围，不能累加虚报成一次全量测试。

## 8. 创作内容与费用的长期规则

- 标题、痛点、正文、产品名单和产品介绍必须基于该采集批次已有完整信源原文；“当天”指批次日期，不是媒体发表日。历史材料不能标成今日新采集。
- 自有产品：科熙本二硫化硒清爽去屑止痒洗发水；事实只取approved品牌知识，不移植竞品功效。资料入口`outputs/product-knowledge/kexiben/`。
- 排行类：先导语/选择标准，自有产品列产品推荐第一位，不要求文章第一句话就是广告；保留有原文依据的其他产品。
- 科普类：沿原知识主题展开，相关段落自然举例，不改造成独立榜单广告。
- 类别保持排行类/科普类，允许细分体裁与主题标签；不确定内容保留needs_review。
- 不伪造亲测、权威榜单、实验数据。原文宣称不等于我们核实。
- 当前字数合同：排行目标3000–3800汉字、最低2800；科普2600–3200、最低2400；不靠套话凑数。
- Word保留真实段落、清晰标题及连续产品编号；溯源另存，不在成品末尾堆内部清单。
- GEO创作只读PG和`doubao_source_content.db`的完整content_text，按长度/SHA/GEO provenance验证，不取excerpt替代全文。
- 引擎为`/opt/monitor/geo-content/engine/geo_source_cards`固定快照；原内容项目安装包不盲改。共享原账本`/home/user/geo-editorial/runtime-api/api/costs.sqlite`。
- 已知已回执的质量失败才允许原引擎有限定向修订；未知付费发送不重试，不降门槛，不自动发布。

## 9. 本地源码、数据、恢复包

| 路径 | 用途 |
| --- | --- |
| `geo-monitor-deploy/dashboard-integration/app/` | 当前大面板前端、六通道/创作网关 |
| `geo-monitor-deploy/{control_panel.py,fleet_status.py,panel.html,capture_bridge.py}` | 控制、状态、网页回传 |
| `geo-monitor-deploy/{all_channel_soak.py,native_soak.py}` | 采集长测与审计 |
| `geo-monitor-deploy/creation/` | GEO创作适配、任务、worker、API、面板、6h记录器 |
| `geo-monitor-deploy/server-source/` | 主后端非配置源码快照；不是完整生产镜像 |
| `redroid-deploy/question_only_*.py` | 当前三原生纯问题队列/关联/worker/回传 |
| `yuanbao-deploy/{android_ui.py,native_core.py,native_client.py,native_models.js,delivery.py}` | 元宝正常UI发送、只读原生读取、严格解析与回传 |
| `geo-source-card-collectors/` | 网页采集与原内容引擎源码；生产各自使用独立venv和运行目录 |
| `geo-monitor-deploy/maintenance/20261015-reliability/` | 当前现场报告、诊断、只读工具与最新脱敏live-validation |
| `geo-monitor-deploy/maintenance/20261015-unified/` | 整合工作记录、费用审计、打包工具及分阶段证据 |
| `geo-monitor-deploy/reports/20261015/` | 正式报告导出位置；长测完成报告仍待到期生成 |
| `outputs/api-editorial/articles/` | Windows同步成品与证据，保留 |
| `deliverables/ContentWorkspace/` | 原桌面程序与必需运行库，不能当缓存删 |
| `redroid/`、`Scrapling/` | 上游仓库，保留.git和本地修改 |
| `doubao-headless-technical-docs/` | 独立技术文档及旧快照，不能当当前生产源码 |
| `references/wenxin-baidu-collector/` | 只读参考仓库，不直接启动其supervisor |
| `ecommerce-review-exporter/` | 独立电商评论工具，本轮无关，保留 |

原生运行：豆包`/home/user/redroid-doubao/batches/批次/`；元宝`/home/user/redroid-yuanbao/batches/批次/`。原生venv：`/home/user/redroid-doubao/worker-venv/bin/python`。网页venv：`/opt/monitor/geo-capture/venv/bin/python`。

当前恢复包：`geo-monitor-deploy/releases/20261015/unified-current/{source.zip,manifest.json,README.md}`。**00:39重新核对39/39服务器映射SHA一致**。只含本轮变更模块，不含私密配置、数据、登录或完整旧引擎，不是盲安装包。`native_models.js`等未必列入现有39映射；修改任何额外模块必须补清单，不能凭“39匹配”断言整个服务器所有文件一致。

前端Docker当前运行tag显示`monitor-dashboard:local`，现有创作发布版本tag为`monitor-dashboard:creation-20261015`；回退tag`monitor-dashboard:before-creation-1792060830`，备份`/opt/monitor/geo-capture/backups/creation-frontend-1792060830`。回退只针对组件文件/镜像，不回滚队列数据库抹掉后续采集。

历史清理/重启已完成并留证据；当前任务不是继续清理。不能把数据库、Android卷、登录、outbox/receipt、Word成品或唯一失败现场当缓存。

## 10. 新对话可以立即执行的只读检查

SSH统一复用`redroid-deploy/remote.py`，读取现有私有配置；**不输出凭据，不把密码写入命令**。PowerShell工作区中运行：

```powershell
python -X utf8 -B redroid-deploy/remote.py 'python3 -B /tmp/probe_reliability_heartbeat.py' --sudo --timeout 45
python -X utf8 -B redroid-deploy/remote.py 'python3 -B /tmp/validate_reliability_live.py' --sudo --timeout 150
python -X utf8 -B redroid-deploy/remote.py 'python3 -B /tmp/current_summary.py' --sudo --timeout 45
python -X utf8 -B redroid-deploy/remote.py 'python3 -B /tmp/audit_creation_costs.py' --sudo --timeout 45
python -X utf8 -B redroid-deploy/remote.py 'python3 -B /tmp/check_release_mapping.py' --sudo --timeout 45
```

主probe读两指针、manifest/status/metrics/verified/report与supervisor/timer。live_validation逐模型核已完成正文/来源/引用/原始结果至PG、重复发送、间隔、创作哈希/Word/审稿/材料出处、核心容器基线；已完成保真与operational_blockers分开，不能把`failures=[]`当成六通道运行正常。

脱敏live报告下载：

```powershell
python -X utf8 -B redroid-deploy/remote.py --download /tmp/geo-reliability-export/live-validation.json geo-monitor-deploy/maintenance/20261015-reliability/live-validation.json
```

其他只读工具：`/tmp/validate_history_fix.py`、`/tmp/validate_yuanbao_video_fix.py`、`/tmp/audit_recent_doubao_body.py`、`/tmp/inspect_reliability_unavailable.py`。专项工具是固定旧任务核查，不当通用恢复器。`/tmp/inspect_doubao_pending.py doubao2`会读取并保存原现场，不发送；相同阻塞不需每轮重复UI探测。

**禁止重跑**：`/tmp/recover_yuanbao_video_only.py`、`/tmp/recover_doubao_history_row.py`、`/tmp/retest_history_window.py`、`/tmp/retest_video_window.py`、`/tmp/deploy_reliability.py`及历史安装/重测脚本。它们是已完成的现场一次性操作，不是日常入口。

## 11. 自动跟进与对话并行边界

- automation ID：`automation`，名称“GEO十二小时采集与创作验收”，**ACTIVE，每5分钟**。
- 绑定当前旧线程：`01a13907-a740-75b2-b266-96bd70ff0fbf`。
- `geo`（一小时长测）与`10`（旧创作汇报）均PAUSED，保持。
- 配置：`C:/Users/78567/.codex/automations/automation/automation.toml`。如需变更，先读最新并通过automation工具更新，保留其他字段；不要直接手写配置覆盖。
- 两项长测各完成并向用户报告一次之后，才暂停本heartbeat；一项完成不能提前停另一项监测。
- 无变化保持安静，只通知确认的新故障、需要用户操作或完成；三个当前阻塞均已通知，不反复提醒。
- 用户新开对话**不会自动迁移旧heartbeat**。新对话先检查现有自动化，别再建重复监测；避免新旧两线程同时恢复同一批次或修改同一原请求。没有用户进一步授权，不自动改heartbeat绑定或给其他线程发消息。

## 12. 下一步优先顺序

1. 核对两个实时指针和状态，接管观察；如接手时已到期，读实际report、独立deadline marker和排空状态，不能由预计时间直接宣布完成。
2. 创作6h已完成并报告，最终证据在`geo-monitor-deploy/reports/20261015/creation-6h-final/`，无需重复汇报或再启动收费任务；原job保持deadline暂停。
3. 继续豆包1/文心/百度与原12h记录；对三个阻塞保留原因与时长，09:48:05按原任务安全收尾，报告实际结论，不伪称六通道通过。
4. DeepSeek等用户完成原工作台登录后再同步校验；豆包2只核原请求是否完整；元宝只研究原首问第一答的严格读取，任何未知发送不重试。
5. 如后续修复需部署：先保留现场，限制组件范围，真实故障回归+正式公网复验，更新源码映射/文档/自动化；是否重开新的完整版本观察窗口必须如实标记旧窗口interrupted，不能覆盖旧异常。

**用户要求本次写交接，没有要求停止服务器、当前任务、服务或自动化。本文编写没有新增收费任务、没有修改运行队列、没有重启服务。**

## 可直接粘贴到新Codex对话

```text
工作区 C:/Users/78567/Desktop/隐身浏览器。请先完整阅读根目录 CURRENT_PROJECT_HANDOFF.md，再读 geo-monitor-deploy/maintenance/20261015-reliability/REPORT.md 和 geo-monitor-deploy/maintenance/20261015-unified/WORKLOG.md 的最新首段，使用 redroid-deploy/remote.py 只读核实服务器192.168.31.106两个实时长测指针和原任务状态，再继续已授权工作。
优先跟进原12h rowidfix测试（2026-10-16 09:48:05截止）与原6h创作（01:05:56截止），若已到期读取真实报告和deadline marker。三个已知阻塞为豆包2第311题135字未完成、元宝第322题同请求ID两组问答、DeepSeek真实登录失效，均不得盲目重发/清缓存/重启或放宽完整性门禁。每题新会话，只发原问题。原六批次和付费10篇队列不重建，历史105/105与116/119不重跑，预算不提高，元宝投屏关闭，不自动发布，不恢复原内容工作台抓取调度。
现有heartbeat automation仍绑定旧线程且ACTIVE，每5分钟跟进，geo和10保持PAUSED；不要另建重复监测或让两线程同时写同批次。先读最新自动化状态，不擅自迁移。两项各完成并报告一次后才停本heartbeat。无变化保持安静，所有结论区分批次累计、当前窗口新增、carry-in、唯一processed、非文字审计、百度不可用及idle；不能把当前窗口称六通道12h连续通过。不要运行交接中列出的已完成一次性恢复/安装脚本，不输出凭据。
```
