# 2026-10-17 12:12 DeepSeek 第八题来源标题缺失恢复

## 已证实原因
进程active/PID3907，但状态7/63、1prepared，native_validation_backoff自11:44:44持续。只读Reader.lookup重现DataError: Incomplete native source metadata。绑定原生会话唯一首问“推荐一款美白面霜”，回答FINISHED、thinking_enabled=0、正文1035字、SEARCH FINISHED的12条来源；其中两个TONYMOLY网址原生title为空。旧reader把空标题视为整个回答无效，无限重读同一完整结果。App登录探针ready，不是掉线。

## 修复
reader.py允许已完成原生搜索结果的空/缺失/空白title：仅用该条真实URL作显示标签，保留native_title原值、native_title_missing=true、title_origin=url_fallback；raw_answer_blocks完整不变。整条结果source_metadata_complete=false/source_title_missing_count明确记录缺失，不编造文章标题，不丢信源。URL仍必须为带hostname的http(s)，非法类型/未知片段/非首问/深度思考/未完成仍拦截。
worker.py的受控DataError原因写入progress.reason，避免仅显示native_validation_backoff而隐藏具体原因。

15测试通过，新增3种原生空标题的保留与原始证据、非法URL拒绝等。正式原请求只读预验证1035字/12来源/2标题缺失/首问/模式，并验证第八题仅1次send_click_intent_committed。备份/opt/monitor/geo-capture/backups/deepseek-source-title-1792210220含原reader/worker及原生只读快照。

在已发送但原答可读的边界短暂重载DeepSeek worker及每日控制协调服务，队列前后均7completed/55pending/1prepared，不清队列、不改request、不重发第八题，不重启其他采集器或App容器。新PID44432从同一本地原答恢复第八题。不得复用本次recover.py为日常启动脚本。

## 实际验收
12:11:27第八题回读入库，12:11:47第九题635字/12来源入库；12:12时9/63、54待发，running/rate_wait，下一题预计12:30:13北京时间。第八题原始正文与raw fragments逐字段一致，真实receiver回执1035字/12条来源，仅发送点击一次。两次入库相距20秒不等于两次提问相距20秒，第八题为早先已发送回答的补读。故障导致等待超出用户20分钟目标，不称历史全程合规；全局发送时钟仍持久化保留。
79/79源码映射一致。
