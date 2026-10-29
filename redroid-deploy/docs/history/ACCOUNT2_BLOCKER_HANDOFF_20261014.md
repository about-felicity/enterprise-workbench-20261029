# 第二个无头豆包模拟器：故障与进度交接

> 后续更新：2026-10-14 15:52 北京时间，已修复并验收首 16 题 GEO processed，第二台无头继续原批次。见 [恢复记录](ACCOUNT2_RECOVERY_20261014.md)。以下保留原交接现场及失败证据，不再代表实时状态。

更新：2026-10-14，北京时间。用户要求本轮停止继续排查，写清近况，供新 Codex 对话接手。**第二个账号尚未修复，当前没有继续采集。** 本文记录当前现场；其他旧文档中的“运行中”不能代替实时核查。

## 1. 用户目标与授权

两个独立无头 Android 豆包账号分别执行相同配置：`geo_questions.json` 中 21 个产品推荐问题，循环 5 轮，各 105 条，发送间隔至少 30 秒。必须回传完整正文、全部信源、引用和搜索词到现有 GEO 面板分析服务。登录完成后关闭 scrcpy；不得因为排查第二台重跑或修改第一台已完成的数据。

用户已多次重新登录第二台，并确认对应账号在手机豆包能正常回答。后来登录的账号与第二台最初的账号不同，不要再用历史失败消息的发送者代表当前账号。

## 2. 当前真实状态（交接前刚核查）

| 项目 | 第一台 | 第二台 |
| --- | --- | --- |
| 容器 | `doubao-hpe14-13-test` | `doubao-hpe14-account2` |
| 数据卷 | `doubao-hpe14-android13-data` | `doubao-hpe14-account2-data` |
| ADB（Linux） | `127.0.0.1:5557` | `127.0.0.1:5558` |
| systemd 服务 | `redroid-geo-products.service` | `redroid-geo-products-account2.service` |
| 当前批次 | `geo-products-21x5-20261013` | `geo-products-21x5-account2-relogin-20261013` |
| 采集与回传 | **105/105 完整采集、105/105 GEO processed 回执** | **0/105，prepared 1、pending 104** |
| 服务状态 | inactive，正常完成，worker_exit=0 | **inactive，排查期间主动停止** |
| 当前账号 UID 尾号 | `385833` | `066524` |

第一批实际最小发送间隔 33.20 秒。GEO 的 processed 证明正文和信源已接收入库，不代表所有后续 AI 产品分析已完成；回执中有 `product_review_status=ai_pending`。

第二台旧批次 `geo-products-21x5-account2-20261013` 也保留，0 条完成，旧状态为 needs_attention 1、prepared 1、pending 103。不要把两个批次拼接、跨账号重置或重新发完旧批次。

**状态显示另有未修复问题：** 第二台 `bridge_health.json` 仍保存停服务前的 `status=running`、`worker_exit=null`，这是过期快照，实际服务已停止。`geo_batch_bridge.py` 的 finally 仅终止子 worker，没有可靠写入停止状态。接手需要修正健康状态的时效和停机记录。

scrcpy 已关闭。两个 Android 容器仍在运行，登录资料保留。

## 3. 已确认的故障证据

### 3.1 已排除共用账号、登录会话与进程阻塞

- 当前进程打开的 IM 数据库核验：第一台账号尾号 385833，第二台当前 066524；第二台原账号为 451113。
- 两台的数据卷、PID namespace、network namespace 独立。
- 原生偏好里的 `X-Tt-Token`、`x-tt-token-supplement`、`session-tlb-tag`、`mfa_token` 等在内存中做摘要比较，全部不同。**没有打印或导出令牌。**
- App 线程快照没有 D 状态内核阻塞；未见 OOM。不能把停滞归因于“两台用了同一个 session”。

相关脚本：`active_database_accounts.py`、`compare_session_isolation.py`、`check_runtime_isolation.py`。部分诊断脚本会打印账号派生目录名，避免对外复制未脱敏输出。

### 3.2 发送失败的明确错误是“无效会话 ID”

监听原生 App 埋点，在一次已确认失败消息的原生重试中捕获：

```text
send_message_status: success=0, result=im_error
message_send_result: error_code=-17, status=1, duration≈75ms
```

读取当前官方 APK 的 DEX 静态常量，`IMErrorCode` 和 `OmniIMErrorConst` 都定义：

```text
ERROR_CODE_INVALID_CONVERSATION_ID = -17
```

这不是靠网上其他产品的同号错误码推测。证据工具是 `read_im_constants.py` 和 `watch_send_telemetry.py`。

