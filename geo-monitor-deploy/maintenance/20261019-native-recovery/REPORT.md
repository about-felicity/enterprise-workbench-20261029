# 2026-10-19 豆包/元宝持续阻塞修复

## 已确认原因
豆包1第68题（昨日批次）的原生唯一首回合答案完整，message status21，全部块is_finish=true，正文360字，返回商品小程序卡片，无search_query_result_block/网页信源/网页citation。worker把所有require_sources且零sources一律改pending，永远awaiting_original_result；LegacyQueue及旧envelope也分别拒绝零信源。因此不是未收到正文，也不能伪造网页来源。

元宝App进程实际不存在；question_only_worker在android.ready/ensure_open之前调用reader.before_new_chat，其NativeClient.connect pidof失败，持续prepare_failed/CalledProcessError，进不到启动App步骤。这证明持续阻塞的程序顺序原因，未证实App此前为何退出。

## 修改
1. question_only_core增加严格source_absence_verified：原请求已确认、首回合、status21、正文/来源读取完整、raw_answer_blocks全部finish、无search块/查询/网页citation，正文与raw块一致，明确source_availability=not_provided。缺原始块、未完成、状态不符、声明有搜索但空结果等不放行。
2. LegacyQueue默认source_absence_verified仍False，只在question-only子类允许上述证明；worker及envelope走同一判断。原始商品卡片完整保留，信源数量仍0，未构造信源。两次一致EOF快照仍必需；CompletionFence包含原始块及零信源状态。
3. 元宝在基线读取前ensure_open；App启动确认app_wait最多20秒，外层75秒限时，不创建新对话或发问题。随后原基线与ready顺序保持，唯一发送意图规则不变。

## 现场恢复与验证
备份 maintenance/20261019-native-recovery/backup-1792372087 含两任务SQLite及原源码/健康/绑定。仅受影响服务安全SIGTERM，未清队列/改凭据/重建模拟器。豆包跨日daily actor在旧服务排空期间启动今天批次，旧服务重启因设备锁短暂失败（未发送）；已停止旧service的重试，今日服务持有唯一设备锁正常运行。以后不要重跑deploy.py。

旧第68题通过固定原binding只读两次一致后完成，不调用UI、不重新提问；唯一send_click_intent仍1。旧批68/68已捕获并回传（总原目标105未全跑完），原始360字/商品raw块/来源0与receipt逐项一致，source_capture_complete=true，run_id=doubao-5efda4f245363349fe75。补读回传发生10/19，不伪称10/18已完成105；昨日剩余历史保留。旧health按真实68完成更新stopped；当前设备属于今天批次。

09:11:55验证：豆包1今天新批3完成/第4题生成，另补回昨日1条；豆包2今天11条；元宝原队列恢复后3条、下一题生成，实际今天入库3；百度今天9条正常继续；文心今天waiting_for_baidu正常等待（昨天168已完成）。三原生回传errors为空。validation.json为现场证据，数值随采集增加，不代表整日已跑满。

28项回归通过：worker6/原始问题绑定9/零信源正反例2/envelope5/reliability6。补充reliability首次因缺capture_bridge模块搜索路径出现2个环境错误，补正确PYTHONPATH及geo venv后6/6通过，未部署失败轮。

当前源码恢复包102/102映射一致，新增geo_batch_bridge和yuanbao android_ui显式映射。DeepSeek的账号、worker、间隔、队列未操作，主GEO09:00和创作01:00配置不变。没有宣称永久无故障；本轮已验证根因、修复与连续真实入库恢复。

维护脚本deploy/recover_bound仅本次现场操作，禁止纳入每日调度或按硬编码批次重跑。validate.py只读生产数据并保存验证报告。
