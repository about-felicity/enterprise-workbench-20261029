# 本次维护文件说明

这是2026-10-15纯问题采集、正文审计、创作接入和长测修复的现场记录目录，不是日常启动入口。

- 当前运行源码：`redroid-deploy/question_only_*.py`、`geo-monitor-deploy/{control_panel,native_entry,all_channel_soak}.py`、`creation/`、`dashboard-integration/`、`geo-source-card-collectors/{web_collectors,wenxin_monitor}/`。
- `audit_*`、`inspect_*`、`current_summary.py`和`export_upgrade_reports.py`为现场诊断/导出。部分脚本依赖明确的历史批次，不可当通用恢复命令。
- `install_*`、`deploy_*`、`start_*`、`resume_*`、`reconcile_*`、`promote_*`、`edit_*`、`retest_*`、`publish_*`、`configure_*`为已经执行的现场一次性操作，**不要盲目重跑**。
- `*.before-current.py`是修复前源码证据；`*-runtime.zip`、`creation-frontend.zip`是分阶段构建输入，可能早于最后修复。日后恢复使用 `releases/20261015/unified-current/` 最新映射包并核对哈希，不能用旧阶段包覆盖。
- 整理/删除的逐文件清单见`local-generated-cleanup.json`，服务器只清理本次已验收无挂载预览容器及未使用构建缓存。原队列、失败记录、登录、成稿全部保留。
- 结论与维护入口见 `docs/reports/UNIFIED_UPGRADE_20261015.md`；结构化脱敏证据在 `reports/20261015/unified/`。
