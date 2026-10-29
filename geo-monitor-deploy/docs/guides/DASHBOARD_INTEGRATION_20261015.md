# 采集控制台接入 GEO 大面板

> 后续已完成公网子路径适配：[https://1any.top/geo_monitor/](https://1any.top/geo_monitor/#capture/doubao1)，真实HTTPS浏览器验证通过。当前版本、备份与回退见 [VPS_GEO_ACCESS_20261015.md](VPS_GEO_ACCESS_20261015.md)。本文保留初始内网集成记录，旧前端包不应覆盖当前前缀适配版本。

大面板入口：[http://192.168.31.106:3000/#capture/doubao1](http://192.168.31.106:3000/#capture/doubao1)。左侧“采集控制”直接展示豆包1、豆包2、DeepSeek、文心卡片、百度卡片；可在同一页面查看当前进度、processed回执、历史批次，设置下次问题/轮数/间隔，新建、暂停、继续、停止及校验登录。百度/文心不显示登录操作。

桌面在主导航内展示五通道横向切换、当前任务和下次设置双栏；手机展示全部主导航和五通道选择，表单改为单栏。其他原有采集通道放在下方折叠区，原模型分析、回答审计与企业概率监控保留。

## 接入方式

复用现有8803任务管理服务和控制台HTML，作为大面板内部的同源页面渲染，不复制任务状态或创建另一套队列。大面板服务端固定代理 `http://127.0.0.1:8803`，白名单为GET panel/status/ui及五个模型的七类控制动作；不开放任意URL、文件或接收凭据接口。

- 新同源路径：`/api/geo-capture/panel`、`/api/geo-capture/status`、`/api/geo-capture/ui`、`/api/geo-capture/control/模型/动作`。
- 原8803入口仍可独立访问，接收端Bearer Token仅留在原服务；前端不读取或输出。
- POST先校验大面板同源Origin，拒绝跨站请求，再转发既有CSRF与操作防重编号到原控制器。使用独立HttpOnly/SameSiteStrict cookie，限定 `/api/geo-capture` 路径，与独立控制台的cookie区分。
- 内嵌页面仅允许同源frame。原8803的禁止外部frame策略不修改；大面板只对白名单内部页面设置同源frame策略。
- 各模型切换同步主页面 `#capture/通道`，直接打开或刷新链接可定位对应通道，手机无横向溢出。

源代码同步到服务器 `/opt/monitor/yuanbao_monitor/dashboard/app/`：修改 `Dashboard.tsx`、`globals.css`，新增 `CaptureControl.tsx`、`api/geo-capture/[...path]/route.ts`。本地副本在 `dashboard-integration/`。后续原Dockerfile.frontend构建会包含这些文件。

## 发布与验证

使用现有前端镜像的已安装依赖构建新镜像，未升级依赖。先在3001独立预览验证，再切换3000；仅前端容器切换，原采集、接收、分析、数据库、内容工作台和模拟器无需重启。发布最终重新纳入原 `local-server` Compose 的 `dashboard` 服务，预览容器清理，避免后续Compose发现重复前端实例。

构建新增7项网关检查通过：固定上游、cookie隔离、同源请求、防重复编号原样传递、非法接口/跨站/过大输入拒绝、内部frame策略与错误处理。旧前端6项相关回归通过；旧版本本身已有1项月度文案断言失败（期待“当月已跑天数汇总”，生产页面文案已变化），先在原运行容器复现，本次未修改该断言或月度功能，构建时明确跳过这1项，不宣称旧套件全部通过。

3001预览和3000上线均用真实浏览器验证：

- 五通道状态、登录按钮显隐、问题草稿在通道间切换保留、恢复已保存设置。
- 真实同源请求到原控制器，使用空问题参数确认经过鉴权后按字段校验拒绝，未改变生产数据。
- 跨站POST被403拒绝；暂停按钮请求由测试拦截，没有真正暂停正在长测的豆包。
- 主导航往返、直达豆包2链接、1440桌面与390手机页面；无浏览器脚本错误、无水平溢出。
- 测试前后同一批次、设置版本、服务状态相同。另核对采集及内容工作台主PID/启动时间、除前端外的容器启动时间与批次进度，保持不变。

证据：服务器 `/opt/monitor/geo-capture/panel-qa/dashboard-integration-preview.json`、`dashboard-integration-live.json`、`dashboard-integration-continuity.json`，以及对应desktop/mobile截图。当前发布记录 `/opt/monitor/geo-capture/dashboard_integration_release.json`。

## 备份与恢复

发布备份：`/opt/monitor/geo-capture/backups/dashboard-integration-1792034762/`。原前端镜像保留为 `monitor-dashboard:before-capture-1792034762`；新镜像 `monitor-dashboard:capture-20261015`，生产别名 `monitor-dashboard:local`。

如需回退，先保存现场，再恢复备份中的原Dashboard.tsx/globals.css，移走本次新增的CaptureControl和API路由文件并保留副本。将原镜像重新标为 `monitor-dashboard:local`，仅对原Compose的dashboard服务执行 `up -d --no-deps --no-build --force-recreate dashboard`。不要执行整个项目的down/up，不触碰采集队列、模拟器、接收服务或其他模型任务。仅前端回退不会改变8803持久化任务状态。

两台豆包两小时长测仍由原服务/截止计时器负责，结束时只暂停登记的两个测试批次。此次大面板前端切换不构成模拟器或采集worker重启；记录长测结果时应明确这一点。
