# 2026-10-17 第二个 DeepSeek 无头安卓模拟器

用户要求新增一个模拟器，完成后用scrcpy投屏供本人登录。已创建独立容器deepseek-hpe14-account2、独立持久卷deepseek-hpe14-account2-data:/data；不复制第一账号/data、token、App数据库或任务队列，仅从原已验证官方2.6.2/version281提取APK，SHA256 1468cae414245e6bd447b0ae79c277958a6da1c25f4e4798ffc04e42127fa14a一致。

与原实例相同现有HPE镜像/硬件配置，2CPU/2GiB内存/含swap3GiB、720×1280、restart unless-stopped。ADB仅服务器127.0.0.1:5561，Windows原SSH隧道15561→5561。两个AndroidID读取后验证不同，只记录结果不公开标识。

已设系统与App简体中文、打开官方登录页面。Windows独立启动器deepseek-deploy/open-deepseek2.ps1，单独artifacts-account2目录；scrcpy窗口标题DeepSeek 2 - Login，PID39300，MainWindowHandle非0且ADB截图确认显示手机验证码/密码登录。截图本目录login-screen.png。保留投屏供用户手动登录，不读取/填写账号密码或验证码。

服务器元信息/home/user/redroid-deepseek-account2/device.json，state=awaiting_manual_login、scheduled=false；尚未将第二设备加入每日任务，不能声称已登录/已采集。第一模拟器及原worker PID44432持续运行，没有重启或修改当前队列/全局发送时钟。后续接入第二路采集时需要按实际账号分别管理锁/时钟与设备，不能直接用原device.py硬编码主设备，更不能重发已完成题。

provision.py为一次性创建脚本，对已存在容器或卷直接拒绝，避免覆盖持久账号数据；以后启动复用docker restart策略和open-deepseek2.ps1，不要删卷重装。

## 13:42 用户登录后校验
用户确认已登录。第二设备独立进程校验ready，App内单个账号token非空落在专用持久卷；只比较账号ID是否相等，结果与第一账号不同，不打印账号ID/token。只开启智能搜索、关闭深度思考，零提问。对空闲第二设备执行App force-stop→冷启动，再次校验ready和两个模式，证明App进程重开后保持登录；未重启第一设备或采集进程。第二设备元信息state=ready，scheduled=false，尚未接入任务队列，不得声称正在采集。
用户登录投屏已关闭：仅关闭第二个scrcpy PID39300/指定窗口，并关闭本地15561→5561专用隧道；服务器第二模拟器保持running。第一worker PID44432/14次已入库继续rate_wait。后续如分配第二路采集需实现独立设备/队列分工/账号时钟，避免重复样本。

## 13:47 第二路已正式启动采集（覆盖此前 scheduled=false 记录）
用户明确授权第二设备按另一设备相同配置立即采集。读取第一路当天持久化daily_tasks配置，21题×3轮=63，interval保存值600按已有policy转换为随机660–1140秒。第二路独立63次，并不分走或重发第一路队列。

新增deepseek2控制通道（追加至MODELS/fleet末尾，保留原6通道顺序）、账号锁deepseek2_account.lock、全局计时deepseek2_last_send.json、专用批次SQLite/队列/原生绑定/回执。启动前仅比较两App持久化账号ID，确认不同，允许独立提问计时，不输出凭据。

第二路运行代码/home/user/redroid-deepseek-account2/code；device/worker/delivery为专用profile，android/reader/policy与第一路同一源码逐字同步，并均加入发布映射。Receiver逻辑模型仍deepseek，source_device=deepseek-hpe14-account2；每日计数DEVICES分别映射deepseek和deepseek2，避免一个账号完成数被另一个抵扣。暂停/继续、保存即时应用、每日05:00及重新校验均单独管理；第二账号重新登录仍使用独立scrcpy入口，未将primary登录网页错误指向第二账号。

正式批次geo-panel-deepseek2-20261017-134730-bf1a1e9e，服务geo-native@geo-panel-deepseek2-20261017-134730-bf1a1e9e.service，PID46395。每日计划已加入deepseek2并保存当天running任务，systemd原target已启用此批；其他模型原保存设置/手动暂停保留，不用daily_plan历史轮数覆盖。只加载每日协调和状态控制服务，所有既有采集进程未重启，原DeepSeek PID44432/15已入库继续。备份/opt/monitor/geo-capture/backups/deepseek-second-lane-1792216050，含原控制源/plan/fleet/SQLite备份，不得恢复数据库覆盖后续数据。

验收：61项控制/每日/receiver/第二路隔离测试通过；阶段性缺失completion_guard导入路径与receiver标签默认值失败已修复后完整重跑，不能将失败计为通过。第二路首题真实1090字/12来源，原生完整正文/信源与processed回执一致，first_user_turn=true、thinking=false/search=true，仅1次发送，1/63、62待发。首次持久化随机1131秒，下一次北京时间14:06:36；第一路15/63与第二路1/63独立。LAN真实Chrome7通道、第二路Logo、21题/3轮/随机间隔、桌面手机、无连接红条、JS错误0与生产测试POST0通过；started-qa.json为结果。公网浏览器首轮遇网络/SSH超时，单独复查记录，不误称首次公网通过。85/85正式源码映射一致。

start_lane.py为一次性登记脚本，已存在settings.deepseek2即拒绝，不能为了重试又建批次。后续由面板/每日协调器沿用原队列。

公网复查最终通过：真实 https://1any.top/geo_monitor/ 页面iframe显示7通道，DeepSeek 2 Logo/21题/3轮/随机间隔/桌面手机检查通过，JS错误0、测试写入0；started-qa.json最终记录public_seven_channels=true。首次网络超时仍保留为失败尝试，不计通过。
