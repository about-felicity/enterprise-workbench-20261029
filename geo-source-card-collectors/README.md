# GEO 正文、信源采集与内容分析

当前写作方案：服务器调用 `deepseek-flash` 完成分类、研究、写作和独立上下文审稿，Windows 同步 Word 并提供原生 Qt 面板。每日采集 01:00，写作 05:00（北京时间），每类最多5篇。部署与恢复见 [API_RUNBOOK.md](API_RUNBOOK.md)。本地豆包控制程序已归档。

桌面操作入口：工作区 `启动内容工作台.cmd`，使用说明见 [DESKTOP_GUIDE.md](DESKTOP_GUIDE.md)。每日批量流程与实际限制见 [API_RUNBOOK.md](API_RUNBOOK.md)。

独立 Python 项目，采集回答正文和来源链接，再下载来源文章做可复核的内容统计。三种模式相互独立：

| 模式 | 数据来源 | 浏览器 |
| --- | --- | --- |
| `baidu_ai` | 百度搜索结果页 AI 卡片、引用弹窗 | Scrapling + 系统 Chrome |
| `wenxin_card` | 百度文心搜索卡片、资料列表 | Scrapling + 系统 Chrome |
| `deepseek` | DeepSeek 网页回答、引用与来源弹窗 | 系统 Chrome + CDP |

`wenxin_card` 指网页搜索卡片。本项目默认无头运行；与另一个豆包 Android 模拟器项目独立，不连接它的服务器、队列或浏览器。

## 安装

需要 Python 3.11+、Chrome/Chromium、可写的本地运行目录。Windows PowerShell：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

Linux/macOS：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

浏览器默认自动发现，也可设置 `MONITOR_CHROME_PATH`；百度可单独设置 `WENXIN_CHROME_PATH`。不使用系统 Chrome 时，需要修改适配器配置并安装相应浏览器，本版本默认使用系统浏览器。

默认运行目录是用户主目录下的 `.geo-source-card-collectors`，与代码分离。下面的命令使用同一个明确的运行目录；路径可自行替换：

```powershell
$env:GEO_COLLECTOR_RUNTIME = Join-Path $HOME "geo-collector-data"
```

Linux/macOS 对应 `export GEO_COLLECTOR_RUNTIME="$HOME/geo-collector-data"`。也可逐次传 `--runtime-dir`，优先于环境变量。不要把登录目录、采集数据与源代码一起提交 Git。

## 登录与就绪检查

DeepSeek 登录命令会打开独立浏览器，等待人工操作，最长 600 秒；成功后退出并保留专用 profile：

```powershell
python -m geo_source_cards.cli --model deepseek --login
python -m geo_source_cards.cli --model deepseek --ready
python -m geo_source_cards.cli --model baidu_ai --ready
python -m geo_source_cards.cli --model wenxin_card --ready
```

`--ready` 不提问；未就绪或验证页会返回非零状态。`--show-browser` 可以展示排查过程。百度卡片不保证每次请求都免验证；遇到验证会停止。DeepSeek 登录依赖真实网页状态，输入框可用只是就绪证据，正式采集还需后续校验。

## DeepSeek 登录巡检与提醒

在一个单独终端持续运行巡检；采集和巡检必须使用同一个运行目录：

```powershell
python -m geo_source_cards.session_watch --interval 180 --reminder-interval 900
# 或安装后使用 geo-session-watch
```

默认每轮检查后等待 180 秒，网页加载本身也需要时间。首次观察到明确的登录入口时立即提醒；持续未登录每 900 秒再次提醒，恢复后记录一次恢复事件。Windows 使用独立进程弹窗，不阻塞采集；带桌面的 Linux 可用 notify-send；无桌面服务器或锁屏时不保证弹窗可见，状态和事件文件仍然保存。`--no-desktop` 关闭桌面提醒，仍保留控制台提醒和文件记录。

```powershell
python -m geo_source_cards.session_watch --once --no-desktop
python -m geo_source_cards.cli --model deepseek --login
```

一次检查退出码：0 表示网页就绪，2 表示需要登录，3 表示无法核验或采集正在占用浏览器。巡检不提问；空闲时使用专用 profile 打开无头浏览器检查并关闭，采集或人工登录时会跳过，不抢占 profile 或刷新正在生成的回答。

采集程序也会检查登录：启动后和每次发送前检查，限频等待中最多每 180 秒检查一次，等待回答/信源时约每 60 秒被动检查一次。检查不聚焦输入框，不把回答正文出现的“登录”当成掉线，也不会因为生成期间输入框禁用就认定未登录。

