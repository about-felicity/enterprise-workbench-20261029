# 内容创作自动衔接与并发部署

2026-10-26，已部署至 192.168.31.106。

- 删除分析仿写最早开始时间控件及前后端时间限制。已有任务中的旧 writing_time 不再阻挡分析；新任务保存 analysis_start=after_capture。
- 每个任务的采集渠道、问题和轮数全部完成后自动入队，分析后由原有阶段依赖继续写作、审稿。调度轮询间隔 2 秒，执行器轮询 1 秒；忙碌时排队。
- 原单进程串行执行器改为有界独立进程，默认 4 路，配置最多 8 路。按计划公平分配，同一任务加进程锁；共享分析缓存争用时延后重入并复用已有响应。
- 保留暂停、预算上限、未知发送结果不自动重发等机制。任务创建不再同步请求余额，真实收费请求仍逐次检查余额并原子预留费用。
- worker 服务采用 KillMode=mixed 和 30 分钟停止超时，SIGTERM 停止接单并等待当前子进程退出。

## 验证

68 项测试通过（含继承测试重复执行）；4 个真实独立子进程的模拟分析时间区间相互重叠，随后执行模拟写作；8 个独立进程争抢同一预算，只有 1 个获准预留，7 个被拒绝。额外 SIGTERM 集成测试确认子任务完成后 supervisor 才退出。

候选页面和部署后页面均经 Chrome Playwright 验证：9 个产品知识库可直接选择，无搜索框、无分析时间框，提交数据包含 after_capture；页面无 JavaScript 错误。

3 个创作服务均 active，健康记录为 bounded_processes、max_parallel_jobs=4。上线前确认没有有效计划、没有可运行创作作业或正在执行的创作浏览器采集；保留旧暂停任务。未调用付费模型开展测试，因此未验证真实模型吞吐量和完整付费成稿质量。模型限流、网络和素材准备仍可能影响耗时。

## 备份与恢复

服务器原文件：/opt/monitor/geo-content/maintenance/creation-parallel-20261026/before
已部署文件及校验：verification/release.json。
服务新增配置：/etc/systemd/system/geo-content-worker.service.d/parallel.conf（本目录留有副本）。
源码、source-snapshot 及 unified-current/source.zip 已同步。恢复前先停止接收新任务并等待在途请求结束，再恢复 before 文件、移除本次新增 drop-in、daemon-reload 并重启三个创作服务；勿清除请求记录或预算账本。
