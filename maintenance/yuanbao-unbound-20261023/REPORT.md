# 元宝提交后退出、未绑定原会话的恢复修复

核验时间：2026-10-23 10:43:27（北京时间）。原批次 `geo-panel-yuanbao-20261023-090004-d6b66215`，21题×8轮，原45秒间隔保持。

## 1. 根因与真实恢复

原批次停在12/168。第13题“推荐一款防脱精华液”09:10:40提交，Android退出记录为low_memory。App重开后在首页；当时尚未写入binding/native文件，request_id为空。已有恢复路径依赖绑定后的会话身份，因此一直等待原结果，而不会重发未知请求。

本地原生历史库已有新会话，标题为“防脱精华液选购推荐”，并不等于问题文本；旧记录中还有同名标题，不能只按标题认领答案。本轮使用提交时间窗、提交前会话基线、全局已绑定会话排除、可见历史列表顺序与唯一入口定位原会话，再由现有读取器核对原问题、首轮问答、原始时间、请求及消息身份。导航自身不认定任务成功。

第13题原会话 `0RSyGTvuBZg`，原请求 `7ea3f684ee9095b55cf3bbeb09954e14`，补读1710字、45个来源；正文SHA256为 `54bcb62650bd38d73b8dded7547113c3f321db434cf7f5e2ea7bebe7cbade4e8`。send_click_intent_committed=1、capture_retries=0，原结果已收到processed回执并入库，没有重发问题。

10:43:27真实核验：原批次22/168完成，geo_processed=22，PostgreSQL成功22；第13—22题均完成、每题点击提交一次、capture_retries=0。worker及每日控制服务active，delivery_errors为空。App PID4403存活，容器工作内存约43.4%。当前进入第23题等待发送间隔。见 verification-final.json。

## 2. 修改与保护

- `unbound_history.py`：新增未绑定原请求的历史补读。要求唯一持久提交记录、有效提交前基线、没有绑定且没有重试，**并且该任务提交后有App缺失进程重开的记录**，才可导航；正常慢回答不触发。唯一候选、UI顺序或身份不足时继续等待，不重新发送。最多两次导航，间隔至少600秒；失败探测也保存60秒退避，重启不清零。暂停、停止、草稿和错误列表阻止导航。
- `question_only_worker.py`：只在元宝prepared且结果absent时接入该补读路径，已有绑定后的历史恢复和原请求保护保留。
- `question_only_adapters.py`：补读后限制到原候选会话及原提交时间窗；发题前基线从读取全部历史正文改为只读会话ID，并纳入原生持久历史ID。
- `native_models.js`：新增仅返回标量ID的原生RPC，实际App加载验证通过。减少历史全文序列化开销；当前证据只能确认low_memory退出，不能证明原全文扫描是唯一内存原因。
- `test_unbound_history.py`：8项测试覆盖候选歧义、时间窗、旧同名标题、已绑定/重试保护、提交证据、退出证据、暂停/草稿/列表顺序、限次及持久退避。

首版上线后第14题也发生过一次历史导航，原结果完整接受且仅发送一次。最终版已增加“提交后进程重开记录”前置条件，专门防止正常未绑定的慢回答被干预。该额外条件的负例和退避恢复通过自动化测试；没有人为制造第二次App内存退出。

## 3. 测试与源码留存

- Linux实际运行依赖环境：元宝46项通过（含新增8项），共享/豆包相关38项通过，合计84项。日志 yuanbao-tests-final.log、doubao-tests.log。
- JS语法检查通过；在实际App加载候选RPC，只返回原会话ID，见lightweight-live.json。
- 真实原会话补读与后续多题连续采集、处理回执、数据库一致性已验证；不是合成结果。
- 221/221恢复源码映射与服务器SHA一致；551个唯一源码快照条目校验无错误。仅更新本轮5个文件的发布映射和快照，没有运行全量打包来覆盖未部署文章候选。
- 保留部署前源码、原任务库备份和原结果于服务器维护目录 `/opt/monitor/geo-capture/maintenance/20261023-yuanbao-unbound/`；本地仅保存非敏感源码与摘要，不复制登录数据库或凭据。两轮部署见deployment.json和guard-deployment.json。实际重启只涉及原元宝采集reader，未停止Android App、清空队列或重建批次。
- Git差异已检查；项目源码与快照保留既有CRLF字节，按cr-at-eol检查没有新增空白错误。源码SHA见final-manifest.json。

| 文件 | SHA256 |
| --- | --- |
| question_only_worker.py | ffaa12abbf8a7835b9dbe811a277db3cd7f9b2eb2ca8512bcd08e4b5f60e7695 |
| question_only_adapters.py | f01cfb70c2a827b304bc951742667d8ec52d52ada92d5a44e8f14cf0552ab477 |
| native_models.js | 9dc9fee3ee96fb39578f496fe25020b1c42ed67807d424689a8a029f614e6b2c |
| unbound_history.py | 86bfe31179d028828ed493abf337087800d6e34734b017196b67cd0452afd4d4 |
| test_unbound_history.py | aee9fe27fe6b21cb66a23a6274242e8469698c14917251a642c9425d3df8b864 |

## 4. 验证边界

本次修复已在元宝原生App和真实原批次验证，没有执行网页浏览器验收。整批168题及下一自然日无人值守仍未验收，不能保证后续永不退出。历史库缺失、候选不唯一、UI列表改变或超出原提交窗口时保持等待/待核对，不盲目重发。

未请求DeepSeek/文章API或余额API，未修改文章预算、费用账本、未知请求记录、原稿及B1/B2独立候选；文章候选没有部署。元宝继续执行用户已有的原监测批次，没有创建额外测试批次。