运行目录里保存 `deepseek_session.json`（最近真实观测及时间）、`deepseek_session_events.jsonl`（掉线/提醒/恢复事件）和 `deepseek_watch.json`（独立检查或因浏览器占用而跳过的记录）。跳过不覆盖已有登录观测。

检查网络/浏览器失败时记为 `unknown`，不谎称登录掉线。提问前明确未登录时，任务保留 pending，可登录后用原批次继续。发送后掉线则进入 needs_attention，人工核对该回答后再决定如何处理，不自动重发。

这是项目内的巡检进程，不是 Codex 定期汇报。关闭巡检终端就停止独立巡检；要在服务重启或机器重启后继续，请由部署环境的进程管理器启动此命令。仅凭网页控件可用仍不能证明服务端 Token 永远有效，正式环境需要真实账号过期/退出验收。

## 采集

```powershell
python -m geo_source_cards.cli --model baidu_ai --question "工业机器人有哪些主要应用场景" --rounds 2 --batch baidu-day1
python -m geo_source_cards.cli --model wenxin_card --question "工业机器人有哪些主要应用场景" --rounds 2 --batch wenxin-day1
python -m geo_source_cards.cli --model deepseek --question "头屑多用什么洗发水比较好" --batch deepseek-day1
python -m geo_source_cards.cli --model deepseek --questions-file questions.txt --rounds 2 --batch deepseek-day2
```

问题文件为 UTF-8，每行一个问题，空行忽略，重复行去重。每个问题支持 1–20 轮。默认导出到运行目录的 `results/YYYY-MM-DD.jsonl`，每个任务一行；可用 `--output` 指定文件。

重要参数：

| 参数 | 作用 |
| --- | --- |
| `--batch` | 固定批次标识；重跑同一命令时跳过已完成任务 |
| `--require-sources` | 无来源链接就停止 |
| `--require-complete-sources` | 无法证明来源完整就停止 |
| `--status` | 只查看任务状态，不启动浏览器 |
| `--min-deepseek-interval` | DeepSeek 新提问间隔，最低 300 秒 |

DeepSeek 的 300 秒是本项目的保守策略，不是平台官方限额声明。时间状态持久保存，损坏时停止。每个运行目录只允许一个采集进程；来源文章分析使用独立锁，可另行运行。多个隔离实例需分别指定运行目录和 `GEO_DEEPSEEK_PORT`（默认 9314），不要共享 profile。

没有 `--batch` 时每次都会生成新批次、进行新的采集；定时任务应显式使用按日期和平台生成的批次标识。重用批次时，模型、问题、轮数和输出路径必须保持一致。

## 正文与信源结果含义

核心字段包括 `task_id`、`batch`、`model`、`question`、`round`、`captured_at`、`body`、`sources`、`source_count`、`capture_mode`、`body_capture_complete` 和 `source_capture_complete`。

| `source_capture_complete` | `source_capture_status` | 含义 |
| --- | --- | --- |
| `true` | `complete` | 当前页面暴露的来源项已按适配器规则提取 |
| `false` | `incomplete` | 已观察到缺项或提取失败 |
| `null` | `unknown` | 缺少可靠的页面计数，无法确认完整性 |

抓到零链接不自动意味着完整。完整性表示对页面的提取情况，不表示回答的事实正确，也不保证页面公开了全部上游检索材料。不同引用可能对应同一个网址，因此引用数量与唯一来源数会不同。

监控问题保持原文，不加“请附信源”等要求，也不追加采集编号。DeepSeek 每轮核验新对话与智能搜索开启状态，结果同时保留原文 `wire_question`。完成判定要求本轮问题出现在非输入区域、正文变化、页面就绪、无可见停止生成控件、正文稳定至少 6 秒，再等待正文和来源列表稳定。这是 DOM 观测规则，仍可能受网页改版或生成暂停影响。

百度模式禁止回退到文心模式充当成功。百度卡片展开并稳定后逐个读取引用；文心要求完成标记、正文稳定，并在滚动后重新检查。

## 中断恢复与无人值守

任务先持久记录为 `capturing`，再执行采集；成功提交 SQLite 后，原子替换 JSONL 导出文件。即使导出写盘失败，重跑相同批次也可从数据库重新导出，无需再次提问。

```powershell
python -m geo_source_cards.cli --status
# 恢复时执行原命令，包括同一个 --batch 和 --output
```

