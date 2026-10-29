# 豆包无头 Android 采集项目

> 当前运行更新（2026-10-15）：两台Android13/Houdini14模拟器常驻，GEO当前原生批次由`geo-native@批次.service`管理，两小时批次116/119条均processed后暂停；历史两个105/105不重跑。旧`redroid-doubao-hpe14-worker`、旧soak24h和两个105/105服务的开机项已停用，定义和证据保留。以下旧单实例验收及启动命令属于历史，不能作为当前五通道任务启动入口。现用[统一面板](../geo-monitor-deploy/docs/guides/CONTROL_PANEL_GUIDE.md)；文件已分类，见[CODE_LAYOUT.md](CODE_LAYOUT.md)。

当前部署：**Android13 Redroid + Houdini14 com1.3 + 官方豆包 App 15.2.0**，运行于 Linux 服务器 `192.168.31.106`。
初始 6 题及额外 100 题已全部完成：1,095 条信源、300 处正文引用，106 个请求编号唯一。
模拟器重启及发送途中重启 worker 已通过，30 项 Linux 故障测试通过。24 小时验证另行记录，未完成时不标记通过。
备份后两题冒烟通过，隔夜约 13.5 小时无原生崩溃。验收现改为先执行 1 小时短测（每 3 分钟一题，20 题），通过后自动启动同频率的 24 小时长测（480 题）；原每 10 分钟一题长测已停止归档。详见 [当前手册](docs/operations/HPE14_FIX.md)。
服务器最新快照见 `hpe14-acceptance/acceptance-snapshot.json`，导出报告在 `hpe14-export/`，实际测试时长以记录为准。

原 NDK 转译器的 `CHECK failed` 已通过更换执行环境绕开。没有修改 APK 或删掉断言。
原 Android15 及失败实验容器已停止，账号数据卷保留；原有八个业务容器未被停止或重启。

文档入口：

- [当前修复、架构、操作、扩展、备份与上游依据](docs/operations/HPE14_FIX.md)
- [无人值守正确性与恢复规则](docs/operations/UNATTENDED.md)
- [完整源码文件树及运行目录说明](docs/operations/PROJECT_TREE.md)

历史实验文件已移到项目外的 `/home/user/redroid-doubao-archive/`；具体归档目录及移动清单见 PROJECT_TREE.md。

Linux 常驻服务是 `redroid-doubao-hpe14-worker.service`，已启用开机启动。
Android 容器是 `doubao-hpe14-13-test`，ADB 仅监听回环端口 5557。
任务和输出均在 Linux 上处理，关闭 Windows、投屏或 SSH 不影响执行。

```bash
sudo systemctl status redroid-doubao-hpe14-worker.service --no-pager
sudo cat /home/user/redroid-doubao/hpe14-acceptance/health.json
sudo python3 /home/user/redroid-doubao/hpe14_report.py
```

将新问题写成 UTF-8 JSON 字符串数组，再提交：

```bash
sudo /home/user/redroid-doubao/worker-venv/bin/python \
  /home/user/redroid-doubao/unattended_worker.py enqueue \
  --batch my-batch-001 --questions /home/user/redroid-doubao/my-questions.json \
  --require-sources
```

结果：`/home/user/redroid-doubao/hpe14-acceptance/answers.json`。
Windows 临时投屏使用 `redroid-deploy/open-doubao.ps1`，默认连接新 Android13。

登录过期、验证码、限流、版本变化或发送状态歧义会明确停止并保留任务，不把不完整数据标记成功。
Houdini 新组件仍有上游到期时间，启动检查从 2028-06-01 起拒绝旧版本，届时必须验证更新。
