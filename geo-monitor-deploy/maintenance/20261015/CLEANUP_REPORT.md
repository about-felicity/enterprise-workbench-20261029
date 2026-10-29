# GEO项目整理与清理记录

日期：2026-10-15，北京时间约13:22–13:37。用户授权梳理整个GEO项目并清理不需要的中间产物。本次先盘点、识别运行依赖、归档必要证据，再按逐文件SHA256清单清理；没有变更正式业务代码。

**实际释放约8.8GB空间：本地约5.31GB，服务器约3.50GB。** 本地工作区从6.70GB降至约1.39GB。这里使用十进制GB；工作区统计为文件逻辑大小，服务器为文件系统可用空间实测增量，统计时仍有正常采集与日志写入。

## 本地处理

| 项目 | 清理前大小 | 处理 |
|---|---:|---|
| 两份旧Android NDK镜像tar | 1.755GB | 删除下载缓存；服务器相同固定digest镜像仍保留，原manifest/index/SHA256存入清单 |
| 六份重复OCI blobs | 1.755GB | 逐个核对SHA256与blob名一致后删除；保留原镜像manifest |
| 两份历史隧道错误日志 | 1.708GB | 完整无损压缩并逐字节哈希核验；压缩后合计30.09MB，原位置各留64KiB尾部 |
| 裸frida-server | 116.34MB | 与保留的xz解压内容完全一致，删除冗余裸文件 |
| 历史构建副本、源码编译及lint缓存 | 约8.95MB | 历史构建副本打包为2.51MB zip并校验每条目；可再生源码缓存直接删除 |

共877个文件删除或压缩替换，清除58处候选目录中的空目录树；仅删除清单内文件，不递归删除未登记的新文件。保留源码、所有Git仓库与原有未提交修改、桌面程序及其运行库、当前APK、Houdini兼容包、ADB/scrcpy、浏览器profile、成品Word和诊断资料。正式源码目录的editable-install egg-info保留。

已留存：

- [清理前盘点](local-inventory-before.json)、[清理后盘点与逐项检查](local-inventory-after.json)。
- [逐文件计划、SHA256和镜像身份](local-cleanup-plan.json)、[实际执行清单](local-cleanup-applied.json)。
- [历史构建副本zip](historical-build-copies.zip)。
- [完整旧隧道日志1](tunnel-error.log.gz)、[完整旧隧道日志2](tunnel-15558-error.log.gz)。

准备脚本与PowerShell执行器均位于上级maintenance目录；路径必须落在本工作区、拒绝junction/symlink、先验证全部哈希和归档再修改。执行器使用原生PowerShell文件操作，并仅移除已经空的目录。脚本是此次一次性清单工具，已加执行后保护，不要为日常维护反复执行旧日期清单。

## 服务器处理

- 执行`docker builder prune --force`，只回收未使用的构建缓存。Docker报告逻辑回收4.349GB；整个清理窗口文件系统可用空间实测增加约3.50GB，两者口径不同，不叠加计算。
- 删除Chrome下载deb，先核对已安装版本与安装包版本完全相同：155.0.8059.39-1。已安装Chrome没有修改。
- 删除裸`frida-server-account2`，先核对保留xz解压内容SHA256完全一致，且没有容器直接bind该文件、没有宿主进程从该文件运行。
- 上述两个冗余文件合计259,887,556字节。没有执行image prune、volume prune、container prune或system prune。
- 原Docker镜像、数据卷、停止的历史Android容器、模拟器修复备份和全部批次均保留。特别保留account2的Keva/openat/FTS故障现场及修复前后证据。

服务器私有维护目录：`/opt/monitor/geo-capture/maintenance/20261015/`；脱敏导出目录：`/home/user/redroid-doubao/maintenance-20261015/`。本地有[清理前状态](server-before.json)、[第一阶段清理后状态](server-after.json)、[文件清单](server-cleanup-plan.json)、[执行结果](server-cleanup-applied.json)、[最终状态](server-final.json)、[最终连续性核验](server-final-continuity.json)。