第二台当前账号的 `im_conversation` 表一直为 **0 行**，界面却持有旧会话 ID `38436542168665602` 并拿它发消息。原失败消息 `message_id=null`、`server_index=0`；重启后显示红色感叹号。第一台当前账号 `im_conversation` 有 3 行有效会话。

第二台 IM 短连接命令 1111/3200 持续反复请求，传输层 `error_code=0`，但会话没有恢复。清数据库后历史消息能同步回来约 2589 条，而会话表仍然为空。基础网络畅通不能证明会话同步成功。

### 3.3 最新发现：两个不同会话缓存文件实际落在同一截断路径

第二台的 Keva repo：

```text
/data/data/com.larus.nova/files/keva/repo/
  FlowIMSDKconversation-local-manager<长账号标识>/
```

该目录名长 111 字符，正常应分别有同名 `.blk` 和 `.chk` 文件（文件名长 115 字符）。第二台实际只生成一个**无后缀、文件名被截到 100 字符**的文件。

`/proc/<App PID>/maps` 显示两个不同大小的共享映射（8192 与 4096）都引用同一文件、同一 inode。App logcat 同时有：

```text
KEVA.NATIVE: ... block file index is error ... block len=0
KEVA.NATIVE: ... fail to mark ...
```

这为缓存文件互相覆盖及反复损坏提供了具体证据。第一台是从之前 Android 环境迁移过 App sandbox，当前目录既有完整 `.blk/.chk`，也有截断残留；第一台业务可用，**不要为了比较去清第一台缓存**。

**证据边界：** 已观察到路径截断、两个映射落到同一文件、缓存损坏、会话缺失以及 -17 的失败链路；尚未证明截断发生在 Keva、ARM libc 包装还是 Houdini 转译层，尚未完成修复后的因果验证。不能写成“Houdini 根因已完全确认”或“已修复”。预先创建完整文件后它们仍为 0 字节，App 仍使用新生成的截断文件，此办法无效。

## 4. 已做的修复尝试及保留现场

所有操作只针对第二台；没有清空整个 App，也没有复制第一台的账号或聊天数据。

| 尝试 | 结果 | 服务器备份 |
| --- | --- | --- |
| 清第二台网络 hostcache 后重开 App | 无效 | `account2/network-cache-backup-1791940861` |
| 备份当前账号 IM DB、WAL、SHM，重建聊天库 | 消息可恢复，会话仍 0 行 | `account2/im-cache-before-rebuild-1791942458` |
| 备份第二台 IM CMD/消息间隔/会话 manager/launch cache 等，触发重新同步 | 无效，长路径文件再次截断并损坏 | `account2/im-sync-backup-1791943316` |
| 备份截断文件，预创建完整 `.blk/.chk` 并按 App UID 设置所有权 | 无效，完整文件仍 0 字节，截断文件重新生成 | `account2/keva-collision-backup-1791944006` |

上表备份路径都在 `/home/user/redroid-doubao/` 下。原失败聊天记录在备份中，当前 IM 库重建后原失败消息不再存在；**不能因为当前库查不到原消息就推断从未尝试发送。**

当前批次首题 task_id：`a3c95521-ed78-5656-ab91-871ccd8a5751`，问题“推荐一款护发精油”。原生失败 local_message_id：`c10c6d72-e1be-4776-a36c-de9f25144bf8`。队列仍为 prepared，原失败证据没有清除。修复后需要核验原记录无服务端确认，保存队列备份与审计事件，再受控恢复这一题；不要直接把所有 prepared 改 pending。

上述一次性脚本包含特定账号/现场断言，**不可无脑重跑**：

- `reset_account2_network_cache.py`
- `rebuild_account2_chat_cache.py`
- `rebuild_account2_im_sync.py`
- `repair_account2_keva_filenames.py`

## 5. 下一步正在查哪里

最后一步已从第二台复制运行时 ARM libc 到：

```text
/home/user/redroid-doubao/account2/runtime-libc.so
```

来源 `/system/lib64/arm64/libc.so`，ELF ARM aarch64。导出符号：`open` 0x72f5c、`__open_2` 0x730f4、`openat` 0x7320c、`__openat_2` 0x73394。**目前仅读取，未改 APK、libkeva、libc 或 Houdini 二进制。**

官方 APK 的 `libkeva.so` 已提取到服务器 `account2/libkeva.so`。静态反汇编发现其 `.blk/.chk` 构造经 0x2592c 拼接字符串，再经 MappingFile::Load（0x328cc）调用 open。当前代码片段未看到导致 100 字符截断的直接证据，不能凭预期修改指令。

