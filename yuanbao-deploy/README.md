# 元宝无头采集

当前运行信息（2026-10-23）：原批次为 `geo-panel-yuanbao-20261023-090004-d6b66215`，21题×8轮、45秒间隔；RAM上限4GiB、RAM与swap合计6GiB，资源策略见 [container_resources.json](config/container_resources.json)。视频卡片在视图中缺失、但同一原请求的原生数据库记录完整时，已支持严格身份校验后的只读补齐；视频仍单独审计，不作为文字成功。见[本次修复与真实核验](../maintenance/yuanbao-recurrence-20261023/REPORT.md)。下段开通验收和文末长测时间为10月15日历史记录。

2026-10-15，用户已完成元宝官方微信授权与手机身份校验。投屏已按要求关闭，模拟器和采集在服务器后台运行。验收批次 `geo-yuanbao-21x5-20261015` 沿用21题、5轮、45秒间隔，完成15题且全部processed后正常排空保留。随后按此前授权启动六通道共同长测，元宝当前为 `geo-panel-yuanbao-20261015-172455-b45ba5d3`；21题20轮仅作两小时容量，面板下次任务默认仍是5轮45秒。没有重复发送旧批次任务。

验收时连续3题均完成原生EOF、GEO processed与PostgreSQL保真核验：正文5041字、全部97条信源、24处引用，三个独立新会话，最小发送间隔52.803863秒，无重复发送／会话。[脱敏验收数据](reports/YUANBAO_CAPTURE_ACCEPTANCE_20261015.json)。processed表示采集数据接收入库，不表示后续产品／信源AI分析已完成，也不构成两小时稳定性结论。

## 控制入口

