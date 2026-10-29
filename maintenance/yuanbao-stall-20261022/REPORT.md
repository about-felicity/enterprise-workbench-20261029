# 元宝第6题停滞修复（2026-10-22）

当前生产批次：`geo-panel-yuanbao-20261022-090005-705819fb`，21个问题×8轮，45秒间隔。09:16检查时5/168完成并入库，第6题从09:04起没有推进。

## 原因与恢复

第6题原请求CID `0RRIw2HvYau`、trace `6679b5f4b1f33941c35d64b60792068a`。App模型的Message和Content均为`INTERRUPTED`，isBusy=false、isEof=false，正文是“已暂停生成。”，页面另有“加载失败，点击重试”。旧解析器把所有非COMPLETED状态统称pending，worker因此长期显示“生成中”；昨日仅处理local临时ID拉取失败的恢复分支不覆盖这种正式服务器ID的中断。最初网络中断的具体原因没有足够证据，不能推断账号风控、OOM或服务器断网。

原CID当时只有ChatConversations索引，ChatMessages/Content/Detail尚未落入App SQLite，不能依赖“数据库里已经有完整答案”才能补读。App抽屉已经显示原历史标题。维护期间仅导航既有历史，再返回原会话，服务器原答成功加载；没有点击发送、继续生成、重新生成或“加载失败”按钮。

原第6题最终1603字、43条信源，trace不变，send_click_intent_committed=1、capture_retries=0、无failed_attempts。processed回执与接收端done回执一致；PG run `66fbcc2e011990d1e520` 的原文、43项完整信源、原问题与批次逐项一致，body/source complete均true。正文SHA256：`b12e26095a4b468a8c4b88f22712e1dbeef8820cc8d28a4129d55ca0d8eb2e12`。

## 通用代码优化

- `native_core.py`区分空闲的INTERRUPTED状态，显示等待补读原历史；不把中断文本当完整答案。
- `native_models.js`新增只读Session CID/title读取；`native_client.py`固定原trace，正式服务器ID补读同样拒绝trace变化。
- `history_refresh.py`沿用严格SQLite证明，并为中断状态增加原生Session标题证明：task、CID、trace、问题、首轮问答内部pair、服务器索引1/2、单答案与标题唯一性均须通过。无证明不导航。只打开既有历史，每题最多2次，相隔至少600秒，失败证明探测至少60秒退避，跨重启保留。
- 导航前须看到原问题且编辑框无草稿。问题滚出屏幕会推迟补读，不猜测点击。此时不消耗导航次数。
- `question_only_worker.py`接入中断恢复；区分控制器“只排空原请求”的内部标记与真正的用户暂停/停止。用户暂停仍不自动导航。
- 面板补充原历史等待、重载及历史暂不可见的中文状态。

以上逻辑没有写死产品、问题或历史标题。仅维护诊断脚本固定本次批次与原请求，不得日常重跑。

## 验证与限制

生产环境32项元宝测试通过（包括3项原生存储测试）；新增覆盖中断识别、错误问题拒绝、Session标题歧义、trace改变拒绝、未落盘历史证明、暂停/草稿保护和导航限次。实际App只读Session接口能准确返回原CID/title。JavaScript经实际Frida加载执行。

保存的中断快照在完整答案页面上做自动导航重放时，原问题不在可视区域，保护条件返回None；未据此声称“自动导航真实故障全链路已验证”。这次原会话的实际恢复用了维护导航，通用自动导航的动作与限次通过模拟设备回归。不能承诺平台以后永不中断，也未完成跨日无人值守验收。

09:34核验：8/168已采集且8条真实入库，第9题等待发送间隔，delivery_errors=[]；6、7、8题连续完成。后续最终进度以服务器`verification.json`为准，不能把此时间点当全天完成。

原始快照、UI、日志、部署备份及验证JSON在服务器`/opt/monitor/geo-capture/maintenance/20261022-yuanbao-stall`。只重载元宝worker，未清登录、队列、App数据或重启容器；临时systemd runtime mask已经解除。文章测试任务保持暂停，三笔原未知付费请求未重发。

09:37最终核验：11/168采集及入库，第12题已进入发送，delivery_errors=[]；6至11题连续完成。170/170恢复映射与服务器SHA一致，475份源码快照校验通过。
