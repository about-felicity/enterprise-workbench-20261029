# 2026-10-17 面板 API cgroup OOM 修复

## 根因和影响
内核 OOM 记录均定位到 monitor-dashboard-api 的容器 cgroup，内存上限 6GiB、含 swap 总上限 7GiB。10/17 北京时间 09:09、09:22、09:29、09:50、10:27 多次杀死 Python；修复前 Docker RestartCount=8。主机仍有可用内存，属于容器额度耗尽，不是 DeepSeek Android 模拟器 OOM。

通过临时独立安装的 py-spy 非阻塞堆栈，定位到多个 dashboard-http 线程处理 /api/models/*/activity，豆包 plugin._analysis_event -> _cached_source_entries -> Path.read_text/json.loads。319MB 索引由 lru_cache(maxsize=2) 保存完整两代，且 lru_cache 不合并并发冷加载，面板重复轮询使多个线程同时解析大 JSON，内存峰值达到 6GiB。其他通道 activity 还在重复扫描回执目录。

## 变更
1. monitor_core/source_activity_index.py：标准库分块解析，只保留每条 URL 的 status 与既有 own_product_mentions 的列表存在性/非空标记；不在 HTTP 线程构造整个索引。保留旧数据没有标签的语义，不从缺少标记的 SQLite 臆测归属。
2. ActivityIndexCache 锁合并冷加载，最多保留一代精简索引；检查间隔 5 秒，原子替换失败保留上次完整结果。单条 JSON 值限制 16MiB。
3. API activity 使用已有 JSONResponseCache，同模型/limit 合并请求，3秒新鲜/10秒旧值可后台刷新；原队列统计及历史回执不删除。

10:36:30 北京时间仅重启 monitor-dashboard-api，保留原 6GiB 限额。未重启采集、未改任务配置、未清队列或历史。DeepSeek MainPID=19635，文心 MainPID=14824 与发布前一致。

## 验证
- 5 项单测通过，覆盖 1/2/3/7/64/65536 字符分块、BOM/中文/转义/嵌套/数字边界、历史无标签、非法或截断 JSON、文件替换失败及 64 并发请求只加载一次。
- 真实319MB索引独立读取：106107条，89607条status=ok，106107条已有列表标签；1.67秒，测试进程峰值RSS73.6MiB。
- 上线48次并发activity请求全部成功且内容一致，40条事件、queued=0/processed=29220/errors=0；请求缓存有coalesced计数。
- 用户实际 https://1any.top/geo_monitor/api/models/doubao/activity?limit=39 通过认证只读验证成功，39条事件；不打印认证cookie。
- 初始API容器约508MiB，随后正常前端/统计请求加载后约0.9–1.0GiB；连续12次/约56秒健康采样 cgroup 913.6–1003.1MiB，远低于6144MiB限额，swap=0，未再触发OOM或自动重启。该短观察不能代替整日负载验证。
- 79/79 正式源码映射一致。完整健康采样在服务器本目录 observation.json。

## 回滚
原API及豆包插件备份在本目录 before/；如需回滚，仅还原这两个文件并重启面板API，新模块可保留。回滚会重新引入原OOM风险，不能靠增加额度代替修复。