- [内网大面板](http://192.168.31.106:3000/#capture/yuanbao)
- [公网大面板](https://1any.top/geo_monitor/#capture/yuanbao)，沿用现有站点登录。
- [独立控制台](http://192.168.31.106:8803/#yuanbao)

六通道共用设置、新任务、暂停、继续、停止、登录校验。设置仅作用于下次新批次；暂停等待当前题和processed回执收尾。未知发送进入待处理，不能通过继续按钮重发。文心／百度无需登录。元宝登录探测只读取当前App页面，不发送问题；服务端是否接受会话以真实采集为准。

内网预览和真实HTTPS子路径均完成浏览器验证：六通道显示、元宝问题列表、CSRF／Origin校验、无副作用的无效参数请求、隔离继续按钮、桌面与390px布局。只更新控制后台和大面板前端；其他采集、分析、内容工作台、SSH隧道和Android容器未重启。

## 运行位置

| 项目 | 当前值 |
|---|---|
| 服务器目录 | `/home/user/redroid-yuanbao`，私有权限 |
| 容器／独立数据卷 | `yuanbao-hpe14-android13` / `yuanbao-hpe14-android13-data` |
| Android／限额 | Android13、Houdini14；2 CPU、4GiB RAM；RAM+swap合计6GiB |
| ADB | 服务器回环5559，Windows SSH转发回环15559 |
| 官方包 | `com.tencent.hunyuan.app.chat`，2.88.0，66517035 |
| APK SHA256 | `b2d6f674358bbc27b10e800bafd49ba4fc596291142148d7d09494097348c7dd` |
| 当前采集服务 | `geo-native@geo-panel-yuanbao-20261023-090004-d6b66215.service` |
| 登录网页兼容 | `geo-yuanbao-wechat-qr-compat.service` |

安装包为[腾讯元宝官网](https://yuanbao.tencent.com/)本次实际分发的中国渠道5040版本，系统及App均为简体中文。没有复制豆包账号数据。Windows `open-yuanbao.ps1` 仅在用户需要交互时手动投屏；正常采集不启动它。

## 原生采集与回传

`android_ui.py` 通过App正常按钮新建对话、验证输入框、单次点击发送；复用豆包 `unattended_core.Queue` 的发送前持久化、唯一任务编号、点击意图和未知发送保护。另加设备互斥锁与跨批次发送时间记录，最低30秒，当前45秒。恢复跳过完成题，保留历史证据。

2.88.0实际使用DTMP聊天引擎。早期找到的明文旧表和Java WCDB迁移表没有写入新消息，不能作为采集来源。`native_client.py` / `native_models.js` 只读调用App已加载的原生查询接口，读取原生问题、成对回答、内容、全部实体及会话状态。以精确APK摘要锁定602个模型字段映射，升级不匹配时拒绝继续。

完成条件同时要求：唯一任务问题一致、HUMAN／AI配对一致、原生COMPLETED、内容EOF、会话非busy、实体数量完整、信源数量与原始JSON及界面声明相符、每个引用能映射到全部信源。保存完整Markdown、全部信源和原始模型；富卡片原始替换元数据在EOF再取最终快照。未知实体或多回答变体直接待核验，不以截图片段冒充完整正文。

当前接口**没有暴露原始搜索词**，明确记录 `search_queries_exposed=false` 和空数组，不把题目或信源标题冒充搜索词。

`delivery.py` 固定回传到现有GEO元宝接收端，凭据只在内存使用；outbox内容及请求身份冻结，相同身份重试，核对processed回执的正文长度、全部信源和完整性标记。`tools/audit_capture.py` 额外核对PostgreSQL原始接收记录的正文／全部信源／引用／原生结果等。GEO按既有配置规范化问题标签，原始prompt和带任务编号的问题仍保留。

进程意外退出时保留原任务、点击意图和会话绑定；若历史不能重新读取，停止并等待核验，不盲目重发。正常暂停通过批次 `maintenance_pause.json` 排空，健康文件写入终态，避免过期running。

## 登录兼容修复及回退

微信SDK已返回二维码，但QBar样式解码没有返回。当前只对`Up.m`调用的同步QBar解码提供App原有失败回退，显示原始SDK二维码；不修改签名、图片内容、授权回调。最终运行版本**没有全进程ART去优化**。X5内核渲染子进程反复退出，磁盘禁用配置又被SDK覆盖，现通过官方 `QbSdk.forceSysWebView()` 在WebView构造前回退系统WebView。

平台要求的身份验证由用户在手机完成；没有代做人脸验证、修改结果或绕过平台校验。底层QBar原生指令故障和服务端风险触发原因未被证明，不把推断写成根因。

兼容服务锁定独立容器／卷、版本及摘要，诊断端口仅回环。回退：先排空采集，停止并禁用兼容服务，正常退出重开元宝；运行时调整即解除，保留账号数据。不要恢复旧整份偏好覆盖成功登录。历史失败日志、备份和原X5文件仍留在私有diagnostics／compat中，见[历史现场](docs/LOGIN_DIAGNOSIS_HISTORY_20261015.md)；其中等待登录与ART去优化属于当时状态。

控制接入备份：`/opt/monitor/geo-capture/backups/yuanbao-panel-1792054779`；前端备份：`yuanbao-frontend-1792055509`，旧镜像标签`monitor-dashboard:before-yuanbao-control-1792055509`。仅回退对应文件／前端镜像；不要恢复旧队列数据库覆盖后续结果。`tools/install_*`是带现场断言的一次性部署记录，不应直接重复运行。

原生解析／回传7项、控制后台12项、网关12项测试已通过；镜像构建运行既有前端6项测试通过（沿用已有单项跳过规则）。目前验收覆盖真实连续样本和前后端接入，长时间全通道采集需独立实测。

六通道长测 `all-channel-soak2h-1792056244` 于北京时间17:24:53.95启动，19:24:53.95仅对六个本测试批次请求排空暂停，独立deadline timer已启用；supervisor与当前指针在 `/opt/monitor/geo-capture/all_channel_soak_current.json`。已设置15分钟复查，正常无变化不通知，最终报告后停止跟进。启动时两个豆包遇到重复通知权限框的不同拒绝按钮，已保留零发送证据后安全恢复；记录器对元宝可选失败表的错误假定也已修复，原异常保留。不能提前宣称六通道无故障连续两小时通过。详见[长测记录](../geo-monitor-deploy/docs/operations/ALL_CHANNEL_SOAK_PREPARATION_20261015.md)。
