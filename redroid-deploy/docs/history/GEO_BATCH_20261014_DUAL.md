# 两台无头豆包并行采集（2026-10-14）

后续停机修复：两台曾分别停在 13/105、67/105，现已修复并接续原批次。间隔更新为 45 秒，增加明确错误的有限退避重试、安全维护暂停和启动兼容校验；第一台的索引及 Keva 冲突也已修复。见 `DUAL_CAPTURE_PAUSE_FIX_20261014.md`，下文启动时的配置/进度作为历史记录保留。

用户在第二台恢复后明确要求另一台也开始抓取。第一台于北京时间约 16:00 启动**独立新批次**，沿用 `geo_questions.json` 的 21 个问题循环 5 轮，共 105 条；不复用旧任务 ID，不重置旧队列、GEO 数据或回执。

| 实例 | 当前服务 | 当前批次 |
| --- | --- | --- |
| 第一台 `doubao-hpe14-13-test` | `redroid-geo-products.service` | `geo-products-21x5-account1-20261014` |
| 第二台 `doubao-hpe14-account2` | `redroid-geo-products-account2.service` | `geo-products-21x5-account2-relogin-20261013` |

第一台历史批次 `geo-products-21x5-20261013` 仍是完整采集 105/105、GEO processed 105/105，所有队列及回执保留。第二台原恢复批次继续，不为并行启动而重启。

两服务均为无头 systemd 运行，账号、容器、ADB、设备锁、任务 SQLite、outbox 和 receipts 独立。每台发送间隔至少 30 秒；各自等待回答上限 900 秒。保持完整正文、全部信源、引用、搜索词和 native_result 回传；以 processed 回执计 GEO 完成，不混称后续 AI 分析完成。

第一台首题实测 217 字符正文、6/6 信源，processed 回执 run_no=42536；初次发送间隔核验 39.93 秒。新服务增加独立批次/设备环境变量和 ExecStopPost 健康停机记录。旧 unit 备份位于 `/home/user/redroid-doubao/account1-new-batch-backup-20261014/`。没有对第一台进行清缓存、重登录或原生库改动。

只读实时核查：

```powershell
python -B redroid-deploy/remote.py '/home/user/redroid-doubao/worker-venv/bin/python /home/user/redroid-doubao/check_current_dual_batches.py' --sudo --timeout 25
```

各批次状态目录 `/home/user/redroid-doubao/batches/<batch>/`。不要重复运行一次性启动脚本 `start_account1_new_batch_20261014.py`；已经入队的新批次只能接续核对，不能重新生成同题任务。断开本地窗口或 SSH 不停止服务器采集。
