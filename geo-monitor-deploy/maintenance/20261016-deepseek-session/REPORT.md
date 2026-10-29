# DeepSeek 登录持久化修复（2026-10-16）

16:13最终验收（覆盖下方待登录状态）：用户已完成登录，新flow770b58d1自动ready。登录窗口真实关闭、采集会话重开校验通过；私密状态0600 user:user。再次鲜活校验5项通过后恢复原63次批次，32 processed、31 pending、active/rate_wait、无回传积压；下一题CLI自然关闭/重开浏览器并成功采集，保存时间持续更新。未创建新批次或重复旧完成题。

另修复用户截图中的状态矛盾：此前登录记录ready，但任务区仍读取上次退出的waiting_login健康快照。控制响应现按鲜活且匹配批次/版本的校验投影ready_to_resume/starting，当前与每日卡片一致；真正较新的登录失效仍优先。登录窗口通过postMessage和无凭据storage信号通知，父面板用1秒轻量状态检查等最终ready后自动刷新。20项控制测试、真实Chrome隔离自动刷新/正确网关路径/校验后继续可用测试通过，均未操作真实采集。正式API current=running、daily=running、32/63、interval600。仅status服务重启，采集bridge PID24470未改变；源码58/58一致。生产证据production-login-resume.json、production-verified.json，机器状态测试qa-login-state.json。

16:02补充：用户反馈卡顿，实测原全量panel初始化4052ms、截图43–55ms。已上线独立登录会话初始化及state返回csrf，不再读六通道数据库；帧160ms循环、状态1秒、输入后立即拉帧、快速文字60ms合并保序，不重放任何输入。bootstrap授权测试和真实Chrome输入夹具通过；正式UI5.5ms、state10.7ms、frame43.6ms。只重启status服务，现有手动登录浏览器及采集器未重启。用户刷新当前页加载新版，远端输入保留；仍等待手动登录完成，未宣称生产会话验收通过。

已部署，源映射58/58一致；未主动重启或中断采集服务。

## 原因与证据边界

今天13:18（日志05:18UTC）出现明确登录页面，13:29恢复；15:45旧流程再次检测登录失效，退出77，停留31/63、32待发、回传无积压。旧日志只记录登录页，没有服务器返回的失效原因，无法证明平台主动撤销会话还是本地会话材料丢失。

本地代码存在两处确切薄弱点：桥接以max-new-captures=1逐题退出CLI、关闭Chrome；虽然使用持久化Chrome目录，但ds_session_id、HWWAFSESID、HWWAFSESTIME实际为session=true/expires=-1 Cookie，没有专门保存恢复。其次profile位于batch/collector/web_profiles/deepseek，新日新批次不会复用。原内容工作台和GEO采集仍应保持账号配置隔离，不混用profile。

## 已实现

- GEO登录入口、校验、每日/续批采集统一使用`/opt/monitor/geo-capture/profiles/deepseek`。此次用符号链接沿用原已登录目录，没有在线搬动Chrome文件。该链接当前指向今天原批次的profile，禁止清理该目标；后续迁移必须停在无浏览器的安全边界并验证。
- 新增web_collectors/session_store.py。登录确认ready时定期及正常关闭前保存Cookie/localStorage/sessionStorage；启动时恢复丢失的会话Cookie和存储，初始化脚本限制DeepSeek自身origin，不覆盖现有刷新值，不恢复已过期持久Cookie。
- 私密状态原子写入、文件0600，目录0700；root操作写入时保持profile原属主，手动登录user与采集user可共用。Token、Cookie值不输出到诊断/报告/源码包。
- 明确登录失效时废弃备份，不循环复活被平台拒绝的会话；仍按用户规则等待手动登录，不重发未知题。保存时间、Cookie过期/会话类型等无凭据诊断保存在geo-session-health.json。

## 验证与当前状态

48项单元/回归测试通过；隔离真实Chrome关闭重开后，主动清空的会话Cookie、sessionStorage恢复，localStorage保留，状态权限0600，失效备份不可恢复。未用生产账号发送测试问题。

部署前旧采集流程已于15:45自行因登录失效退出，没有现成有效会话可保存。部署后以生产user重新打开原profile并只读校验，仍login_required。因此已打开新版登录入口，等待用户手动完成一次登录；原63次任务不新建、不清队列。目前尚不能宣称生产账号的登录重开验证通过，也不能保证平台主动撤销的会话永不过期。

入口：http://192.168.31.106:3000/api/geo-capture/login/ui

代码备份、release.json、tests.log及qa-browser.json位于服务器同名maintenance目录。用户登录完成后检查自动checkpoint权限/属主、自动关页和重开校验ready；随后按原600秒间隔继续原任务。
