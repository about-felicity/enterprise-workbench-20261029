企业工作台前端精简，2026-10-27。

基于线上 Dashboard、PerformanceBoard、globals.css 修改，部署前检查源文件一致。移除企业概率监控导航入口；采用用户提供的四路径 SVG，青绿色 #43c9aa；去除页头英文、重复说明、导航副标题、筛选口径复述及重复指标说明；绩效规则改为折叠查看。

生产构建通过；预览 HTTP 校验通过后替换前端容器；7 个视图切换、采集及创作 API、资产管理入口检查通过，无浏览器 pageerror。桌面截图已核对。生产备份 /opt/monitor/maintenance/panel-cleanup-20261027，旧前端容器 monitor-dashboard-before-clean-20261027 保留以便回退。源码及发布快照已同步。