本次维护脚本最终版已归到私有维护目录的`tools/`；此次产生的5份服务器根目录临时脚本已合并清除，完整源码也在本地maintenance目录保留。

## 旧测试进程与开机项

13:34保存定义、状态、完整观察事件和journal后，退出`geo-editorial-acceptance-current.service`。它是10月9日启动、一直针对2026-10-09批次等待前置条件的临时验收观察器，elapsed_seconds=0；不是正式采集、写作或分析worker。原状态仍保留waiting_prerequisites，**没有把这次旧验收标成通过**。

已完成的`geo-doubao-soak2h-1792030883.service`及其deadline timer关闭开机启用，停止已触发完的timer；unit定义与实际两小时报告仍保留。只影响记录器和测试计时器，不操作两个原生批次服务，不恢复任务，也不影响面板后续新任务。

原定义、状态和日志位于服务器私有`retired-observers/`目录；脱敏[退出记录](retired-observers-applied.json)已下载。本次没有改变Codex自动化；`automation`、`geo`和`10`保持原暂停状态。其他历史失败单元及真正待处理的采集故障没有通过reset-failed掩盖。

## 清理后核查

最终完整快照13:36:21：

- 10个运行容器的ID、镜像ID、状态和启动时间逐项未变，未停止／重启主面板、分析、数据库、接收器或模拟器。
- 排除明确退出的旧验收观察器后，8个所核对业务／隧道服务的PID、启动时间和重启计数未变；文心原批次持续前进至125/126 processed。
- Docker镜像集合及数据卷集合未变。镜像列表顺序不稳定，比较按集合进行，不能用列表顺序变化误报删除镜像。
- 两台豆包仍为原两小时批次116/119条processed，维持已暂停；旧105/105历史批次与证据未动。
- 内网主面板HTTP200；公网未登录入口HTTP302跳转登录，保持原鉴权。
- VPS只读核查：nginx、geo-monitor-auth、offline-fallback均active，GEO相关程序／发布信息／备份总计不足100KB；未修改VPS程序、认证配置或隧道。
- DeepSeek仍等待网页登录，百度卡片仍为原重试耗尽待处理状态。这些不是此次清理导致，也没有靠删缓存或重发来掩盖。

只进行了状态、完整性和依赖核查；未额外发送生产问题或触发付费AI请求。清理不表示历史AI分析或采集阻塞已全部解决。

## 恢复方法

1. 历史构建副本：先把`historical-build-copies.zip`解压到临时恢复目录，按归档中的工作区相对路径取回所需文件；不要覆盖正在维护的新源码。
2. 完整隧道日志：gzip解压到新文件，再按清单SHA256核对；无需覆盖当前仍可写的原日志路径。
3. frida裸文件：按需要从保留的xz解压并核对清单SHA256，不需要重新下载。
4. 旧NDK镜像：优先从服务器仍保留的`erstt/redroid:13.0.0_ndk_ChromeOS`和`erstt/redroid:15.0.0_ndk_AVD`导出。固定manifest digest分别为`sha256:26884891bc012a9e26e803b187a1f01c4d4ef3ddfef68afbbb3a508683b5dfa0`、`sha256:6c2597228d0884626ebd9e3905d5334d8e2e9d6554db4c639851eabd04a65d83`，已与本地旧tar index核对一致。也可通过原下载器按固定版本重建缓存。
5. Docker构建缓存由下次正常build重建；Chrome已安装，不需恢复deb。
6. 旧观察器和已完成长测unit保有私有定义备份。仅当明确需要复现原测试时恢复相应配置；不要常规重新启用已结束的两小时记录器，以免改写历史结束时间。

项目文档已整理为[工作区总览](../../../README.md)和[GEO运维入口](../../README.md)。原交接、实验、故障和验收文档继续保留，作为有日期的历史记录。
