# 当前项目完整源码文件树

整理日期：2026-10-07。源码、配置和文档文件完整列出如下；不包含运行数据或第三方依赖。

```text
redroid-doubao/
├── .gitignore
├── README.md
├── HPE14_FIX.md
├── UNATTENDED.md
├── PROJECT_TREE.md
├── requirements.txt
├── compose.hpe14.yaml
├── runtime_preflight.py
├── unattended_core.py
├── unattended_worker.py
├── test_unattended.py
├── soak_monitor.py
├── soak_sequence.py
├── test_soak_sequence.py
├── hpe14_report.py
├── package_hpe14_results.py
├── backup_hpe14_release.py
├── backup_android13_volume.py
├── redroid-doubao-hpe14-worker.service
├── redroid-doubao-native-log.service
├── redroid-doubao-soak24h.service
├── hpe14-questions.json
└── hpe14-soak-questions.json
```

服务器上还保留以下必需运行目录，纯净源码包不包含它们：

```text
/home/user/redroid-doubao/
├── hpe14-acceptance/
├── hpe14-export/
├── soak24h/
├── soak1h/
├── soak-smoke/
├── backups/
├── linux-tools/
├── worker-venv/
├── __pycache__/
```

`hpe14-acceptance` 是当前队列、结果、故障日志及截图；`soak24h` 是正在运行的长测；
`soak-smoke` 保留重启后验证证据；`backups` 保存镜像、登录数据和一致性队列备份。
`linux-tools` 和 `worker-venv` 是 ADB 与 Python 依赖；`__pycache__` 是 Python 自动生成的缓存。
Android 实时登录数据位于 Docker 卷 `doubao-hpe14-android13-data`，不在项目源码中。

历史实验、诊断与下载中间产物已归档到 `/home/user/redroid-doubao-archive/20261007-014544-utc`，移动清单是该目录的 `cleanup-manifest.json`。
此次整理未重启模拟器、worker、日志或长测服务。归档是可恢复的移动，不释放磁盘空间。

纯净源码包：`/home/user/redroid-doubao-source.tar.gz`。
恢复到新服务器还需要安装依赖、加载已验证镜像、恢复数据卷并按 HPE14_FIX.md 配置服务。
