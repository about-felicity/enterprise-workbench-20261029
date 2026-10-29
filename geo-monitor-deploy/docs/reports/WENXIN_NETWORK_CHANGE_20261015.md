# 文心一小时长测中的导航故障与恢复

北京时间2026-10-15 10:41:28，文心原批次 `geo-wenxin_card-21x6-20261015` 在39条完成并全部processed后，第40个观测遇到异常停止。10:54 heartbeat发现，10:57:36备份并修复，继续原批次；当前一小时长测必须保留这次中断，不能认定连续一小时通过。

直接错误：`Page.goto: net::ERR_NETWORK_CHANGED at https://www.baidu.com/`。已核对实际调用栈及代码：`collect_wenxin_search()` 在 controller.py:833 导航到首页失败，发生于 `_navigate_fresh(本题搜索URL)` 之前。现有恢复分类已覆盖导航超时、DNS和页面上下文销毁，但漏了该明确的导航网络变更错误。没有证据判断服务器为何发生网络变更，不把浏览器错误进一步推测成网络设备或服务器最终根因。

修复仅向独立 GEO venv 中的 `geo_source_cards/search_recovery.py` 增加 `Page.goto: net::ERR_NETWORK_CHANGED` 的读失败分类，继续使用既有次数上限、20秒冷却和持久化失败尝试记录。分类仅用于百度/文心只读搜索；DeepSeek、原生豆包、未知提交、未知错误不自动重发。原内容工作台 venv 未修改，原 GEO 和其他采集服务未重启。

备份目录：`/opt/monitor/geo-capture/backups/wenxin-network-change-1792033056/`。包含旧模块、SQLite一致性备份、完整历史capture.log、health、恢复控制状态、审计与面板resume操作编号。旧SHA256 `cf840857af806d87bf1ebea1661eb6021c7cb2512bc4b97c302ae3949bc6b425`，新SHA256 `b7c46e0aabb820a0412aefc1174aa65e28f0331c27b875b8946a2f6d009383bb`。

仅恢复已确认在首页导航失败的任务 `089b054835c2923394f55a560dd2c2de08ba971b4ec5fe8cf242ab3839ea306d`：确认model=wenxin_card、needs_attention仅1条、capturing=0、无部分结果；锁住该批bridge与collector后，调用既有SearchRecovery.failure()归档原错误、登记第1次恢复与冷却，再通过面板resume继续。原39条任务的ID、结果、完成时间逐项比较未变，未清队列、清缓存或重建批次。

12项针对性检查在本地和独立 GEO venv 通过，新增检查导航网络变更的归档/冷却和对DeepSeek/未知提交的禁止恢复。`repair_wenxin_navigation.py` 是带现场断言的一次性恢复脚本，禁止盲目重跑。后续是否真正恢复，必须核对第40条及之后的全文/全部信源processed回执与数据库，不仅凭running状态。

恢复验收追加：10:59第40条已完整完成并processed，含34条信源。11:00对全部40条文心回执再次逐条对照PostgreSQL正文、全部信源、原始结果、引用和source_entries，保真检查通过。原10个Docker容器启动时间、内容工作台4个正式服务PID/启动时间、两个旧豆包105/105均未改变。后续采集仍运行；最终一小时结论仍必须报告中断事实。

11:01:26复查：第41条亦已processed，含27条信源。恢复后连续2条完整结果回执成功，进度41/126，服务active/running、无回传错误。未修改长测异常记录或起始时间；截至此刻一小时窗口尚未结束。
