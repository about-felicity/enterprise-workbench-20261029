# 第二台恢复记录（2026-10-14）

后续运行及恢复优化见 `DUAL_CAPTURE_PAUSE_FIX_20261014.md`：第二台第 68 题明确临时错误已归档并退避恢复；第一台也修复相同兼容问题。当前间隔 45 秒，并增加持久化有限重试和安全维护暂停。本文以下记录第一次恢复现场，进度不是实时快照。

**最终复核：北京时间 15:52，16/105 完整正文及全部信源已取得 GEO processed，服务 active、健康快照有效，第 17 题正在处理。最短发送间隔 36.94 秒。前 16 题逐题核验：当前库各一个请求、均有服务端确认，GEO 存储正文/全部信源/引用/搜索词与原生结果完全一致。** 本地验收文件：`test-results/account2-recovery-acceptance-20261014.json`。

北京时间 15:30 已连续验收首 7 题 GEO processed；第二台服务 active、继续原 105 题批次。第一台仍为 105/105，未重跑。此文更新交接文档的“尚未修复”状态，历史交接与失败证据保留。

后续稳定性核查：首 14 题 processed 后，第 15 题触发原先 300 秒等待上限并自动停机；核对发现同一已确认请求后来取得完整正文及 11 条信源。`resume_account2_late_answer.py` 保存队列备份、保留 needs_attention 历史事件后，直接完成现有回答的对账，**没有重发**。第二台独立设置 `DOUBAO_ANSWER_TIMEOUT=900`，服务已恢复；发送间隔仍为至少 30 秒。停机时健康文件准确记录了 needs_attention、worker_exit=2，没有遗留 running。

## 定位结果与证据边界

发现并修复了两个故障，不能把它们混成未经验证的单一因果链。

1. **长文件路径在当前 Houdini 的 ARM64 系统调用转译链路被截成 256 字节。** `probe_arm_openat.py` 使用自己编译的 ARM64 ELF 直接执行 openat，不使用 Keva、ARM libc 或账号数据。240、255、256 字节路径正常；270 字节的 `.blk/.chk` 被截成同一路径。strace 记录宿主 openat 收到 256 字节路径；同环境原生 x86 touch 能创建 270 字节完整路径。这确认了截断发生的层级，尚未定位 Houdini 内部具体机器指令。
2. **会话落库另被旧会话全文索引链路阻断。** 运行时跟踪确认：SDK 账号是当前账号，服务器返回 AVAILABLE、未删除的真实会话；DAO 的 39 列 INSERT 与表结构一致，但返回 SQLite code=1。旧 `fts_im_conversation` 使用 `mmicu`，四个触发器把会话 INSERT/UPDATE/DELETE 连到该索引。应用启动会重建这四个触发器。在运行后仅隔离这四个触发器，同一次官方 SDK 拉取成功落库，会话数从 0 变 1。将会话索引换为内置 `unicode61`、重建索引并恢复四个触发器后，重启与原生拉取均成功，会话继续增长。可确定旧 mmicu 索引与当前原生写入连接不兼容；原生日志仅给出通用 code=1，未直接取得其 sqlite3_errmsg 的详细分词器错误，不能把宿主 Python 的 `unknown tokenizer: mmicu` 当作原生错误原文。

Keva 修复后仍未恢复发送；定位并修复第二项后，原失败消息原生重试成功，随后新任务连续成功。因此“只修长路径就已解决发送”是不成立的。

## 可恢复修复

- 第二台已安装库的 `libkeva.so` 仅修改 MappingFile::Load 的 open 调用点 `0x32904`，转到 `0x5ec00` 的 276 字节 ARM64 包装。短路径沿用原 open；长路径以目录 fd + basename 调用 openat。未修改 APK、ARM libc、Houdini 或第一台库。
- 原库 SHA256：`0c63f1733430c9ca012fdaa547efe515899076819e64186a4c1e76afe05a26b4`；修复库 SHA256：`dab31cd9e76eefbdc72502108029d181fbccca5e1304816c472d6c8373f9117c`。`runtime_preflight.py` 只对第二台增加该库校验，补丁被覆盖时阻止发送。
- 当前完整缓存路径 269 字节，`.blk/.chk` 分别映射 8192/4096 字节、不同 inode。截断残留文件仍保留，未清除缓存、登录或历史消息。
- 会话 FTS 改为 `unicode61`，四个同步触发器已恢复。消息全文索引未改。会话标题的中文分词/搜索行为可能与原 mmicu 不同；采集使用唯一任务编号及原生结构正文精确关联。
- 健康桥接新增 SIGTERM/finally 停机记录、worker 退出信息、进程标识与 45 秒心跳有效期；第二台 systemd 增加 ExecStopPost，停止后写 stopped。`check_two_accounts.py` 同时核对实际服务及快照有效期，避免将过期 running 当作实时状态。

