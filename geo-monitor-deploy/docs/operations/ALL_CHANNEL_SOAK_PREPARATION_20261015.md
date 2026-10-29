# 全通道长测准备状态

用户授权DeepSeek、元宝、两个豆包、文心、百度一起真实采集长测。2026-10-15本轮准备时按上一轮2小时提供默认选项；实际启动前创建独立测试身份，记录真实开始／截止，不把准备时间算入通过时长。

## 当前证据

- DeepSeek：用户已在本机专用Chrome登录，成功同步到服务器原内容工作台及独立GEO profile；`reports/20261015/deepseek-manual-login.json`记录`source_ready=true / geo_ready=true`。同步通过既有SSH加密stdin传递，未记录cookie／token值，未发送问题。内容工作台原暂停标记保持，未自动启动付费写作。
- 元宝：用户已完成微信授权和手机官方身份校验，投屏已按要求关闭。DTMP原生读取已完成连续3题验收：5041字正文、97条全部信源、24处引用，3个新会话，processed与数据库保真全部通过；最小发送间隔52.8秒。已接入六通道控制后台、内网大面板与真实HTTPS子路径，原21题5轮验收批次继续无头运行。接口未暴露搜索词，明确记录未暴露，不伪造。详见[元宝状态](../../../yuanbao-deploy/README.md)。
- 豆包1／2：模拟器在线，当前两小时批次仍暂停116／119；原两个105／105批次保留。不能把继续旧测试当作新的共同长测。
- 文心：现有批次126／126 complete。
- 百度：现有批次已完成105个观测，其中92条完整processed、30唯一、62去重、13不可用；不得把不可用观测算作完整回答。

## 启动门禁与约束

元宝登录与原生结果适配已通过。启动全通道同步长测前已建立独立测试身份、截止排空保护，实时复核其余通道登录／队列状态；单独的元宝验收批次不算全通道长测。

六个采集通道均就绪后，使用原21题；采用独立测试批次及足够覆盖测试窗口的轮数容量，面板原默认设置保存并恢复。DeepSeek最低300秒，豆包／元宝最低30秒，百度／文心最低60秒；保持各自发送防重与原网页串行资源约束。每题新会话／页面，完整数据进入持久outbox，同一请求身份重试回传并核对processed。

记录每通道真实首发、间隔、原始结果及完整正文／信源／引用／搜索词保真、唯一入库／去重、错误、容器与服务重启。截止只对本测试批次请求排空暂停，等待当前题与回执收尾，不影响后续用户批次。不清缓存／队列，不重发未知发送，不重跑历史完成批次。

## 已实际启动

`all-channel-soak2h-1792056244`，北京时间2026-10-15 17:24:53.95开始，19:24:53.95截止请求排空。指针 `/opt/monitor/geo-capture/all_channel_soak_current.json`，目录 `soak/all-channel-soak2h-1792056244`，supervisor `geo-all-channel-soak2h-1792056244.service`，独立timer `geo-all-channel-soak2h-1792056244-deadline.timer`。原问题、轮数和间隔快照在manifest；20轮只是容量，面板默认已恢复。最终结论须来自真实report／metrics／verified，不能由预计截止推定通过。

| 通道 | 新测试批次 |
|---|---|
| 豆包1 | geo-panel-doubao1-20261015-172454-e5bec1f9 |
| 豆包2 | geo-panel-doubao2-20261015-172455-301bb730 |
| 元宝 | geo-panel-yuanbao-20261015-172455-b45ba5d3 |
| DeepSeek | geo-panel-deepseek-20261015-172455-856bd963 |
| 文心卡片 | geo-panel-wenxin-card-20261015-172456-6bcd4c30 |
| 百度卡片 | geo-panel-baidu-ai-20261015-172457-03cf4503 |

启动故障必须保留：记录器误假定所有原生队列都有可选`failed_attempts`归档表，导致最初采样OperationalError，已修复并补测试；`metrics.jsonl`原样保留。两台豆包的Android重复通知弹窗只有`permission_deny_and_dont_ask_again_button`，旧worker仅识别`permission_deny_button`，导致发送前准备失败。已兼容两个拒绝按钮，只针对确认为豆包通知权限的提示，不处理其他权限；服务器44项测试全部通过。确认两道首题没有发送意图／点击／原生请求后，备份SQLite并记录恢复事件，继续同一批次，未重发未知请求。随后两个豆包均已取得processed。证据`notification_preflight_recovery.json`及私有diagnostics。豆包1后来出现UI传输关闭／准备超时，phase-v2证明未点击后由既有有界机制恢复，已获得首条processed；这仍是长测中的异常，不抹去或称从头无故障。

元宝验收旧批次完整15题已排空保留。六通道测试到期仅暂停manifest列出的批次，若用户新建任务则跳过，不强杀、不重置队列。每15分钟heartbeat复核并只在故障／需要操作／完成时通知；既有网页一小时heartbeat及10保持暂停。尚无全通道两小时通过结论。

记录器随后补齐原豆包旧回执与通用回执的协议差异：旧协议的正文完成依据是冻结payload中的`body_capture_complete`、原生`finished`与`complete`，保存ID位于`save.run_id`；通用协议使用analysis完成字段及`stored_run_id`。两者均继续校验完整信源标志、请求身份、正文／信源数量与PostgreSQL字段保真。原ValueError采样记录保留，6项记录器测试通过，六通道真实回执均已通过适配后的审计。独立定时器向上取整到19:24:54，避免截断亚秒导致不足7200秒。
