# 2026-10-17 10:43 DeepSeek检查与内存额度调整

- 登录探针ready，Android容器正常；发现2/63 preparation_backoff，实际欢迎语“欢迎回来，想从哪里开始？”导致旧固定文案门禁再次拦截，不是掉登录。
- Android.ready现按已登录、点击新对话后空编辑器、两个模式按钮、单个欢迎TextView及无回复操作的布局判断；不枚举随机欢迎语。原生数据库首问身份校验和只智能搜索/禁深度思考不变。13项测试通过，含未来未知欢迎文案和旧会话拒绝。
- 无prepared/未知点击的安全边界更新android.py并短暂重载DeepSeek worker，原批次/SQLite队列保留2完成61待发；每日控制仅为加载修复短暂重载，其他采集器未重启。备份/opt/monitor/geo-capture/backups/deepseek-layout-memory-1792204871。
- 北京时间10:42:13第三题已完成并入库：正文553字/12信源，first_user_turn=true，thinking_enabled=false，search_enabled=true。3/63，60待发，running/rate_wait。下一次10:53:37，持久化间隔692秒。上一次真实间隔1237.74秒，因本次门禁故障超20分钟37.74秒；不称历史间隔均合规，不修改事件。
- 用户要求提高服务内存上限。主机15.35GiB、可用约7GiB；仅把主要面板API从6GiB/含swap7GiB提高到8GiB/含swap9GiB。docker update在线生效，不重启API，StartedAt仍02:36:30 UTC；compose同样永久保存，config --quiet校验通过。未给全部容器无限制扩额，Android DeepSeek原2GiB等其他限额不变。
- 调整后API约1.412GiB/8GiB，Android约873.5MiB/2GiB；79/79源码映射一致。
