# 元宝原请求卡住修复 2026年10月21日

用户要求排查并修复元宝停滞。现场是今天原批次`geo-panel-yuanbao-20261021-090004-d6fb7a84`，21问题×8轮=168，45秒间隔；初查38篇完成/入库，39题“推荐一款洗面奶”自09:36:19一次点击后停滞。

## 原因及证据

元宝原请求trace `aab7836d6728b3fee41187ab6aa438dc`、CID `0RPgFhBs0yO`，存在本地临时问答ID。临时答正文为“回答拉取失败，正在重试”，原生状态却是COMPLETED/EOF。旧解析器只按零信源返回required_sources_pending，于是无限等待。真实服务器答案`0RPgFhBs0yO_2`已经在App自身SQLite里；Markdown视图同时出现本地占位和正式答，trace相同。旧绑定只保存临时server_answer_id、没有晋升；JS readKnown还忽略调用方messageId、一直读T.h的last指针，加剧误读临时占位。

不是本次登录失效，也未观察到本次OOM；最初平台为什么产生“拉取失败”的网络细因没有足够日志，不能推断服务器断网或账号风控。确切的软件缺陷是临时ID与正式ID并存/切换时不能安全追踪原答，且错误被误归为信源尚未齐全。

证据保存在服务器`/opt/monitor/geo-capture/maintenance/20261021-yuanbao-stall`，包括原native/绑定、只读store、原UI、exact-native、SQLite备份与各版源码backup。inspect.py后来覆盖诊断快照；真正旧临时native及binding还在backup和任务.binding-promotion.json。不要因最后一次inspect看到正式答就否认早期占位故障。

## 修复

- `native_models.js`按请求的server ID读指定消息；last正好匹配走原快速路径，只有不匹配时只读定位该ID内部对象。缺失/歧义分开；不替换成其他轮次、保留原生对象不改写，不长期retain堆对象。
- `binding_recovery.py`只允许local临时ID升级正式ID：task、CID、trace、原问题逐字、内部问答pair、首问index1/首答index2、单答案、视图上下文全部一致。服务器ID之间任意替换、多轮/多变体或trace变更不接受。旧绑定及原native原样保存，晋升有独立审计。
- `native_client.py`保留原trace和internal pair完成晋升。视图有正式ID而DTMP模型尚未hydrate时保持已验证原占位pending，不误报网络传输错误、更不重问。其他RPC异常仍报错。
- `native_core.py`将已现场核实的临时“回答拉取失败，正在重试”单独识别为native_answer_fetch_failed；不视为成功正文、零信源成功或品牌未提及负样本。
- `history_refresh.py`与元宝worker分支：准备超过120秒、只处理上述已确认占位且App原SQLite存在相同CID/首轮问答/相同trace/原问题的正式记录时，按数据库实际标题导航既有历史，再回原会话刷新。标题不写死；不输入、不点击发送/重新生成。每题最多2次，每次至少600秒，动作前持久化，用户暂停/停止时不导航。没有唯一可见历史条目就保留等待，不猜测点击。
- 主采集配置、日期、任务、间隔和其他模型未修改。只重新加载元宝worker，未重启App或容器。第一次reader部署停服曾达到systemd停止超时，被systemd终止；当时是已prepared原题补读，队列/点击意图仍保留，未发生新点击。后两次是正常安全退出。

## 验证

25项元宝相关测试通过，包含已有严格原生/信源/视频/存储、临时ID身份拒绝用例、未hydrate回读、暂停/频率/次数约束和历史导航零发送。真实故障通过既有App历史导航读取原请求恢复，不重问；泛化自动导航经过模拟设备回归与真实数据库身份门槛验证，未在正在采集的新题上人为制造故障做破坏性重现，不宣称长期永不失败。

原第39题1849字符、46信源，原trace未改，send_click_intent_committed=1，capture_retries=0，无failed_attempts。真实processed回执与上游done回执一致；PG run `7fe6cd27eca5f55616c9` 的answer_raw逐字、capture_result.sources完整46项与原生一致，body/source complete均true。正文SHA `aa44ff4306332d928196260eb38b8efea97d0a9bdcf953ee3b5b1e293343e4e9`。业务规范问题名“洗面奶推荐”，原问题仍在prompt/capture_result.wire_question；不要错误地把标准化问题名当串题。

2026-10-21约11:02北京时间最新verify epoch1792551715：46/168已采集且46真实入库，运行第47题generating，delivery_errors=[]。这不是全天任务已跑完。日志证明39至46继续完成；原任务继续执行。

一次性deploy.py/deploy_refresh.py/deploy_final.py及UI导航脚本都已使用，不得日常重跑。以后只读检查真实当前批次，不把本文固定39题诊断脚本当作通用恢复器。原始缓存、登录、队列、回执未删除。