服务器 venv 本轮额外安装 `capstone`、`pyelftools` 用于只读诊断；有 `/usr/bin/strace`。可进一步跟踪第二台文件打开路径，对比传入路径和最终 syscall，或查 ARM libc/Houdini 的路径转换。不要全量打印网络、账号 token 或私聊内容。

诊断脚本（Windows `redroid-deploy/` 及服务器根目录有同名文件）：

- `inspect_keva_paths.py`：文件长度、inode、映射相关路径。
- `inspect_im_runtime_errors.py`：脱敏筛选 logcat 缓存错误。
- `inspect_conversation_state.py`：当前账号库的会话数量与状态。
- `inspect_all_im_state.py`、`inspect_im_cache_keys.py`：跨库/缓存对照。
- `inspect_keva_library.py`、`disassemble_keva.py`：库读取与 ARM64 静态反汇编。后者当前固定读 `account2/libkeva.so`，分析 libc 时应先改目标路径，勿误读。
- `account2_ui.py`：操作第二台已观察到的控件，默认只输出可见文本。
- `check_two_accounts.py`：两批队列/回执/间隔与 GEO 入库摘要，第二台 running 快照已过期。

验收条件：会话缓存文件正常且互不覆盖；有效会话恢复；第二台至少连续几题成功得到完整正文和信源；GEO 有对应 processed 回执；实际发送间隔 ≥30 秒；服务持续无头运行。仅“能打开输入框”或网络测试通过不能验收。

## 6. 环境、操作入口与现有代码

Windows 工作区：`C:/Users/78567/Desktop/隐身浏览器`。实际运行项目源码在 `redroid-deploy/`，不是用于参考的技术文档副本。

Linux 服务器：`192.168.31.106`；项目根 `/home/user/redroid-doubao`；Python `/home/user/redroid-doubao/worker-venv/bin/python`；ADB `/home/user/redroid-doubao/linux-tools/platform-tools/adb`；业务 worker 代码 `/home/user/redroid-doubao/geo-batch-code`；队列 `/home/user/redroid-doubao/batches/<batch>/tasks.sqlite`。

```powershell
python -B redroid-deploy/remote.py '远端命令' --sudo --timeout 25
python -B redroid-deploy/remote.py --upload 本地路径 /home/user/redroid-doubao/目标文件
python -B redroid-deploy/remote.py --download 远端路径 本地路径
```

使用已有 SSH 配置，不输出 `remote.py` 的私有配置或凭据。远端执行超时可能只是通道结束，脚本可能已执行；先核查副作用再重试。长命令若返回 exec session_id，继续 poll，不要立即重复执行。

镜像 `doubao/redroid:13-hpe14-com1.3`，已验 image ID `sha256:18244ad4ab1c36047438bb9c524d8f8d6f848ee8d7537a98483a26c5dda7601f`；Android13 SDK33、Houdini14 com1.3、豆包官方 15.2.0（versionCode 15020040），每台 2 CPU/3GB。第二台仅安装第一台的官方 APK，新建独立数据卷，没有复制用户数据。

此前已部署的采集保护：`unattended_worker.py` 识别可选通知弹窗、新对话空白落地页，并在发送前阻止仍显示旧采集问题的页面；`unattended_core.py` 对 fts 为空的原生消息用唯一任务编号和完整结构正文精确匹配。最近一次服务器相关单元测试共 **39 项通过**，但这不能证明第二台原生发送问题修复。

GEO 真正服务目录 `/opt/monitor`。回传配置 `/opt/monitor/doubao_mumu_controller/doubao_lan_receiver_config.json`，含 token，不打印。协议 POST `/api/v1/captures` + GET `/api/v1/status/{request_id}`。`geo_batch_bridge.py` 保留完整 `answerText/items/citations/search_queries/native_result`；202 仅代表接收，processed 回执才计完成。GEO PostgreSQL 容器 `monitor-postgres`，DB `monitor`，用户 `monitor_app`。

## 7. 给新对话的直接任务

先读本文和 `redroid-deploy/ACCOUNT2.md`，核查当前第二台服务/缓存/会话状态。沿“长路径截断导致 Keva 文件冲突→会话同步失败→invalid conversation ID -17”继续定位具体层，并做可恢复修复。随后受控恢复第二台当前批次首题，验证完整正文、信源及 GEO processed 回执，再继续 21×5、至少 30 秒的无头批量任务。修正过期 running 状态。第一台已完成 105/105，保持原成果；不要要求用户重复登录来替代故障排查。

根目录旧 `PROJECT_HANDOFF.md` 主要记录内容工作台，有更早的“不启用 Redroid”历史要求；用户后来明确授权了本次两个无头豆包采集项目，本次范围以最新用户授权和本文为准。
