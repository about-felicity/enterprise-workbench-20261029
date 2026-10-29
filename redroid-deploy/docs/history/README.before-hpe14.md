# Redroid / 豆包部署记录

详细技术架构、操作流程、备份恢复、故障排查和扩展设计见同目录 `PROJECT_GUIDE.md`。本 README 保留部署与测试摘要。

最新无人值守加固与验收见 `UNATTENDED.md`：新增 Linux 本地持久队列 worker，22 项故障测试通过；真实 App 三次就绪失败，任务已熔断保留，当前仍未通过无人值守上线验收。systemd 模板已验证，未启用生产服务。

## 当前状态（2026-10-06）

- ERSTT/redroid 已克隆到相邻的 redroid 目录，提交 e32446b85e112b64354d6e9a0e511a89a2419c95。
- 本机 Docker Desktop 已启动。
- 本机 WSL 内核：6.18.33.2-microsoft-standard-WSL2。
- 内核配置明确显示 `# CONFIG_ANDROID_BINDER_IPC is not set`，`# CONFIG_DMABUF_HEAPS is not set`；`modprobe binder_linux` 返回模块不存在。
- 已部署到 `user@192.168.31.106`，服务器目录 `/home/user/redroid-doubao`。
- 服务器：Ubuntu 22.04.5、Linux 6.8.0-138-generic、Intel i5-13420H；已有 Binder 模块，无需重启服务器。
- 当前运行 Android 15，ADB 隧道可连接，截图与 UI 自动化可用；此前测试过 Android 13 的两种转译镜像。
- 豆包官方 APK 15.2.0（versionCode 15020040，arm64-v8a）已安装。APK SHA-256：`5056b1351f7b3afe2f0303391bc5671e391af4534ba701a40f2cf7f89e89098b`。
- 实测 NDK 镜像：能显示登录页，随后在 `libndk_translation.so` 的 `GuestVAListParams` / `CallBooleanMethodV` 中 SIGABRT，`params_arm64.h:254: CHECK failed`。
- 实测 Houdini 镜像：豆包启动无响应，产生 ANR；临时增加到 4 核仍未显示可交互页面。
- Android 15 AVD 转译镜像 `erstt/redroid:15.0.0_ndk_AVD` 已加载，摘要 `sha256:6c2597228d0884626ebd9e3905d5334d8e2e9d6554db4c639851eabd04a65d83`。需显式配置 `ro.enable.native.bridge.exec64=1` 和 `ro.dalvik.vm.native.bridge=libndk_translation.so`；默认 `libnb.so` 配置导致 ARM 库加载失败。
- Android 15 实测豆包连续运行超过 3 分钟，手机号登录页可交互，期间未记录原生崩溃。容器限制 2 核、3GB 内存，数据存放在独立的 `doubao-redroid_android15-data` 卷，之前 Android 13 数据卷保留。
- 用户已登录。已关闭 scrcpy，在后台 Android 中连续发出 3 个测试问题，并直接从聊天 SQLite 数据库读取全部回答：37 条信源记录、15 处正文引用，保存于 `test-results/`。
- **稳定连续运行未通过**：第三题已落库但 UI 停在搜索状态；后续重开 App 出现 `guest_params_arch.h:278: CHECK failed: 32080 <= 0` 和 SIGABRT。现已停止失败的豆包进程，保留后台模拟器及登录数据。不能宣称当前环境已支持长期无人值守。
- 原来的 8 个业务容器 ID 均与部署前一致，未停止或重启原有业务服务。
- 已配置 Redroid `unless-stopped` 重启策略和 Binder 模块的开机加载；ADB 只绑定服务器回环地址。

## 本机投屏与诊断

在 PowerShell 运行：

```powershell
& .\redroid-deploy\open-doubao.ps1
```

脚本会建立本机 `127.0.0.1:15555` → SSH → 服务器 `127.0.0.1:5555` 隧道并打开 scrcpy 窗口。关闭投屏不会停止服务器上的 Android。登录时检查国家区号：中国手机号应使用 +86，镜像初始显示 +1。

```powershell
.\redroid-deploy\.venv\Scripts\python.exe .\redroid-deploy\inspect_device.py
```

诊断文件位于本机 `artifacts`：`crash.log`（NDK 崩溃）、`houdini-anr.log`、`houdini-logcat.log`、`services-before.txt`、`screen.png`、`screen.xml`。当前 Houdini 启动卡住时 UI 层级为空；NDK 登录页曾成功读取文字与按钮。

服务器上的 `compose.ndk.yaml` 与 `compose.houdini13.yaml` 保存了 Android 13 配置，供后续比较测试；不会自动回退。模块配置文件为 `/etc/modules-load.d/redroid-doubao.conf` 和 `/etc/modprobe.d/redroid-doubao.conf`。

## Linux 服务器部署

需要 x86_64 Linux、Docker Engine、Compose 插件，以及 Binder 内核支持。软件渲染无需 GPU。当前配置采用 Android 15 AVD 转译镜像和 memfd。其他应用与其他豆包版本仍需分别实测。

