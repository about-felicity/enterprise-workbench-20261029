# 公网入口旧页面缓存修复（2026-10-17）

用户实际访问`https://1any.top/geo_monitor/`，截图为带夸克的旧采集工作台。本地3000在线，生产镜像仍是creation-workflow-20261016（ecb5660d96fe），没有回滚；采集API正常，公网VPS的13000反向隧道也能直接取到新版。

通过沿用原鉴权的短时测试会话分别比对：内网及VPS直连隧道引用Dashboard-uloUm694.js/index-8PoEqwQi.css，公网首页却引用Dashboard-828cJjD3.js/index-D2U38PmX.css，说明公网代理返回了旧缓存HTML，不是用户看错入口或本地镜像回滚。原Nginx GEO根location仍启用geo_monitor_frontend共享缓存、固定creation-prefix-v3 cache key、后台更新和过期内容兜底，并忽略上游Cache-Control；响应对浏览器却声明no-store，导致仅看响应头误以为完全没有缓存。

只在VPS`location ^~ /geo_monitor/`内把`proxy_cache geo_monitor_frontend`改为off，增加live-no-shared-cache诊断头，保留鉴权、隧道、上游离线兜底、API独立location及其缓存策略。备份`/root/geo-monitor-access-backups/20261017-frontend-cache-1792199866/nginx.conf`，Nginx配置检查后仅平滑reload；没有修改本地容器、任务配置、账户或采集进程。

修复后同一公网首页立即引用与内网一致的新JS/CSS；公网真实Chrome验证六通道、每日六张任务卡、05:00、无夸克侧栏、旧工作台默认隐藏；内容创作Word知识库、每日任务配置、01:00以及94篇成稿均可访问。桌面/390px检查及浏览器错误记录在服务器`/opt/monitor/geo-capture/maintenance/20261017-public-entry/qa-public.json`和截图。测试禁止真实控制POST，仅正常读取GET；不将GET `/api/control/status`误报成写操作。

用户刷新原公网标签即可获得新版本，必要时Ctrl+F5。后续每次发布必须验证用户实际公网入口和HTML资源版本一致，不能只验证内网3000。不要重新套用旧Nginx缓存配置或盲目重跑旧发布脚本。
