from pathlib import Path
import shutil,json
root=Path.cwd();folder=root/'maintenance/project-status-20261028';archive=folder/'previous-documents';archive.mkdir(exist_ok=True)
names=['PROJECT_STATUS.md','CURRENT_PROJECT_HANDOFF.md','内容创作模块现状.md','新会话接手提示.txt','README.md','企业工作台模块清单.md']
for n in names:
 if not (archive/n).exists():shutil.copy2(root/n,archive/n)
status='''# 企业工作台：项目现状

更新：2026-10-28 15:35—15:37（北京时间）。本文以本轮服务器只读核查为准，旧文档已归档至 `maintenance/project-status-20261028/previous-documents/`，不能用旧报告中的待办或运行数量代替现状。

## 当前运行

入口：http://192.168.31.106:3000/ ，本轮 HTTP 200。工作区名称仍为“隐身浏览器”，产品名为“企业工作台”，没有迁移目录。

- 主面板、后端、资产管理运行于 Docker；`monitor-dashboard`、`monitor-assets` 均运行，`monitor-dashboard-api`、接收器、product/content worker、PostgreSQL 健康。不要用同名 systemd unit 的 inactive 判断 Docker 服务停机。
- 内容创作 `geo-content-api`、`geo-content-worker`、`geo-creation-studio` 均 active。采集、付费模型和任务调度是独立链路；服务 active 不等于所有任务完成。
- 无头 Android 模拟器、GEO 抓取分析、内容创作、知识库与图片、资产管理属于同一工作台；独立工具目录不等于都已接入菜单。

## 今日 GEO

| 通道 | 本轮核查结果 |
|---|---|
| 豆包 1 | 105/105 完成，回传处理 105 |
| 豆包 2 | 105/105 完成，回传处理 105 |
| 元宝 | 168/168 完成，回传处理 168，无本批回传错误 |
| 百度卡片 | 105 次处理完成：103 条带来源结果，另 2 条只有正文，均已回传；不能说 105 条都有信源 |
| 文心卡片 | 102/168，运行中，当前为频率等待，错误列表为空；整批尚未完成 |
| DeepSeek | 保留既有插件/回传与停用历史批次；本轮未检查账号、未恢复自动采集 |

这些是核查时刻的批次结果，不代表未来不会中断或跨日无人值守已验收。

## 内容创作

当前接口列出 19 个产品知识库、18 个计划（不等于全部启用）。以下是当前任务列表口径的成稿数，不是历史所有文件总数：

| 执行日期 | 列表任务数 | 成稿数 | 状态分布 |
|---|---:|---:|---|
| 2026-10-28 | 14 | 152 | 完成 9、待定时 2、部分失败 2、补采 1 |
| 2026-10-27 | 10 | 180 | 完成 7、素材不足 3 |
| 2026-10-26 | 11 | 180 | 完成 9、素材不足 2 |

最近已验证修复：

- 科熙本防脱精华：原分析请求 HTTP 502、没有可用答复。保留原未知请求与费用预留，建立单独补做执行；10 月 28 日现为完成，共 9 篇。
- 盖白染发剂：10 月 26 日零稿任务已自动补采，取得 4 篇有效外部素材，生成 3 篇；3 个 Word 经生产 HTTP 下载及 ZIP 结构检查通过，旧失败提示已清理。
- 自动补采已上线：每个无稿且素材不足的问题逐轮补采、合并来源、去重，重新筛选后进入写作；同时最多 2 个补采任务，共享原浏览器会话、锁和采集资源。等待间隔逐步增加至最多 30 分钟，没有以固定总轮数直接结束素材不足任务。
- 补采策略从 10 月 28 日开始，额外纳入上述 10 月 26 日染发剂任务；**没有自动追补所有旧日期任务**。已有文章的问题、API 不明请求、格式失败不由素材补采直接重跑。平台验证、预算、暂停保护仍生效。
- 写作前排除任何自有产品信源、跑题来源和重复链接；V2 至少 1 篇有效完整外部正文，旧工作流仍有 3 篇要求。按直接输出策略交付，不再等待原自动终审放行。
- 产品配图已上线：按产品匹配绑定图片，优先置于产品介绍标题下，居中等比，Word 最大 14×9cm；预览、Word、ZIP 均支持。无图时正常输出文字，补图后重新下载可生成配图版本；保留原稿及收据哈希。
- 梵玢 FBCY 植萃奢护染发剂知识库已更新在原产品记录内；新任务使用新版本，已有任务保持创建时资料快照。
- 并发架构为 Go 调度/资源槽位 + Python 采集适配与内容引擎，不能说全项目已改成 Go。常规采集与写作各支持最多 10 路，受资源、站点间隔及预算限制。

## 仍需处理 / 观察

1. 今日“防脱”已有 8 篇、“科熙本造型喷雾”已有 22 篇，但状态为 `complete_with_failures / REWRITE_V2_STOPPED`。这是部分失败，并非任务全无成果；本轮只记录，未恢复这些 API 执行。
2. 今日“梵玢防脱洗发水”已有 4 篇，另有素材问题正在自动补采检查。
3. 10 月 27 日眉毛增长液、控油蓬松洗发水、防脱精华，以及 10 月 26 日控油蓬松洗发水、眉毛，仍有素材不足；历史原因包含自有来源被排除、媒体范围限制和正文不足。
4. 文心今日批次尚未结束；自动补采仅完成本次染发剂真实闭环及 7 项针对性测试，不能声称所有任务/跨日场景已验收。
5. 本轮未重新查询 API 余额，也未核查资产误删恢复结果；不沿用旧余额或把旧请求视为已恢复。

## 证据与入口

- 本轮机器快照：`maintenance/project-status-20261028/live-status.json`（其 services 中面板 systemd inactive 只是单元查询；随后已核对实际 Docker 服务正常）。
- 最近补采发布：`maintenance/automatic-supplement-20261028/verification/{release.json,final.json}`，7 项测试通过，生产成稿下载验证通过。
- 配图发布：`maintenance/article-images-20261028/`；知识库更新：`maintenance/kb-dye-update-20261028/`。
- 当前交接：`CURRENT_PROJECT_HANDOFF.md`；模块边界：`企业工作台模块清单.md`。
- 最近源码恢复映射 270 项；本轮只更新现状文档和保存只读快照，没有部署、重启或修改任务预算。
'''
(root/'PROJECT_STATUS.md').write_text(status,encoding='utf8')
(root/'CURRENT_PROJECT_HANDOFF.md').write_text('''# 企业工作台：当前交接

更新：2026-10-28。先读 `PROJECT_STATUS.md` 的最新运行结果；旧交接已保存在 `maintenance/project-status-20261028/previous-documents/`。历史维护脚本不是待执行指令。

## 工作入口

- 工作区：`C:/Users/78567/Desktop/隐身浏览器`，PowerShell；服务器 `192.168.31.106`，时区 Asia/Shanghai。
- 内网：http://192.168.31.106:3000/；既有公网：https://1any.top/geo_monitor/（本轮未验证公网）。
- SSH 用 `python redroid-deploy/remote.py "命令" --sudo --timeout 30`；上传/下载用该工具 `--upload LOCAL REMOTE` / `--download REMOTE LOCAL`。不得输出凭据文件。
- 主面板、主后端、资产管理是 Docker 容器；创作 API、worker、studio 是 systemd 服务。先辨明服务类型。

## 代码与数据

| 内容 | 本地 | 服务器 |
|---|---|---|
| 大面板 | geo-monitor-deploy/dashboard-integration | /opt/monitor/yuanbao_monitor/dashboard |
| 创作适配、前端、导出 | geo-monitor-deploy/creation | /opt/monitor/geo-content/creation |
| 内容与采集引擎 | geo-source-card-collectors/geo_source_cards | /opt/monitor/geo-content/engine/geo_source_cards（创作）；其他采集部署按映射确认 |
| Go 调度 | geo-monitor-deploy/creation-go 及 source-snapshot 对应源码 | /opt/monitor/geo-content/bin/creation-runner |
| 豆包/元宝 | redroid-deploy、yuanbao-deploy | /home/user/redroid-doubao、/home/user/redroid-yuanbao |
| 产品、计划、补采 | 创建模块 | /opt/monitor/geo-content/studio |
| 写作任务 | 创建模块 | /opt/monitor/geo-content/runtime/runs |
| 共享费用账本 | 只按接口/维护工具操作 | /home/user/geo-editorial/runtime-api/api/costs.sqlite |

## 最新逻辑与边界

- 采集完成后自动分析、写作；每次执行保持当日计划及知识库快照，后续配置修改用于后续执行。
- 直接输出，不恢复旧自动审稿拦截；继续过滤自有产品和跑题信源，保持身份与资料来源约束。
- 自动补采入口 `creation/supplement.py`；策略 `/opt/monitor/geo-content/runtime/supplement_policy.json`；每任务 sidecar 为 studio/days/日期/plan-id.supplement-state，补采原始数据在 capture/plan-id/supplements/日期/问题摘要/round-N。由 studio.tick 调度，无稿素材问题才会重入。
- 配图入口 `article_images.py`，派生缓存 runtime/illustrated；匹配实际产品绑定，不覆盖原 approved 文档或收据。无图产品继续文字输出。
- 未知 API 发送记录不得删掉重试；保留请求、答复、费用预留。最近 502 补做是用户指定的单独恢复，不是通用盲重发策略。
- 用户曾授权未完任务每次上限 10 元、共享日上限 30 元，单篇不变；**授权不等于每个新旧任务实际配置都是 10 元**。先读具体预算，勿擅自提高或清账。
- DeepSeek 采集无需改动；写作 API 是另一条链路，不混淆。
- 仓库存在大量历史改动，部署先比对生产 SHA、备份后定点覆盖，不能整目录盲覆盖。最近 release 与 270 项恢复映射已同步；本地快照不含完整业务数据库、上传素材、登录或密钥，不是整机备份。

## 当前待办

今日两项部分失败、一个补采任务和旧日期素材不足详见 `PROJECT_STATUS.md`。最新修复的防脱精华 9 篇和染发剂 3 篇已完成，不要重新建付费任务。后续按用户具体请求读现场日志再处理，不把旧文档中的恢复/部署脚本当成授权。

本轮仅更新现状和交接，没有修改生产服务或新增写作调用。API 余额、资产误删恢复、自动化调度状态未在本轮核查。
''',encoding='utf8')
(root/'内容创作模块现状.md').write_text('''# 内容创作模块现状

更新：2026-10-28 15:35，北京时间。完整数字与未完成事项以 `PROJECT_STATUS.md` 为准，原 10 月 23 日说明已归档。

当前流程：选已有产品知识库 → 保存任务与执行快照 → 专用百度/文心采集 → 读取外部完整正文 → 排除自有、重复和跑题来源 → 分析、写作 → 直接生成文章 → 预览及 Word/ZIP 下载。采集结束自动分析，不再单设分析开始时间。

Go 负责执行并发和采集资源控制，Python 负责适配和内容引擎。常规采集与写作各最多 10 路，实际受内存、站点节奏和预算约束。

V2 使用至少 1 篇有效完整外部正文；旧工作流仍有 3 篇门槛。素材不足且该问题尚无成稿时自动追加采集轮次；新结果与已有素材合并，再走同一套来源过滤。补采最多 2 个任务并发，间隔逐步增加，复用原会话与锁。没有固定总轮数强行结案，但人工暂停、预算、平台验证和未知 API 请求仍需尊重。

补采现覆盖 2026-10-28 起任务，额外包含 10 月 26 日盖白染发剂；不代表所有历史缺稿都已自动补跑。盖白染发剂已实际补采成功、生成 3 篇，逐篇 Word 下载通过；防脱精华 10 月 28 日 9 篇全部完成。

产品图依据产品绑定自动插入产品介绍标题下，Word 居中、等比、最大 14×9cm，预览和 ZIP 同步。无图片则纯文字交付；补图后重新下载可生成派生配图版本，原稿与校验记录保留。

当前有 19 个知识库、18 个计划；10 月 28 日列表 152 篇，9 项完成、2 项待定时、2 项部分失败、1 项补采。不能以文章总数推断全部问题都完成。具体未完成项及证据见主现状文档。

核心文件：`creation/studio.py`、`materials.py`、`supplement.py`、`owned_sources.py`、`article_images.py`、`article_export.py`、`runtime.py`、`panel.html`。发布与测试记录分别位于 `maintenance/automatic-supplement-20261028/` 和 `maintenance/article-images-20261028/`。
''',encoding='utf8')
(root/'新会话接手提示.txt').write_text('工作区 C:/Users/78567/Desktop/隐身浏览器，项目名企业工作台。先读 PROJECT_STATUS.md、CURRENT_PROJECT_HANDOFF.md（2026-10-28 更新），再按用户当前问题用 redroid-deploy/remote.py 核对现场。旧文档已归档，勿按历史脚本盲恢复。防脱精华9篇、盖白染发剂3篇已完成；自动补采与产品配图已上线，但还有其他部分失败和历史素材不足。保留登录、原请求、费用预留、原稿及用户暂停；不盲重发未知API，不擅自调高预算，不输出凭据。面板/资产/主后端是Docker，创作API/worker/studio是systemd。源码快照不是完整业务数据备份。然后继续用户新请求。\n',encoding='utf8')
p=root/'README.md';s=p.read_text('utf8');p.write_text('> **2026-10-28 最新入口：运行数字、已上线功能与未完成事项见 [项目现状](PROJECT_STATUS.md)，接手请读 [当前交接](CURRENT_PROJECT_HANDOFF.md)。下文旧日期结论为历史，不代表当前任务或审稿策略。**\n\n'+s,encoding='utf8')
p=root/'企业工作台模块清单.md';s=p.read_text('utf8');s=s.replace('首页、企业概率监控','首页、各分析页（企业概率监控入口已移除）');s=s.replace('## 同目录内的其他内容','资产管理已通过 `monitor-assets` Docker 容器接入，监听服务器本地 8001；设备、员工、分配记录属于该模块，本轮未修改其数据。\n\n## 同目录内的其他内容');p.write_text('> 2026-10-28 补充核对：主面板/主后端实际由 Docker 容器运行；运行状态见 PROJECT_STATUS.md。以下更名发布描述为 10 月 26 日历史。\n\n'+s,encoding='utf8')
print('Updated',names)
