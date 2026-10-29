# DeepSeek当前接手入口（2026-10-21）

先读根目录[CURRENT_PROJECT_HANDOFF.md](../CURRENT_PROJECT_HANDOFF.md)，再读本目录REPORT.md最上面的标准安装包v3记录。

- 用户已改为本人/多台同事自己打开Chrome、登录并加载插件，公网回传到本地服务器；默认随时手动开始，实际每设备保存配置优先。
- 默认21题×3轮、随机10–15分钟、深度思考关、智能搜索开。不要拿旧20–30分钟或上游42次循环覆盖新设置。
- 最新分发包`outputs/DeepSeek_标准安装包_v3.zip`，完整解压；可读CMD/Python/extension/哈希清单，不使用被Defender移除过的自释放PS1路线，不让用户关闭防护。
- 公网上传`https://1any.top/geo_monitor/collector/deepseek`，同事本地8767、本人旧版8766；独立设备密钥和outbox，只有processed回执算入库。分发包含限权登记能力，不要公开上传。
- 2026-10-21 13:32只读核查：公网ingest/upload-tunnel active，服务器browser-test/browser-receiver inactive，主09:00每日计划没有DeepSeek。历史android默认值不代表当前采集后端；别恢复旧模拟器或服务器无头浏览器。
- geo-2等Codex自动巡检现在全部PAUSED；不能继续声称每20分钟自动检查正在执行，本次未修改自动化。服务器自身定时与Codex巡检是两回事。
- 未知发送只补读原会话、不重问；账号限制不绕过，不据登录失效断言已检测到脚本。

旧10月19日HANDOFF已存`geo-monitor-deploy/maintenance/20261021-cleanup/previous-handoffs/deepseek-browser-deploy__HANDOFF_LATEST.md`。install_test.py、activate_production.py及旧部署/恢复脚本均为历史一次性记录，不是当前启动入口。
