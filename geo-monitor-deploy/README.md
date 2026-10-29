# GEO运行与维护入口

更新：2026-10-21。当前状态见工作区[PROJECT_STATUS.md](../PROJECT_STATUS.md)，完整交接见[CURRENT_PROJECT_HANDOFF.md](../CURRENT_PROJECT_HANDOFF.md)。旧报告中的05:00主监测、12小时或6小时复测、DeepSeek等待旧浏览器登录等描述都是历史快照。

主GEO每天北京时间09:00启动，当前自动通道为两路豆包、百度卡片、文心卡片和元宝；DeepSeek改为手动Chrome插件公网回传。创作中心已接入同一主面板，通常01:00独立采集、最早04:00写作，按任务保存配置执行。

- 采集调度：`control_panel.py`、`daily_tasks.py`、`daily_dispatch.py`。
- 原生采集桥接：`native_entry.py`、`capture_bridge.py`；worker在相邻redroid/yuanbao目录。
- 创作：[creation/README.md](creation/README.md)。
- 主面板源码：`dashboard-integration/app/`；主后端部分本地源码：`server-source/`。
- 受控恢复包：`releases/20261015/unified-current/`，按manifest逐文件恢复，不能盲目覆盖生产。
- 当前维护证据：`maintenance/20261021-followup/`；此前报告保留原样。
- 版本管理与完整创作引擎源码副本说明：[SOURCE_CONTROL.md](../SOURCE_CONTROL.md)。

公网面板：https://1any.top/geo_monitor/；内网面板：http://192.168.31.106:3000/。服务器主目录`/opt/monitor`，采集控制`/opt/monitor/geo-capture`，创作`/opt/monitor/geo-content`。

只读检查优先复用已有SSH配置，不输出凭据。任何修复均先备份、检查发送中请求与用户暂停，不删队列、回执、账本、Android卷或登录。`archive/one_off`和历史maintenance脚本不能当作通用恢复命令重跑。
