# 源码使用与目录说明

本仓库现在包含原工作区`redroid-deploy`的71个文本源文件，以及固定提交的`redroid`上游子模块。`SOURCE_MANIFEST.json`记录原始源文件的SHA256，可与原工作区核对。

## 正式执行入口

- `redroid-deploy/unattended_core.py`：任务、匹配、结果校验。
- `redroid-deploy/unattended_worker.py`：Linux worker与CLI。
- `redroid-deploy/runtime_preflight.py`：当前环境基线。
- `redroid-deploy/compose.hpe14.yaml`：当前Android13/Houdini14实例。
- `redroid-deploy/redroid-doubao-hpe14-worker.service`：当前常驻服务。
- `redroid-deploy/soak_monitor.py`、`soak_sequence.py`：独立验收观察器。

**不要直接执行默认deploy.sh来部署当前版本**：它使用默认compose.yaml，属于旧方案。当前方案应明确指定`docker compose -f compose.hpe14.yaml`，并先准备验证过的镜像、外部数据卷及登录状态。具体见TECHNICAL.md与RUNBOOK.md。

## 本地远程工具

`remote.py`、`tunnel.py`等原源码保留，便于迁移与维护，但真实`local_server.txt`和`server_known_hosts`不入库。

需要这些工具时，将根目录`local_server.txt.example`复制为`local_server.txt`并在本机填写。真实文件已加入.gitignore；不要把密码写进源码或提交。现有remote.py使用密码认证和AutoAddPolicy，部署到新环境前应审核主机指纹策略。

## 历史实验与维护脚本

为了保留整个项目，包含Android15、旧Houdini13、构建实验、迁移、备份、清理和故障注入脚本。这些不是新的生产默认流程。

- `build_*`、`probe_*`、`migrate_test_app.py`、`fix_hpe_namespace.py`等含实验容器名、卷名和路径；阅读后再使用。
- `clean_server_project.py`会移动服务端文件，不要当成无副作用的检查命令。
- `test_phase_recovery_live.py`涉及真实发送阶段验证，不属于普通离线单元测试。
- `test_unattended.py`、`test_soak_sequence.py`用于已有Linux依赖环境的离线测试；本次上传只做Python语法和JSON检查，没有重新故障注入。
- 子目录历史README、PROJECT_GUIDE等保留原貌，可能含过期的长测状态。2026-10-12状态以根目录README和evidence摘要为准。

## 未上传内容

不上传真实账号密码、known_hosts、Python虚拟环境、缓存、下载镜像／转译包／APK、App聊天数据库、登录数据卷、截图及原始答案、备份tar。这些是凭据、运行数据或第三方二进制，不属于可安全提交的自有源码。

新机恢复需要单独安全传递已验证镜像和合法可用组件，并由操作人建立登录状态。源码上传完整不等于所有外部依赖可公开再分发或安装后即运行。

原有文章生产项目`geo-source-card-collectors`未纳入本仓库，避免混淆独立系统。
