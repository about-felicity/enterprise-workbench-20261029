# 创作专用文心、百度采集通道

2026-10-20部署。新增任务 `plan-fbb1750d49ea45cb8d3a490b44a19e32`，名称“文心＋百度专用素材采集”，使用既有创作知识库和16个独立去屑/止痒问题，每题1轮，两个渠道各16次。每天北京时间01:00执行，首日为10月20日；今天已经过01:00，部署后立即执行当日任务。任务类型仅采集，不启用收费文章生成。既有创作草稿未更改。

## 资源与数据隔离

- 全局开关 `/opt/monitor/geo-content/creation_search_pool.json`，同时要求任务settings显式设置 `search_pool=creation_only`。未选择专用池的旧任务与DeepSeek继续遵守原共享资源门禁。
- 独立浏览器互斥锁 `/opt/monitor/geo-content/search-pool/browser.lock`，独立至少60秒发送记录 `last_search.json`；不使用主GEO `search_browser.lock` 或 `search_last_start.json`。
- 浏览器profile、journal和结果均在任务自己的 `studio/capture/计划ID/days/日期/渠道/` 内。两个创作搜索渠道串行执行，先百度后文心，限制额外内存用量；可与主GEO现有浏览器同时工作。
- 新任务不再因其他主GEO采集正在运行而等待，仍按01:00日计划执行。若平台要求验证，保留原任务并显示需处理，不绕过验证。
- 仅调用现有采集CLI导出独立素材，未启动任何GEO回传bridge或receiver。创作后续按studio_plan_id取该任务的私有素材；主GEO每日配置、数据统计和执行服务未修改/重启。

## 验收

- 专用任务已在创作中心API任务列表出现，状态collecting；原有暂停/继续、编辑和进度条可用。
- 第一条百度真实结果已完整保存：907字、5条来源，正文和来源完整标记均为true。百度1/16，文心等待百度队列完成，不能称两路已全部验证完成。
- 创作health返回 `search_resource_pool=creation_only`、`geo_ingest_enabled=false`。文章任务数0，无收费写作调用。
- 8项素材回归测试通过，新增专用锁/发送记录隔离验证；共享DeepSeek仍保留资源冲突保护。
- 仅重载无活跃子任务的创作studio服务，未重载主GEO通道或旧素材服务。备份 `/opt/monitor/geo-capture/maintenance/20261020-creation-search`。
- 部署脚本 `deploy.py` 为已执行的一次性操作，不可重跑；`inspect.py`、`verify.py` 为只读核查。实际第一批进度见acceptance.json，随后会继续推进。
