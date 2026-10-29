# DeepSeek 安卓 App 无投屏采集

2026-10-17 接入现有 GEO 六通道与创作专用素材流程。

- 官方 APK：https://download.deepseek.com/apk/deepseek.apk ，版本 2.6.2 / versionCode 281，SHA256 `1468cae414245e6bd447b0ae79c277958a6da1c25f4e4798ffc04e42127fa14a`。
- 独立容器 `deepseek-hpe14-android13`，固定卷 `deepseek-hpe14-android13-data:/data`，ADB 仅服务器回环 `127.0.0.1:5560`；2GiB 内存、3GiB 内存含交换上限、2 CPU。复用已安装的 HPE Android 13 镜像；不共享其他模型的数据卷。
- App 简体中文 `cmd locale set-app-locales com.deepseek.chat --user 0 --locales zh-CN`。
- Windows 手动投屏：运行本目录 `open-deepseek.ps1`，复用原 SSH 凭据读取器和 scrcpy，回环隧道 15560→5560。日常采集无需 scrcpy、Windows 或网页保持打开。
- 主任务：`geo-native@批次.service` → `native_entry.py` → 本目录 `worker.py`。默认 21 问题×3 轮；随机 660–1140 秒。历史 600 秒设置兼容为此范围；新保存的最小间隔产生 `[最小间隔, min(1199,最小间隔+480)]`，均不超过 1199 秒。
- 每题新对话，UI 校验智能搜索开启、深度思考关闭；发送前再次确认模式和问题原文。一次持久化点击意图只对应一次点击；结果未知补读原请求，不重发。
- 使用 App 原生 WCDB 的 SQLite WAL 事务读取正文、完整搜索列表、引用及 USER/ASSISTANT 身份；两次稳定完成快照后才入库。Compose 非可点击图标通过已读到的界面边界执行普通点击，避免新版 App 的 UiObject.info 不稳定。
- `delivery.py` 复用既有 DeepSeek 接收协议、冻结请求身份和真实 processed 回执；显示名为 DeepSeek 安卓App，source_device 为独立容器名。历史网页 source_device 仍可统计；跨设备计数求和。
- 创作专用 `private_capture.py` 只写产品专用目录的 results.jsonl 和进度账本，不创建接收器或读取其凭据。与主采集共用账号锁和发送时钟，按原 01:00 错峰规则等待，数据不进主 GEO。
- App /data 保存账号；旧网页 44/63 与其余 19 条待发记录留在历史。未将这 19 条冒充今日新增任务。旧网页当前启动链接已归档移除。

不能清理固定 Android 卷、native 队列、bindings、outbox、receipts 或全局发送时钟。普通连接异常退避，只有可确认的登录失效退出 77 等待用户。手动暂停沿用原控制面板，不自动覆盖。任务结束后按正常每日配置启动新一天任务。

生产验收见 `geo-monitor-deploy/maintenance/20261017-deepseek-native/REPORT.md`；源码包不是包含账号卷和数据的整机恢复备份。
