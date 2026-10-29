# 豆包第二账号独立模拟器

2026-10-14 15:30 北京时间恢复更新：已定位并绕过 Houdini ARM64 openat 长路径 256 字节截断，修复旧会话 mmicu FTS 触发链路阻断原生落库的问题。已连续验收首 7 题完整正文/全部信源 GEO processed，实际最短发送间隔 37.80 秒；第二台 active 无头继续当前 21×5 批次。停机/过期 running 状态已修复。第一台保持 105/105，不重跑。详见 `ACCOUNT2_RECOVERY_20261014.md`，以下历史进度保留。

15:52 最终复核：16/105 GEO processed、最短发送间隔 36.94 秒、服务 active，第 17 题处理中。第 15 题迟到完整回答已直接对账，无重发；第二台等待上限改为 900 秒。验收逐题核对服务端确认、请求唯一性及 GEO 完整内容一致性。

2026-10-13按用户要求新建供人工登录。容器doubao-hpe14-account2，镜像doubao/redroid:13-hpe14-com1.3，独立新卷doubao-hpe14-account2-data，2 CPU/3GB，restart unless-stopped。

Linux ADB 127.0.0.1:5558，Windows SSH隧道127.0.0.1:15558。使用open-doubao-account2.ps1打开scrcpy窗口“Doubao - Account 2 Login”。隧道后台隐藏运行；投屏窗口由用户明确要求显示。

已安装与现有已验证环境相同的官方豆包15.2.0，仅提取base.apk安装，没有复制旧账号的数据或登录资料。用户自行完成首次协议及登录。第二账号未安排任何自动采集任务，不会争用第一账号的worker。现有21x5采集继续运行。

后续用户确认登录，并明确要求第二账号同配置采集。已关闭标题匹配的scrcpy窗口，启用redroid-geo-products-account2.service；环境变量DOUBAO_BATCH=geo-products-21x5-account2-20261013、DOUBAO_CONTAINER=doubao-hpe14-account2、DOUBAO_SERIAL=127.0.0.1:5558。每账号独立105条、SQLite、设备锁、outbox和回执，正文/信源按设备独立回传。geo_batch_bridge.py默认值兼容第一账号；第一账号进程未重启。

终端状态空白根因：/usr/local/bin/monitor-live读取record.status，而原豆包payload未带status。新桥接填status=success；终端对旧豆包完整正文、complete=true且非空信源显示captured，其余缺状态显示unknown。不修改历史原始入库记录、不把ai_pending标为分析完成。旧脚本备份monitor-live.before-doubao-status-20261013，只重启监控显示，未重启采集或面板。当前显示由monitor-live-display临时systemd服务输出到tty1。

运行核查发现第二账号并未实际取得回答，不能说其正常采集：首题及下一题消息均卡在原生发送中，message_id=null/server_index=0、fts_content=null；App重启后红色感叹号、status12，原生重试后status10仍无回答。基础网络DNS/ping通过；第二容器独立重启并通过运行环境校验仍未解决。两题重试均点击原消息的已确认发送失败控件，保留同一原生local_message_id，未清空数据库或新建重复提问。
新增严格结构文本匹配：fts为空时只在包含本任务唯一编号的用户消息里核对完整text_block，避免误报absent。Linux33测试通过。第一账号进程未重启、不受影响。曾短暂允许隔离失败任务以验证下一题，验证同样失败后停止第二账号服务，撤销隔离模式默认启用，保留105队列（1 needs_attention、1 prepared、103 pending），等待排查账号发送链路。用户已被询问该账号在手机端是否能正常回答，不能假称账号封禁或登录无效。投屏保持关闭。

用户确认第二账号在手机端可以正常回答。针对是否两模拟器登录同一账号，compare_active_accounts.py 按各队列实际发出消息的发送者 UID 与数据库 UID 交叉核对：第一账号尾号385833，第二账号尾号451113，same_sender_uid=false、same_account_database=false。因此已排除两模拟器登录同一账号；尚不能排除第二账号自身手机与模拟器同时登录的影响。最新核查第一批70/105已采集并收到GEO processed回执，仍在运行；第二批仍0/105、blocked_native_send。不得把账号不同当作发送故障已修复。

13:20—13:26（北京时间）后续核查：第二账号登录设备页只有当前redroid和Motorola手机；账号管理可打开，但新对话短暂空白后回到同一旧失败对话。临时关闭第二容器private DNS、重开App、在原失败消息上重试一次仍未取得回答，已恢复原DNS设置。未清除App数据、未退出已有账号；已通过“添加账号→手机号登录”打开第二模拟器重新认证入口并开启scrcpy（Doubao - Account 2 Login）。用户输入期间停止UI操作。重新登录后必须核对当前账号，不能继续用旧消息发送者ID代表新会话；两条原失败消息和任务均保留，第二批仍未恢复。

worker已补充：跨页面过渡检查旧采集消息，发现新对话实际回退即禁止发送；发送点击前再检查；识别已观察到的“为你推荐”空白新对话页；仅处理豆包的Android可选通知权限弹窗，其他权限不自动变更。Linux39测试通过；第二账号旧会话实测被新保护拦截，未产生新消息。

第一批曾自行停在90/105，原因是Android“Allow 豆包 to send you notifications?”挡住界面；第91题无发送意图、点击事件、App请求。resume_first_notification.py核验未发送、处理弹窗、验证新对话并保存before-notification-recovery.sqlite后，仅恢复这一题，保留原失败事件；服务恢复后第91条正文及信源已收到GEO processed回执，状态running。恢复脚本SSH等待超时但远端已执行成功，不要重复运行。后追加的空白页识别改进已在服务器文件中，下次进程启动生效；未为该改进中断已恢复的采集。

用户随后确认第二个已登录。active_database_accounts.py按两个App当前进程打开的唯一数字IM数据库核验：第一账号尾号385833，第二账号当前尾号066524，与此前451113不同，也与第一账号不同。旧消息发送者不能代表切换后的当前登录账号。新登录账号通过新对话就绪检查后，第二服务已切换至独立批次geo-products-21x5-account2-relogin-20261013，仍105题/至少30秒/完整正文+信源回传。旧批次及两条失败消息全部保留；没有跨账号重置/复用旧发送任务。检查时scrcpy已关闭。新批次首题开始等待回答，最终是否成功以回执为准。
