# GEO代码分类、服务重启与恢复记录

2026-10-15，北京时间。运行状态快照截至14:17:05；百度随后继续处理原批次，因此计数会继续变化。

## 结果

本地186个文件、服务器117个维护／测试／历史脚本已实际分类。10个运行容器、8个LAN常驻systemd服务及网络看护timer、3个VPS服务已重启并核验。生产容器ID、镜像和数据挂载保持一致，没有重建数据库或Android数据卷。

百度原批次恢复运行，连续新增5条完整回答并取得processed回执；另1次没有完整卡片的观测明确标为不可用，未冒充成功回答。全部既有结果保留。DeepSeek网页登录仍过期，用户已选择先完成其他服务、稍后登录；内容工作台维持原登录阻塞暂停，不能宣称全部通道正在采集。

## 文件分类与恢复依据

- 本地分类索引：[GEO](../../CODE_LAYOUT.md)、[豆包](../../../redroid-deploy/CODE_LAYOUT.md)。运行模块和有路径依赖的入口保留稳定位置；测试、部署、诊断、导出、历史脚本、指南、报告和发布包分别归类。
- [本地移动清单](organization-applied.json)记录186个旧／新路径与前后SHA256；[原文件备份](before-organization.zip)保留移动前内容。移动后的Python补充项目根目录导入路径，122个移动Python文件通过语法检查。
- [服务器分类清单](server-organization-applied.json)记录117个脚本。服务器索引为`/opt/monitor/CODE_LAYOUT_20261015.md`及`/home/user/redroid-doubao/CODE_LAYOUT_20261015.md`。
- 服务器原脚本备份：`/opt/monitor/geo-capture/maintenance/20261015-reorganize/server-code-before.tar.gz`。本次后续使用的11个临时文件另归档至该目录`tools/staging-archive/`，见[清单](staging-archive.json)。没有删除失败现场或重置failed状态以掩盖故障。
- 配置、密钥、登录profile、数据库、任务队列、outbox、receipts、成品和原生修复证据保留。私有数据库备份只留在服务器维护目录，没有下载到普通报告目录。

## 重启范围与过程

| 范围 | 已核验结果 |
|---|---|
| GEO核心8容器 | PostgreSQL、Redis、两个接收器、分析API、产品分析、信源正文worker、主面板均实际重启；进程运行，有健康检查的容器通过检查 |
| 两个Android容器 | 均实际重启，Android启动、当前APK／Houdini／Keva兼容修复预检及原账号本地登录检查通过 |
| LAN的8个常驻服务 | 内容工作台4服务、采集控制台、原生日志、显示服务、VPS隧道均active，验证时NRestarts=0；网络看护timer恢复active |
| VPS的3个服务 | nginx、GEO登录鉴权、离线fallback实际重启；nginx配置检查通过，公网同源控制验证通过 |

本次未重启操作系统或Docker daemon。原生采集任务处于用户长测结束后的暂停状态，文心任务已完成，均未为“重启全部服务”而重新启动采集。

重启中有两项启动检查需要处理，证据保留：

1. 接收器原健康检查依赖分析API的8765端口；先等接收器、后启动API会延迟就绪。已启动API并修正维护工具的启动顺序。
2. 第一台Android虽已报告boot完成，第一次应用启动检查仍返回非零。首次维护unit因此失败；该次命令没有记录足够stderr，不能进一步认定底层原因。恢复工具加入有界ADB／应用就绪等待，随后两台预检通过。恢复时检查实际启动时间，没有重复重启已经完成的第一台容器。初次失败unit与journal仍保留。

最终恢复于14:05:05完成，[完成记录](restart-complete.json)、[重启前快照](restart-before.json)、[前后核验](restart-verification.json)、[最终容器健康](final-containers.json)、[VPS记录](vps-restart.json)可追溯。

旧HPE14验收worker、24小时旧测试以及两个旧105题服务的开机项已关闭，操作前均无活动进程；定义与日志归档。它们不再是当前任务入口，不能为消除历史failed状态而重跑，见[旧单元处理清单](superseded-units.json)。

## 百度暂停的具体原因及修复

这次确认的是`capture_bridge.py`的退出与SQLite读取竞态。桥接循环先读取队列快照，再检查子采集器是否退出；两者之间，子采集器已经把暂时的失败任务收尾为`completed / supplement_unavailable`。桥接器却沿用旧`failed_deferred`快照，在看到子进程退出后错误判定仍有失败任务，退出码2并显示阻塞。