服务器备份（均位于 `/home/user/redroid-doubao/account2/`，私有权限）：

| 备份 | 内容 |
| --- | --- |
| `openat-repair-1791959111` | 原 Keva 库、Keva/数据库/登录偏好、队列、旧健康文件、权限与库路径 manifest |
| `bridge-stop-fix-1791959280` | 原桥接/测试/systemd、过期 running 健康文件 |
| `conversation-fts-isolation-1791962284` | 原数据库、四个触发器恢复 SQL；启动后触发器被重建，第一次隔离未生效 |
| `conversation-fts-isolation-1791962374` | 启动后隔离前数据库与恢复 SQL；本次验证落库恢复 |
| `conversation-fts-repair-1791962496` | FTS 迁移前完整数据库和原索引/触发器 SQL |

回滚前先停第二台服务、备份**当前**数据库及队列，然后 force-stop 第二台 App。库可按 `openat-repair-1791959111/manifest.json` 的路径、所有者和权限恢复原库。原索引定义与完整数据库快照均保留；恢复旧索引会重新引入已观察到的写入故障。不要直接用旧数据库覆盖新采集数据，不要重置已完成队列或 GEO 回执；如需完整回到旧现场，先另存当前 sandbox/队列/回执。第一台不参与回滚。

## 防重复与验收

首题旧原生请求 `c10c6d72-e1be-4776-a36c-de9f25144bf8` 在交接前数据库备份中为 status=12、message_id=null、server_index=0；当前库无此任务请求。保存队列备份和审计事件后进行了唯一受控恢复，形成 `c47f2d74-642f-4c93-9745-b0fe2c5fbfec`。当时只修 Keva，仍失败；服务再次暂停，保留该请求。

FTS 修复并重启验证后，只点击已观察到的 `com.larus.nova:id/retry`，对这个既有请求原生重试，保留相同 local_message_id。队列的旧失败点击、恢复、重试事件均保留，prepared 未批量重置。后续由既有 worker 按队列继续，至少 30 秒间隔。

15:30 验收：首 7 题连续 processed，正文长度 342/325/267/319/412/339/277 字符，全部信源数 5/5/6/12/5/11/12；实测最短成功恢复后发送间隔 37.80 秒。验收逐题将 GEO PostgreSQL 的完整正文、items、citations、search_queries 与原生采集结果精确比较，同时检查 processed 回执的 answer_present、source_capture_complete、expected_source_count。采集数可短暂领先 processed 数，以回执为准，不把 AI pending 当作分析完成。

41 项相关单元测试通过；原生补丁探针、实际重启、会话落库与连续业务/GEO 验收均通过。scrcpy 进程数为 0，临时 Frida 监听及 ADB 转发已关闭。剩余任务继续由 `redroid-geo-products-account2.service` 无头执行，断开 Windows/SSH 不影响服务。

只读实时检查：

```powershell
python -B redroid-deploy/remote.py '/home/user/redroid-doubao/worker-venv/bin/python /home/user/redroid-doubao/verify_account2_recovery.py' --sudo --timeout 25
```

服务器验收记录：`account2/recovery-acceptance-20261014.json`，会被最终复核更新。修复/恢复脚本是带现场断言的一次性工具，不要重跑 `recover_account2_rejected_task.py`、`retry_account2_repaired_native.py`、`resume_account2_late_answer.py` 或旧清缓存脚本。

参考：[SQLite 官方 FTS 文档](https://www.sqlite.org/fts3.html#tokenizers)；故障结论以上述本机探针和实际运行证据为依据。
