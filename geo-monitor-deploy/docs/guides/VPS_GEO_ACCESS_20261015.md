# VPS 公网 GEO 采集控制适配

入口：[https://1any.top/geo_monitor/](https://1any.top/geo_monitor/#capture/doubao1)。保持原有GEO网站登录，登录后左侧“采集控制”可在公网访问五个通道。LAN根路径和原8803控制台继续可用。

已于北京时间2026-10-15 11:55左右部署，11:56完成真实HTTPS浏览器校验。最终报告 [vps-geo-control-report.json](../../reports/20261015/vps-geo-control-report.json)，进程连续性报告 [vps-access-continuity.json](../../reports/20261015/vps-access-continuity.json)。

## 已确认的问题

原SSH隧道已将VPS13000转到LAN3000，18765转到LAN8765，站点通过 `/geo_monitor/` 反代访问。此次不增加端口或重启隧道。

旧路径下所有 `/geo_monitor/api/` 均转到分析服务8765，并带共享短时缓存；新采集控制接口实际在前端3000，其原路径及cookie限定在根路径 `/api/geo-capture`，主机校验仅允许内网。直接经域名和子路径访问会出现上游、前缀、Cookie路径与HTTPS Origin不匹配，不能仅添加页面链接。

## 实现

- 新增VPS专属 `location ^~ /geo_monitor/api/geo-capture/`，保留既有 `auth_request /geo_monitor/_auth`，直接转发原13000隧道至前端3000网关。
- 此location禁用proxy_cache、共享缓存与自动上游重试，标记 `X-Geo-Control: live`；原分析API的短时缓存保持原配置，其他站点配置不修改。
- 转发固定Host、HTTPS和 `/geo_monitor` 前缀；网关只允许固定域名 `1any.top`，要求指定的HTTPS转发前缀及同源Origin，原CSRF和防重复操作编号继续传给既有8803控制器。
- 公网控制Cookie为HttpOnly、Secure、SameSiteStrict，Path限定 `/geo_monitor/api/geo-capture`。不共享不同浏览器的控制会话。
- 前端基于当前pathname适配 `/geo_monitor` 前缀，iframe、状态/控制API、独立窗口及主分析请求均保持同源子路径，不使用公网浏览器访问内网端口。
- 只给GEO根页面缓存键增加版本，确保新HTML引用新前端资源；登录保护、原分析API及资源缓存行为保留。

## 验证范围

新增共11项网关检查通过，旧相关6项回归通过。旧月度文案断言仍按已记录的历史基线跳过，不冒充原套件全部通过。新版先在LAN3001验证，随后通过原Compose仅更新dashboard服务，再对VPS执行 `nginx -t` 和平滑reload。

真实访问 `https://1any.top/geo_monitor/` 后验证：

1. 未登录首页仍跳到原登录页，未登录控制API仍返回401。
2. 登录后五通道状态加载，豆包2直达链接、各通道切换、原有登录校验按钮显隐正确。
3. 真实写请求携带公网Cookie、CSRF和Origin到达原控制器，使用空问题列表确认按字段校验拒绝，生产设置不变。暂停按钮另用请求拦截验证公网路径，未实际暂停长测。
4. 跨站POST被403拒绝，控制API不返回HIT/STALE缓存，两独立浏览器上下文获得不同控制CSRF会话。
5. 1440桌面及390手机页面无脚本错误、无横向溢出；独立窗口也使用同源前缀URL。
6. 从控制页返回总览，主分析API仍请求 `/geo_monitor/api/analytics`，未落到域名裸端口。

校验使用现有站点账号的10分钟临时签名会话，仅在测试进程内存中使用，结束后关闭浏览器；没有修改账号、密码、认证密钥或登录策略，未输出会话凭据。现有认证脚本包含顶层监听，校验器只加载其认证定义并排除监听语句，不启动第二个认证服务。

部署前后：原采集/内容工作台及SSH隧道主PID与启动时间不变，除前端外的容器启动时间不变，当前五通道批次不变且计数持续增加；两台豆包两小时测试继续。测试没有新建或重发采集题目。

## 备份与部署位置

- LAN源代码：`/opt/monitor/yuanbao_monitor/dashboard/app/`，新增 `dashboardPaths.ts`，更新Dashboard、CaptureControl及白名单API网关。
- LAN备份：`/opt/monitor/geo-capture/backups/vps-prefix-1792036453/`。
- 原前端镜像：`monitor-dashboard:before-vps-prefix-1792036453`。
- 新镜像：`monitor-dashboard:vps-prefix-20261015`，生产别名仍为 `monitor-dashboard:local`。
- LAN发布指针：`/opt/monitor/geo-capture/vps_frontend_release.json`。
- VPS配置：`/etc/nginx/nginx.conf`，仅GEO段新增独立控制location与根HTML缓存版本。
- VPS备份：`/root/geo-monitor-access-backups/1792036519/nginx.conf`。
- VPS发布记录：`/var/lib/geo-monitor-control/release.json`。
- 当前前端源码包：`dashboard-vps-prefix-20261015.zip`；操作脚本见 `deploy_vps_frontend.py`、`vps_geo_access.py`、`check_vps_geo_access.py`。旧dashboard-integration包是公网前缀适配前的历史版本，不能覆盖部署。

恢复时先保留故障现场，只还原对应GEO段/该前端版本，再对nginx做配置校验后reload；前端仅使用原Compose的dashboard服务 `--no-deps --no-build --force-recreate`。不要对整个Compose执行down/up或修改采集任务状态，也不要重启SSH隧道、模拟器、接收服务或分析worker来回退页面。

截图：[桌面](../../reports/20261015/vps-geo-control-desktop.png)、[手机](../../reports/20261015/vps-geo-control-mobile.png)。这里只验收访问与控制链路，不代表DeepSeek登录已恢复、产品分析积压已解决或双豆包两小时测试已结束。
