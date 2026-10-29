# 元宝内存上限在线调整

2026-10-23 11:14:28（北京时间）核验。用户已授权必要时提升元宝内存。

- 服务器物理内存约15.35GiB，检查时可用约4.8—5.5GiB。元宝原容器RAM上限3GiB；cgroup保留oom=7、oom_kill=4的历史计数，Android另有low_memory退出记录。
- 已执行 `docker update --memory 4g --memory-swap 6g yuanbao-hpe14-android13`，RAM上限从3GiB提升到4GiB。RAM+swap合计仍为6GiB，swap允许量由3GiB变为2GiB；调整前实际swap约0.54GiB，未挤占现有用量。没有增加主机交换空间。
- Docker inspect、实际cgroup memory.max、Docker磁盘hostconfig.json均为4294967296字节；RAM+swap磁盘配置保持6442450944字节。设置已保存在当前容器配置，未通过重启来验证。
- 容器ID、容器进程、启动时间、数据卷及App PID4403前后完全一致，未重启容器或App，没有清除登录、重置队列或重发问题。没有修改Java堆上限：实际Java分配约38MiB，仅占现有512MiB上限约7.3%，本次证据指向容器/系统内存压力，不需盲目放大Java堆。
- 原批次从调整时56/168推进到58/168；处理回执与PostgreSQL成功数均58，第59题正常生成。worker active，delivery_errors为空；采集内存监控已读取新4GiB上限，工作内存约1.12GiB/28.1%。核验窗口没有新增oom/oom_kill计数。
- 资源策略保存于服务器 `/home/user/redroid-yuanbao/container_resources.json`，本地 `yuanbao-deploy/config/container_resources.json`；SHA256为 `2fc1dbc5f280822e8e921f78b57a0607f8cc8163d22a8a1e07310d943e5566e8`。加入受控恢复映射，新总数222。只增补本资源文件，没有运行全量源码打包；553个唯一源码快照条目校验无错误。
- 既有阈值/限次内存维护、原请求身份及未知请求保护保留。未修改文章候选、API预算、费用账本或原稿，没有新的文章/余额API调用。

这是在线配置和连续采集的实际验证，不是整批或跨日无故障验收。4GiB是容器可用RAM的上限，不是主机独占预留；仍需保留已有内存采样及安全边界维护。若将来重建容器，必须保留当前命名数据卷、镜像及启动参数，并沿用本资源策略；不要重跑历史provision脚本覆盖现有环境。

回退仅在核对当前实际RAM/swap均低于旧上限后使用原3GiB/合计6GiB配置；不能在高占用时盲目缩容。本轮没有执行回退。

证据：before.json、after.json、result.json、verification.json；本轮只读核验脚本verify.py、在线调整脚本resize.py。首次下载私有资源目录被权限拒绝，已仅将本非敏感JSON复制到临时文件读取，没有放宽私有目录权限。
