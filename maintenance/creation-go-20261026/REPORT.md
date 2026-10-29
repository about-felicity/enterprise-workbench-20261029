# Go 动态并发部署记录

2026-10-26 已部署到本地服务器 192.168.31.106。用户要求 DeepSeek 抓取保持现状，本次未修改其账号、浏览器会话、采集锁或通道配置。

## 运行行为

- Go 二进制 `/opt/monitor/geo-content/bin/creation-runner serve` 替换创作 worker 主进程；默认 10 个任务同时推进，按计划公平分配，不为空闲槽位常驻子进程。
- 模型网络请求通过私有 Unix socket 交给 Go 连接池并发发送。已有 Python 引擎仍负责文章阶段、收费前预留、响应落盘、质量校验及导出。不是整个系统去 Python。
- 百度/文心已从全局浏览器锁改为每个计划、每个渠道的独立锁和频率状态；原有持久浏览器资料按同一身份隔离。每计划最多一个搜索采集子进程，整个创作模块最多 10 个搜索采集槽位，按需启动、完成释放；每次仍只采一个问题，不绕过原有验证、退避和每通道间隔。
- 独立采集池不使用主 GEO 浏览器锁，不写主 GEO 素材。DeepSeek 分支保持原路径。
- 可用内存低于 1200MB 时等待；新浏览器启动期间每个预留 256MB 的启动余量，避免同时到达时重复计算相同可用内存。采集服务 MemoryHigh=4G、MemoryMax=5G。10 是并发容量上限，不是无条件保证在当前机器负载下同时启动 10 个完整浏览器。
- 活跃采集继承槽位和资源锁，即便启动器被杀死，仍运行的子进程也不会丢掉独占权。正常结束删除活跃记录、释放槽位。无任务时不启动浏览器。
- SIGTERM 停止接单，等待在途任务完成后关闭模型 socket；未知请求仍保留现场，不自动付费重发。既有暂停作业未重新启用。

## 验证和边界

- 83 项 Python 兼容性测试通过，包含预算原子预留、未知请求、恢复和素材隔离。
- Go 测试与 `go test -race`、`go vet` 通过：10 个真实子进程同时运行、10 个模拟模型请求同时进入上游、10 个采集租约和第 11 个等待、计划公平、坏状态隔离、停止接单及启动器崩溃后锁仍有效。
- 实际 Go serve 进程启动 10 个模拟适配任务，SIGTERM 收尾成功，socket 正确清理。
- 上线后通过真实 Go 网络层执行一次只读余额检查，成功；以实际采集用户取得并释放生产槽位，权限正确。
- Chrome 页面验证通过：9 个知识库均可直接选择，无搜索框、无分析最早开始时间，提交自动衔接配置，页面无 JS 错误。
- 三个创作服务 active；worker MainPID 的可执行文件实际为 Go 二进制。上线空闲时 worker 服务占用约 10MB，此数值不包含工作任务、浏览器和其他服务。
- 本次没有付费生成请求，也未开展 10 个真实平台浏览器的持续采集压测；因此不把模拟并发结果当作真实平台吞吐量保证。真实速度仍受可用内存、平台接口和验证码等影响。

## 文件与恢复

校验清单：verification/release.json。Go 源码位于 geo-monitor-deploy/creation-go，已保存 Linux amd64 静态二进制副本。源码、二进制、systemd drop-in、source-snapshot 和 unified-current/source.zip 已同步。

服务器备份：/opt/monitor/geo-content/maintenance/creation-go-20261026/before。
新增配置：geo-content-worker.service.d/zz-go.conf、geo-creation-studio.service.d/dynamic.conf。

恢复前停止接收新任务并等现有请求与采集结束。恢复 before 中原文件，移除本次新增两个 drop-in，daemon-reload 后重启创作服务；旧 parallel.conf 会恢复原 4 进程设置。不要清除请求、任务与预算记录。

重建二进制：在 creation-go 目录执行 `CGO_ENABLED=0 go build -trimpath -ldflags "-s -w" -o creation-runner .`，测试使用 `go test -race ./...`。安装到 /opt/monitor/geo-content/bin/creation-runner 时必须设置模式 0755；仅从 ZIP 解包不会保证执行权限。
