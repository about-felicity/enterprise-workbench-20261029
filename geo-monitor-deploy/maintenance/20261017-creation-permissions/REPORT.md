# 01:00专用采集启动失败与权限修复（2026-10-17）

用户询问后检查实际日志，确认首次凌晨任务并未采集成功：01:00:01已由runuser启动CLI，但三模型日志均报PermissionError，任务数据库没有创建，DeepSeek0/16。此前只验证root API/界面与权限夹具，没有验证真实user跨所有生产父目录的访问，漏掉该故障；不能把服务active或等待主GEO当作凌晨成功。

根因两层：`/opt/monitor/geo-content`是root:root0700，采集user无法穿越；`materials/days`由服务UMask0077隐式创建为root0700，即使具体day/model/collector子目录已属user0700也无效。01时段失败后05:00主GEO开始，私有服务进入waiting_for_geo，遮住了先前启动错误。DeepSeek主监测另有真实login_required（昨日44/63，剩19、今日0/63），不能将两种原因混为登录。

修复只作用私有采集路径：新collector_directory在每次创建运行目录时校正所有私有祖先user0700；对geo-content基目录仅赋collector组穿越权限，变root:user0710，不允许user列目录，不开放其他用户。原runtime/private数据仍root0700、凭据不改；拒绝越界和符号链接路径。覆盖多个产品的studio/capture祖先，避免同类隐式父目录权限重复出现。

真实user(uid1000)隔离回归：在root0700父目录/UMask场景下可以写/读collector探针，不能列父目录、不能读其他私有runtime，拒绝越界，无浏览器和收费调用。16项素材/每日编排回归通过。生产三模型collector路径逐个由真实user写/读/删除探针通过。只在active_channels=[]时重启创作素材服务；主六通道和原创作worker PID/启动时间全部未变。

修复后仍遵守错峰：当前文心主采集中，专用服务waiting_for_geo，不抢账号、不强行发新题。专用DeepSeek仍需重新登录后才能真正采集。0/16未被改成完成、未知题未重发，旧44/63原队列保留。尚未在实际平台产生补采成功，不能称凌晨任务已补跑完。服务器证据maintenance/20261017-creation-permissions/release.json；verify.py为真实uid回归，materials.before.py为备份。源码包67项更新。