任务状态为 `pending`、`capturing`、`completed`、`needs_attention`。进程中断留下的 `capturing` 在该批次恢复时转为 `needs_attention`；已失败任务也进入该状态。严格信源校验失败时，已取得的结果保留在数据库的 `result` 字段，不作为成功结果导出。结果不明时停止，不自动重发。人工核对网页会话和错误后，确认需要新采集才使用新批次，不要删除数据库来绕过保护。

外部调度器应记录退出码、任务状态和错误；非零退出应告警，避免对失败批次无限重试。数据库、磁盘余量、登录失效、验证码和页面改版仍需运维处理。本版本提供安全停止和恢复保护，尚未通过三个真实平台的长时间无人值守验收。

## 来源文章内容分析

采集与文章下载分两步，避免来源站点慢请求拖住提问：

```powershell
python -m geo_source_cards.source_analysis --input "$env:GEO_COLLECTOR_RUNTIME/results/2026-10-07.jsonl" --output "$env:GEO_COLLECTOR_RUNTIME/analysis/day1.jsonl" --keyword 工业机器人 --brand 品牌甲 --brand 品牌乙
```

也可使用安装后的入口 `geo-source-cards` 和 `geo-source-analyze`。分析读取 JSONL 或 JSON 数组，支持重复 `--keyword`、`--brand`，`--no-fetch` 可只统计已有回答或缓存文章。

每个来源保存请求地址、最终地址、文章标题、正文、提取方法、文本 SHA-256、下载状态及关键词/品牌提及次数。成功文章缓存 24 小时；同一运行中相同 URL 只下载一次。

| 文章状态 | 含义 |
| --- | --- |
| `fetched` | 已取得足够的 HTML/纯文本正文 |
| `failed` | 网络、HTTP、验证页、过短正文、体积等问题；保留错误 |
| `unsupported` | PDF、媒体等当前未实现的格式 |
| `not_fetched` | 禁止网络下载且无可用缓存 |

下载逐次检查 URL 和重定向的公网地址，连接超时 5 秒、读超时 15 秒，正文大小上限 2 MB；循环检查 30 秒总耗时，但 DNS/底层阻塞不保证严格的 30 秒结束。正文提取优先 article/main，过滤导航、脚本等，复杂动态网站可能失败。此工具面向受控采集任务，URL 检查不构成对不可信用户的完整网络隔离。

当前分析是可复核的字面统计；提到某品牌不等于推荐它，也不等于正面评价。语义摘要、推荐倾向和事实核验可接入独立分析器，详见 [架构与扩展](ARCHITECTURE.md)。

## 迁移和测试

源代码可打 wheel 后安装，不依赖上级 GEO 项目或当前工作目录：

```powershell
python -m pip wheel . --no-deps --wheel-dir dist
python -m pip install dist/geo_source_card_collectors-0.5.0-py3-none-any.whl
python -m unittest discover -s tests -v
$env:GEO_RUN_BROWSER_TESTS = "1"
python -m unittest discover -s tests -v
```

迁移机器时安装 Python/Chrome 和依赖，设置新的运行目录，重新验证登录后开始新批次。结果 JSONL 可直接复制；Chrome profile 跨系统不保证可用，现有任务日志绑定绝对输出路径，不能直接当成跨机器可续跑的队列。历史数据库应保留为审计资料。

默认测试不访问真实平台；浏览器集成测试使用本地 HTML。验收范围和后续真实平台检查清单见 [测试记录](VERIFICATION.md)。

## 每日分析与飞书写作

0.4.0 新增 Scrapling 多后端文章抓取、近重复聚类、摘要与每日结构变化分析，以及本地提示词和飞书“豆包工作”的文件交接。完整配置、文件树和操作命令见 [每日信源分析与写作](API_RUNBOOK.md)。真实文心与 DeepSeek 的自然问题已完成一次采集到 Word 的流程验证；每日自动调度和长时间验收尚未完成。

DeepSeek 的 `source_entries` 保留来源序号，`sources` 保存去重网址。多个编号可以指向同一网址，因此来源完整性核对编号覆盖，不能把去重网址数直接等同于网页展示的来源条目数。

飞书两个独立工作任务的知识抽取、新提纲、可选产品提及和原文隔离流程见 [本地分阶段写作](API_RUNBOOK.md)。对应入口为 `geo-staged-editorial prepare/accept/check`。

0.5.0 的服务器部署、本机文件回执、动态类别批量生产、05:00 调度目标及六小时验收门槛见 [每日部署与验收](API_RUNBOOK.md)。当前原生本地定时任务不能保存，批量成稿仍在验收，不能按已完成的每日自动生产使用。

