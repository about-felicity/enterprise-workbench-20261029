# 盖白染发剂 HTTP 502 阻塞恢复

2026-10-29完成。目标计划plan-3224f5a2caac465a988083ae15ab0865，当日7个问题。4个阶段记录HTTP_REJECTED/502且无response.json或answer.json；普通继续原来会进入同一失败请求再次暂停。

用户明确批准原¥2预算内四个阶段各补做一次。保留旧请求、原费用预留及原16篇成稿；为对应中断阶段建立独立补做票据。新增人工触发的有界HTTP502/503/504恢复流程，同阶段最多补做一次。真实REQUEST_UNKNOWN或仍在执行的请求不适用；普通自动恢复不会重发。修复safe_original将HTTP5xx误判为可原样继续的问题。

界面将HTTP异常聚合显示，并提供“核对并补做”；保留预算与原记录的说明。38项隔离回归通过；页面状态、补做按钮、自动更新、断线恢复、移动端及知识库编辑验证通过。

最终服务端核对：状态complete，7/7个问题完成，27篇成稿，无失败文章，错误提示为空。原16篇成稿收据SHA256全部一致。已扣费及保留额度合计¥1.293181，小于原¥2上限；此值不是单独的本次补做账单。

仅部署creation/recovery.py、runtime.py、studio.py、worker.py、editorial_status.py、panel.html，并重启HTTP API。Go调度与studio服务PID保持不变。
服务器备份及恢复记录：/opt/monitor/geo-content/maintenance/api-http-recovery-20261029。各job下api/http-recovery/保留原票据、原active记录、reservation引用和替代票据映射。源码恢复快照及映射已同步。
