# GEO运行与维护入口

更新于 2026-11-12。当前状态见工作区 [PROJECT_STATUS.md](../PROJECT_STATUS.md)，完整交接见 [CURRENT_PROJECT_HANDOFF.md](../CURRENT_PROJECT_HANDOFF.md)。

主 GEO 每天北京时间 09:00 启动。豆包四路、百度卡片和元宝各自推进，文心卡片在百度收尾后启动。DeepSeek 的 GEO 采集已停用，历史结果仍可查。创作中心按已保存的任务配置独立执行。

- 采集调度：`control_panel.py`、`daily_tasks.py`、`daily_dispatch.py`。
- 原生采集桥接：`native_entry.py`、`capture_bridge.py`；worker在相邻redroid/yuanbao目录。
- 创作：[creation/README.md](creation/README.md)。
- 主面板源码：`dashboard-integration/app/`；主后端部分本地源码：`server-source/`。
- 受控恢复包：`releases/20261015/unified-current/`，按manifest逐文件恢复，不能盲目覆盖生产。
- 当前维护证据：`maintenance/20261021-followup/`；此前报告保留原样。
- 版本管理与完整创作引擎源码副本说明：[SOURCE_CONTROL.md](../SOURCE_CONTROL.md)。

公网面板：https://1any.top/geo_monitor/；内网面板：http://192.168.31.106:3000/。服务器主目录`/opt/monitor`，采集控制`/opt/monitor/geo-capture`，创作`/opt/monitor/geo-content`。

只读检查优先复用已有SSH配置，不输出凭据。任何修复均先备份、检查发送中请求与用户暂停，不删队列、回执、账本、Android卷或登录。`archive/one_off`和历史maintenance脚本不能当作通用恢复命令重跑。

### 安卓低内存退出

当元宝进入原会话读取退避时，查安卓的进程退出记录和 `lowmemorykiller` 日志，并核对宿主机的 `MemAvailable` 和 `SwapFree`。2026-11-12 的中断发生在宿主机交换空间不足时，已把总交换空间从 8 GiB 扩到 12 GiB，并写入开机挂载配置。恢复后先按原发送凭据回读会话，确认这条及后续回答均取得 GEO 入库回执。