上传本目录后执行：

```bash
bash deploy.sh
```

脚本会检查环境，必要时尝试加载已安装的 binder_linux 模块。缺失模块时停止，不自动替换内核。Ubuntu 的匹配内核扩展包可按上游说明安装；具体操作需结合服务器发行版。

ADB 仅绑定服务器回环地址。Windows 通过 SSH 转发连接，避免直接对外暴露：

```powershell
ssh -N -L 15555:127.0.0.1:5555 USER@SERVER
adb connect 127.0.0.1:15555
adb -s 127.0.0.1:15555 shell getprop sys.boot_completed
adb -s 127.0.0.1:15555 install -r .\doubao.apk
scrcpy -s 127.0.0.1:15555
```

APK 应来自豆包官方渠道。登录时由用户在投屏界面输入手机号、验证码或扫码，当前登录数据存储在 Docker 的 `doubao-redroid_android15-data` 卷中。安装、登录、ARM 转译兼容性都需要实测。

```bash
docker compose stop
docker compose start
docker compose logs --tail 100
```

停止或移除容器不会清除命名卷；不要使用 `docker compose down -v`，这会删除应用数据和登录状态。

## 需求可行性与验证顺序

目标链路：问题列表 → Python 调度 → ADB / uiautomator2 → 豆包 App → 等待回答结束 → 提取文本 → JSONL / CSV。

1. 验证 Android 完成启动，ADB 能操作设备。
2. 安装官方 APK，确认正常启动与联网。
3. 用户完成登录，人工发送一个问题。
4. 检查 UI 层级是否暴露回答文字；若没有，再评估复制功能或截图 OCR。完整长答案、滚动与流式输出必须单独验证。
5. 实测至少三个问题，检查回答完成检测、超时、重复输出与新会话操作。
6. 再编写依赖实际页面元素的循环脚本，保留问题、回答、时间、状态和失败截图。遇到登录失效或验证要求暂停。

无头运行表示无人观看投屏时 Android 仍在后台运行。App 的循环提问和答案提取使用 ADB / Android UI 自动化；Playwright / 无头浏览器不能直接抓取原生 App。当前任务明确使用模拟器里的 App。

实测结论：无头模拟器能够发出问题并保存回答，正文及原始信源可直接提取。当前 x86 ARM 转译环境仍有 App 卡住和崩溃，自动循环的稳定性未通过；修正转译兼容性之前，不能部署为长期无人值守采集。

## 已验证的数据提取

`test-results/report.md` 可直接查看正文和信源；`answers.json` / `answers.jsonl` 保留完整结构；`answers.csv` 与 `sources.csv` 可导入表格软件。

| 问题 | 信源记录 | 正文引用 |
| --- | ---: | ---: |
| 国博地址与开放时间 | 12 | 4 |
| 故宫预约入口 | 9 | 4 |
| Python 列表与元组 | 16 | 7 |

`sources` 是搜索参考资料列表，`citations` 是正文实际引用，包含原始位置、标题、URL 和 doc_id。正文 Markdown 来自消息 text_block，不依赖截图 OCR。

`export_chat_store.py` 已部署在服务器 `/home/user/redroid-doubao/`。它通过 Docker 查找该模拟器数据卷，以 SQLite 只读事务查询 `im_message`，只导出指定测试问题对应的聊天记录，不读取账号数据库。此方法依赖服务器管理员权限及当前 App 的数据库结构，后续升级应重新验证。

```bash
sudo python3 /home/user/redroid-doubao/export_chat_store.py
```

`doubao_loop.py` 是实验性循环脚本：ADB 发送问题，再等待对应新消息完成落库并直接读取正文和信源；默认 `--source-mode store`。控制脚本目前在 Windows 上运行，Android 与数据库读取在 Linux 服务器；不需要投屏窗口或无头浏览器。因为转译崩溃，最终连续批次尚未验证成功，遇到错误会保存证据并停止，避免重复发送。

```powershell
.\redroid-deploy\.venv\Scripts\python.exe .\redroid-deploy\doubao_loop.py --questions .\redroid-deploy\test_questions.json --output .\redroid-deploy\artifacts\new-run
```

UI 备用模式 `--source-mode ui` 可复制正文并逐条打开信源分享链接，但 PDF 等页面可能显示“分享失败”，重定向也可能改变 URL。数据库中保留原始 URL，已确认第 8 条 PDF 信源也可提取。

Android 系统输入曾出现 InputDispatcher 的指针重叠异常，因此脚本使用 ADB input；剪贴板预览浮层曾挡住分享按钮，测试时仅在模拟器内设置 `clipboard_overlay_enabled=false` 与 SystemUI `READ_CLIPBOARD=ignore`。原有业务容器未停止或重启。

## 来源

- https://github.com/ERSTT/redroid
- https://github.com/remote-android/redroid-doc
- https://github.com/remote-android/redroid-doc/blob/master/deploy/wsl.md
- https://developer.android.com/tools/adb
- https://github.com/openatx/uiautomator2
- https://www.doubao.com/download
