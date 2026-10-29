# GEO 运维入口

**最新（2026-10-15晚）：** [统一升级、正文核验和长测记录](docs/reports/UNIFIED_UPGRADE_20261015.md)。六通道现用新会话／纯问题采集；[内容创作](creation/README.md)已接入大面板与公网同源网关，直接复用GEO完整素材。后文“内容工作台独立／DeepSeek等待登录／豆包暂停”等是旧维护快照。最新采集12h与创作6h复测尚在进行，以实时指针和最终报告为准。

完整业务与源码地图见[工作区总览](../README.md)。此处维护GEO采集控制、主面板集成、上线验证及诊断；内容工作台为另一套独立服务。

最新维护结果见[代码分类、服务重启与百度恢复记录](maintenance/20261015-reorganize/RESTART_REPORT.md)：10个容器及相关LAN／VPS服务已重启核验；两个豆包保持长测后暂停，文心完成，百度原批次继续，DeepSeek按用户选择等待稍后登录。

代码分类见[CODE_LAYOUT.md](CODE_LAYOUT.md)：运行模块保留稳定入口，测试在`tests/`，维护工具在`tools/`，历史一次性脚本在`archive/one_off/`，指南/报告在`docs/`，结构化证据在`reports/20261015/`，发布包在`releases/20261015/`。最新桥接修复源码包为`releases/20261015/geo-runtime-post-reorganization.zip`，按manifest映射恢复，不是自动安装器。

## 生产组件

| 组件 | 服务或容器 | 位置／接口 |
|---|---|---|
| 主面板 | `monitor-dashboard` | `/opt/monitor/yuanbao_monitor/dashboard`；3000；公网`/geo_monitor/` |
| 分析接口 | `monitor-dashboard-api` | `/opt/monitor/doubao_dashboard_server.py`；8765 |
| 豆包接收 | `monitor-doubao-receiver` | 8790；完整原生结果及processed回执 |
| 网页结果接收 | `monitor-result-receiver` | 8791；DeepSeek／wenxin结果及去重身份 |
| 产品分析 | `monitor-product-worker` | `remote_product_ai_worker.py`及`monitor_core/product_analysis.py` |
| 信源正文 | `monitor-content-worker` | `doubao_source_content_worker.py`；`doubao_source_content.db` |
| 数据存储 | `monitor-postgres`、`monitor-redis` | PostgreSQL为采集及分析业务库；Redis按原服务用途保留 |
| 采集控制 | `geo-monitor-status.service` | `/opt/monitor/geo-capture`；8803；`panel/control.sqlite` |
| 豆包1／2 Android | `doubao-hpe14-13-test`、`doubao-hpe14-account2` | 独立数据卷，ADB仅服务器回环5557／5558 |
| 豆包新任务 | `geo-native@批次.service` | `/home/user/redroid-doubao/batches/批次/`；运行代码`geo-batch-code/` |
| 网页任务 | 原`geo-capture-*.service`或新`geo-web@批次.service` | `geo-capture/batches/`及`panel/jobs/` |
| 公网穿透 | `monitor-vps2-tunnel.service` | 原SSH隧道，VPS13000→LAN3000，18765→LAN8765 |

核心Compose定义：`/opt/monitor/deploy/local-server/docker-compose.yml`，项目名`local-server`。新控制面板不接管核心Docker容器的生命周期。不要运行整栈`down`或全局清理来修单个采集器。

## 代码和部署版本

- 控制服务：`control_panel.py`、`fleet_status.py`、`panel.html`。
- 网页结果桥接：`capture_bridge.py`；原生桥接在`redroid-deploy/geo_batch_bridge.py`及生产`geo-batch-code/`。
- 最新前端修改源码：`dashboard-integration/app/`，包括`dashboardPaths.ts`和`api/geo-capture/[...path]/route.ts`。
- 当前前端发布包：`dashboard-vps-prefix-20261015.zip`；生产镜像`monitor-dashboard:vps-prefix-20261015`。`monitor-dashboard:local`为同一镜像。
- 服务器`vps_frontend_release.json`、`dashboard_integration_release.json`记录不同发布阶段，回退须同时考虑公网子路径。
- 旧集成zip、rev2/rev3脚本、一次性故障恢复脚本和报告仍保留作证据，不能作为通用升级入口重复执行。

## 文档顺序

1. [控制台操作指南](docs/guides/CONTROL_PANEL_GUIDE.md)：问题、轮数、间隔、开始／暂停／继续／停止及登录校验。
2. [主面板集成](docs/guides/DASHBOARD_INTEGRATION_20261015.md)、[公网接入](docs/guides/VPS_GEO_ACCESS_20261015.md)：发布、验证、回退位置。
3. [双豆包实际两小时结果](docs/reports/DOUBAO_2H_REPORT_20261015.md)、[网页一小时结果](docs/reports/GEO_1H_REPORT_20261015.md)：两次测试范围和结论分别保留。
4. [分析进度复查](docs/reports/ANALYSIS_PROGRESS_20261015_1317.md)：区分采集入库、产品AI核验和信源正文归档。
5. [清理及恢复清单](maintenance/20261015/CLEANUP_REPORT.md)：本次清理的审计和恢复方法。

## 维护边界

先查实际队列和服务状态，再操作固定批次。暂停应排空当前题和回执，发送未知禁止重发；不要删除队列、缓存或profile来代替排查。历史105/105批次不重跑。`/api/status`中的终止worker标签可能概括为stopped，继续／暂停等操作以`/api/panel`里的持久任务状态为准。

正文抓取库、原始结果、receipts和历史修复备份是数据，不是可随意重建的缓存。Docker构建缓存可重建，但Docker镜像、数据卷、停止的历史Android容器不在本次清理范围内。维护工具仅适用于这次已记录的清理清单，不是定时删除器。
