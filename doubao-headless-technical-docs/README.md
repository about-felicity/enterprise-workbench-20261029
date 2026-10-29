# 豆包无头 Android 采集项目

基于 Linux、Redroid Android 13、Houdini 14 和豆包 Android App 的持久化采集系统。通过 UI 提问，通过只读 App SQLite 数据匹配请求、答案与信源，使用 systemd 守护和显式失败恢复。

本仓库包含自有采集源码、部署配置、测试、历史排障脚本及技术文档；通过Git子模块固定Redroid上游版本。不是豆包官方API。不包含账号、APK、转译库、镜像及运行数据。

- [详细技术说明](TECHNICAL.md)：架构、模块、数据协议、状态机、兼容性、部署、恢复、测试和限制。
- [运维手册](RUNBOOK.md)：状态核对、任务提交、排障和迁移。
- [2026-10-12 验收快照](evidence/acceptance-2026-10-12.json)：脱敏的统计与证据边界。

## 当前结论

核查时间：**2026-10-12 17:42 北京时间**。

| 项目 | 已核查结果 |
|---|---|
| 执行环境 | Android 13 Redroid + Houdini 14 com1.3 + 豆包15.2.0 |
| 累计队列 | 完成562题、待处理1题 |
| 导出数据 | 5,740条信源记录、1,619处正文引用、562个唯一请求ID |
| 1小时短测 | 20/20，通过，实际观察3605.15秒 |
| 24小时长测 | **失败，未通过**；计划480题，入队426题，阶段快照完成425题 |
| 长测实际观察 | 76,593.95秒，约21小时16分34秒 |
| 当前worker | failed；业务熔断，不自动重复发送 |
| 待处理原因 | `Required sources are missing` |
| 原生异常 | 当前报告未检出fatal/ANR；OOM=false、容器自动重启计数0 |

“未检出原生异常”仅描述保留日志；不等于证明所有时间都不存在异常。旧文档中“长测进行中”的说法已经过时。

本文档项目与后续 DeepSeek网页／百度文心／文章生产工作台是**独立系统**，不要混用其队列、费用策略、服务或验收结论。本次文档核查没有重启服务、重跑题目或恢复失败长测。


## 项目源码

- [redroid-deploy/](redroid-deploy/)：完整本地文本源码，保留原文件布局。
- [源码清单与SHA256](SOURCE_MANIFEST.json)：逐文件核对，无凭据、数据库或原始聊天输出。
- `redroid/`：ERSTT/redroid上游Git子模块，固定原工作区提交；保留上游自己的许可证。
- [源码使用说明](SOURCE_GUIDE.md)：正式入口与历史实验边界。

```bash
git clone --recurse-submodules https://github.com/about-felicity/doubao-headless-technical-docs.git
```

仓库是私有仓库，需要账号访问权限。镜像、Houdini组件及App需另行准备，不能仅clone就声称可运行。
