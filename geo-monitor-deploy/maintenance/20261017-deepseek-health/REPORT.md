# DeepSeek双模拟器检查（2026-10-17 15:55）

第一台容器running、无容器OOM；App真实截图为手机号验证码/密码登录首页，device.auth=login_required，原批次18/63、45待采、无待回传。14:46 worker因登录要求退出77，不是本次维护停止，也不能靠重启恢复账号。未重发、重置或改原队列。

第二台容器与worker正常，心跳持续更新。检查期间由8条增长到9/63，零回传异常、pending_delivery=0，现正常等待下一次发送（北京时间16:07:44），未重启或操作第二台App。

按用户既有scrcpy偏好，启动第一台open-deepseek.ps1，127.0.0.1:15560投屏窗口DeepSeek - Login，PID18920，真实scrcpy日志确认连接设备且成功渲染。未复制第二账号会话。第一台需要用户人工登录；现有daily_tasks每30秒自动复核scrcpy登录，desired=running会继续原任务。登录未完成前不能声称第一台已恢复。此窗口保留给用户，登录后再确认自动续跑并关闭投屏。

## 15:58 用户重新登录后的验证

auth只读确认ready。原服务自动恢复，PID30871，同一batch已完成第19题并真实入库（1162字、12来源）；当前19/63，下一题正常rate_wait，无待回传。第二台9/63持续running。已验证PID/serial后关闭仅第一台scrcpy18920及15560→5560专用隧道，没有停止模拟器、ADB server或第二台任务。

原因核查结果：第一台容器从北京时间09:37:36持续运行，RestartCount=0，未被OOM杀死；/data始终挂载原持久卷。14:35–14:55内核日志无OOM事件。只读检查Android日志窗口2838行，没有可确认的HTTP401/403、token/session过期、异地顶号或踢出原因；只导出脱敏计数，不导出原始logcat或token。系统exit-info仅列出ISOLATED NOT NEEDED的隔离进程回收，不能当作主App崩溃原因。采集worker/android/device/policy代码没有退出账号或清理App数据动作。

能确认的是App真实回到登录首页，采集器因此安全退出77，重新登录后原任务恢复；目前没有证据进一步确定服务端是过期、其他设备登录、风控或其他原因，不能编造准确原因。登录持久卷可以保存本地资料，不能强制平台继续接受失效会话。证据logout-diagnostics.json与inspect_logout.py。本轮不改生产代码或发送间隔。
