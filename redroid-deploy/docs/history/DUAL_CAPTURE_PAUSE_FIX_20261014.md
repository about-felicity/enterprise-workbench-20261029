# 两台采集停机修复与恢复优化（2026-10-14）

**北京时间 17:49 最终验收：第一台 31/105、第二台 96/105 GEO processed，两台均 running、无回传积压。已逐题验证原生当前尝试唯一性及 GEO 全正文/信源/引用/搜索词一致；新间隔实测最短 59.30/56.47 秒。** 验收文件：`test-results/dual-pause-fix-acceptance-20261014.json`。

用户核查回传时，两台分别停在第一台新批次 13/105、第二台 67/105，全部已完成数据均有 processed，delivery_errors 为空。停机发生在采集端，不是已有数据的 GEO 回传失败。

## 已确认的原因

- 第一台第 14 题留下 click intent，但没有原生请求。运行时对第一台跟踪，确认原生会话 INSERT 同样经过旧 `mmicu` 会话索引并报 SQLite code=1；会话表仍仅有迁移时的 3 行。第一台还存在两个 Keva 映射指向同一截断文件、同一 inode 的情况。旧数据使前面的任务可以工作，不能据此认定这些兼容问题不存在。
- 第二台第 68 题有服务端确认，但回答只有“出了点问题，请稍后重试。”，没有信源。此前代码将其视为普通完整回答，随后触发 Required sources are missing，让整个服务以退出码 2 停机。未观察到可以据以认定账号封禁或平台限流的明确错误码。

## 修复和恢复规则

1. 第一台会话 FTS 改为 `unicode61`，重建索引并恢复四个触发器；完整原生消息和队列备份保留。第一台也安装已经验证的 Keva openat 长路径包装，两个实例的 `.blk/.chk` 现在均为完整路径、不同 inode。没有修改 APK、登录账号或令牌。
2. 对有服务端确认、完成标记、正文**精确等于已观察到的错误提示**且无信源的回答，有限重试两次，退避分别为 90/180 秒。失败原生请求、回答及完整结果归档到 `failed_attempts`；新尝试保留原任务 ID，追加独立尝试编号，不与旧错误或迟到回答混配。只把唯一当前尝试的完整正文/全部信源回传 GEO。
3. 普通缺信源回答、未知格式或未确认发送不适用自动重试。点击意图按已归档的尝试边界分别计算；进程重启不能再次点击同一尝试。重试计数和 not_before 存在 SQLite，服务重启不跳过退避或清除历史证据。
4. 两台常规发送间隔设为 45 秒，等待回答上限保持 900 秒。发送前验证按钮存在、启用、位置稳定及输入未改变；点击返回也只记录 tap returned，以原生请求/服务端确认作后续依据。点击前失败允许有限准备重试，未知点击结果仍保护停审。
5. 启动前校验两台 Keva 修复库 SHA256，以及当前账号会话 FTS 的兼容定义。补丁被覆盖或旧索引恢复时阻止继续发送。
6. 增加安全维护暂停：写入 `maintenance_pause.json` 后，当前题先完成对账，bridge 处理完 processed 回执后退出，不开始下一题。`maintenance_control.py` 提供 pause/status/resume；pause 只请求排空，不直接杀服务或 App。设备和导出锁按作用域释放。

第一台第 14 题在确认索引故障、修复并重启同步后，由操作员进行一次独立标记的恢复尝试。第二台第 68 题的明确错误按上述规则归档并退避重试，随后取得完整正文、10 条信源和 processed。

## 维护边界的一次中断及处理

安装第一台 Keva 补丁时，停止 worker 恰逢第 21 题 click intent 已提交、tap returned 未落盘，造成发送状态不明。这次停止时机不合适，不能把查不到请求当成从未尝试。保存队列、原点击和维护备份，重启同步后仍无原生请求；由操作员做了一次明确标记的新恢复尝试，原中断证据归档，不启用未知发送的自动重发。第 21 题及随后 22—24 题均完成 processed 对账。

第二台随后在原生请求已有服务端确认的边界仅重载 Python worker，App 保持运行，同一个请求继续完成，没有重新点击发送。两台已运行支持安全维护标记的版本；后续维护使用该机制。

## 备份与验收

服务器项目根 `/home/user/redroid-doubao/` 下保留：

- `account1-fts-repair-1791968692/`：原生数据库、当前队列、旧 FTS/触发器 SQL。
- `dual-pause-fix-1791969502/`：两台当前队列/健康文件、原 worker/core/bridge/preflight/systemd。
- `account1-keva-repair-1791969980/`：Keva/数据库、原库、权限和路径 manifest、当时的在途队列。
- 各批次 `before-pause-reconcile-*.sqlite`、第一台 `before-maintenance-boundary-recovery-*.sqlite`，以及保留的 `failed_attempts` 和 events。

回滚前安全暂停并备份最新数据。不要把旧队列/数据库直接覆盖已经采集的结果，不清除 GEO 回执；原生库按 manifest 路径和权限恢复，原索引 SQL 保留用于回滚评估，恢复它会重新引入已观察到的兼容故障。

**47 项 Linux 测试通过**，覆盖重试持久化、退避/上限、拒绝重试普通缺信源或未确认结果、旧队列迁移、同一尝试禁止第二次点击、点击前控件缺失不提交点击意图，以及维护暂停先完成在途题而不发送下一题。

端到端验收 `verify_dual_pause_fix.py` 对两台的 processed 数据逐题比较 GEO PostgreSQL 正文、全部 items、citations、search_queries 与原生采集结果，并核对服务端确认及**当前尝试**只有一个请求；保留的明确失败请求不冒充重复成功数据。核对两台完整 Keva 映射、兼容 FTS 和四个触发器、有效健康状态与新发送间隔 ≥45 秒。

首个验收快照：第一台 20/105（第 14 题起连续 7 题），第二台 77/105（第 68 题起连续 10 题），新发送实际最短 59.30/57.19 秒。维护边界恢复后另核验第一台第 21—24 题成功、第二台继续至 89/105。最终实时数量以 `dual-pause-fix-acceptance-20261014.json` 为准；临时 Frida 监听和诊断转发已关闭。

第一台历史批次始终保留 105/105 processed；当前两批各自仍为原定 105 个任务，没有把历史批次重新入队。scrcpy 保持关闭。processed 仅证明入库，不把 ai_pending 混称分析完成。

实时检查：

```powershell
python -B redroid-deploy/remote.py '/home/user/redroid-doubao/worker-venv/bin/python /home/user/redroid-doubao/check_current_dual_batches.py' --sudo --timeout 25
```

安全维护（选定其中一个当前 batch）：

```text
worker-venv/bin/python maintenance_control.py <batch> pause
worker-venv/bin/python maintenance_control.py <batch> status
# 等 status 显示 drained=true，再修改或重启 App。
worker-venv/bin/python maintenance_control.py <batch> resume
```

这些恢复/修复脚本带特定现场断言，已经执行过的脚本不应再次运行。