原任务数据库已经完成收尾，无需清队列、改结果或重新登录。修复将子进程退出检查放到队列读取之前；只有子进程已退出时，才根据新读取的终态判定阻塞，避免把采集器仍在恢复的中间状态作为最终失败。真实SQLite回归测试在旧实现复现退出码2，新实现正确完成且不产生无正文回传。

14:10:06通过控制台继续原批次`geo-baidu_ai-21x5-20261015`，没有新建任务、重置失败计数或盲目重发。14:17:05复查新增6个完成观测，其中5条完整回答、5个不同新导航ID、5次processed；1次不可用另记，服务active、回传错误0。此前卡片未完整呈现的原始证据仍保留，桥接修复不等于保证每次百度都会呈现卡片。

生产旧桥接代码备份为维护目录`capture_bridge.before.py`。本地修复源码在[capture_bridge.py](../../capture_bridge.py)，带manifest的[运行源码包](../../releases/20261015/geo-runtime-post-reorganization.zip)不是自动安装器。

## 采集与数据保真快照

| 通道 | 实际任务状态 | 完整观测／processed | 唯一入库 | 其他 |
|---|---|---|---|---|
| 豆包1 | paused | 116／116 | 116 | 模拟器在线，剩余容量未启动 |
| 豆包2 | paused | 119／119 | 119 | 模拟器在线，剩余容量未启动 |
| 文心卡片 | complete | 126／126 | 126 | 不重跑已完成任务 |
| 百度卡片 | running | 89／89 | 30 | 59次重复完整观测、8次不可用；97个任务已完成、8个待执行 |
| DeepSeek网页 | waiting_login | 0／0 | 0 | 63个待执行，用户稍后登录 |

对391条唯一入库回执核对完整正文、全部信源、引用及原始结果等字段；原生结果还检查问题、批次及轮次，核对全部通过。百度89次完整观测含重复，因此不能将89与唯一30直接相加。重启前所有已完成任务的结果字符串保持原样，两个历史105/105批次仍各105条processed，未重跑。

证据：[采集核验](capture-verification.json)、[逐条脱敏保真元数据](verified-captures.jsonl)、[重启前队列](queue-before.json)、[继续原百度批次](baidu-resume.json)。`processed`仅表示接收与入库，不能当作产品分析全部完成。

产品分析worker重启后于14:12:49处理了新增实采数据；信源正文worker也有新的抓取周期。[分析快照](analysis-after-restart.json)仍包含历史产品分析待处理／拒绝和信源抓取失败，不能由服务正常推断所有历史分析或信源正文均已完成。

## 公网与测试

[公网验证](public-control-verification.json)通过：原网站鉴权、五通道读取、真实无效配置写请求到达控制器并返回400、CSRF／Origin校验、跨站403、Cookie安全属性、禁共享缓存、不同会话隔离、桌面／手机以及分析API前缀。暂停按钮在已暂停任务中禁用属于预期；恢复按钮请求仅拦截检查URL，没有实际恢复豆包任务。

[测试结果](validation-results.json)：GEO控制／桥接／长测28项在Windows和Linux通过；原生worker52项在实际Linux运行环境通过；参考仓库3项通过，共83项。没有为测试创建额外生产问题，也没有合成付费分析调用。

## 用户指定参考仓库

已取得[wenxin-baidu-collector](https://github.com/about-felicity/wenxin-baidu-collector)，固定commit`8789ea281b201b6ec7a9770ddb24f6ac5f800929`，本地只读参考位置`references/wenxin-baidu-collector/`。[比对记录](../../../references/REFERENCE_REVIEW.md)覆盖新页面导航、正文展开、参考资料抽屉及完整信源检查。

本次真实阻塞发生在桥接状态读取层，未出现需要整套替换DOM抓取逻辑的证据。参考仓库可用于后续页面适配；没有启用它的额外supervisor或降低当前完整正文／全部信源的回传要求。

## 回退与待办

文件分类可按manifest从本地zip或服务器tar选择性恢复旧路径及内容；回退导入路径改动时一并恢复对应测试／工具。不要用历史发布包覆盖当前公网前缀适配。

回退运行桥接代码前，先让当前百度题目和回执排空暂停，再恢复`capture_bridge.before.py`及对应服务；不得在未知发送中直接替换、重启或重发。数据库及Android卷不属于代码回退范围。

唯一需要用户后续操作的是原内容工作台的DeepSeek网页登录。用户完成后，再同步并验证GEO独立会话；当前保持登录阻塞，内容流水线原暂停标记未改变。百度继续原批次，两个豆包维持暂停，文心完成状态保持。
