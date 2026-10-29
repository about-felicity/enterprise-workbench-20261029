# DeepSeek 公网 scrcpy 登录投屏

2026-10-17 16:47（北京时间）已发布至内网及 https://1any.top/geo_monitor/ 。

采集控制新增两个账号的“DeepSeek 登录巡检”卡片。正常状态按钮灰色禁用；确认掉登录、人工验证或账号限制后按钮亮起，点击在当前访问设备的浏览器打开对应模拟器的真实 scrcpy 视频和控制。无需在访问者电脑或手机安装桌面 scrcpy。这里是在浏览器承载 scrcpy 流，并非远程网站启动访问者设备的原生可执行程序。

## 实现和运行

- 官方 scrcpy-server 5.0 在各自模拟器提供 H264 和控制协议；服务器 ffmpeg 连续转为 multipart JPEG 供桌面与移动浏览器显示。不是 ADB 截图轮询。指针点击、拖动、返回、退格、键盘和移动端输入框通过 scrcpy 控制连接；两个账号独立端口、锁和登录流程。
- `geo-deepseek-auth-check.timer` 每五分钟执行只读检查，独立于浏览器是否打开。断连、读取失败等 unknown 不会直接误判掉登录。确认登录或人工验证异常后，通过现有 drain 机制禁止新题；正在处理的结果仍按原机制回传。
- 可用状态需要持久化账号与真实输入界面证据。封禁、账号限制、验证码或不能识别的阻断弹窗都不算成功；正常输入界面的回答正文提及“封禁”等词不会被当成账号封禁。无法检测平台没有呈现在界面的隐性风险，也不会为了检验账号发送额外测试问题。
- 手动登录流程每两秒检查；连续正常后还会运行新会话及模式校验，保持深度思考关闭、智能搜索打开。全部通过才关闭 scrcpy、释放账号锁、刷新面板并让原任务续跑。手动暂停的任务保留暂停。
- 面板每五秒取状态，异常有显著提示及标题提醒。“启用浏览器提醒”由用户授予通知权限。浏览器通知依赖页面仍打开；未实现关闭浏览器后的系统推送或短信。
- 修复第二个 DeepSeek 在父页面导航白名单缺失的问题，`#capture/deepseek2` 与投屏返回会保持正确账号。
- 沿用登录会话、来源/Host 检查、CSRF、动作标识和私有登录 flow 校验。视频端口只在服务器回环地址开放，公网通过原受保护网关；无需公开 ADB。

## 验证

- 最终 Python 回归 58 项通过：认证/协议 13、每日任务 24、控制面板 20、登录引导 1。网关与创作网关 Node 测试 28 项通过。
- 两台真实模拟器分别只读启动 scrcpy，首帧约 1.5 秒，连续帧输出正常。测试结束关闭自身视频进程和 ADB 转发。
- 真实视频加隔离控制夹具验证桌面及 390px 手机：触摸、输入、风险/验证中保持窗口、正常后关闭，无横向溢出。输入和异常状态转换都使用夹具，没有向生产 App 注入测试输入。
- 预览、正式内网、正式公网浏览器验收均通过：七通道、健康按钮灰色、300 秒巡检配置、第二账号投屏路由、风险不成功、ready 关闭、手机布局、无 JS 错误及无生产测试 POST。公网登录异常和视频响应在浏览器测试中使用隔离夹具；并未强制退出真实账号进行一次完整的生产重新登录。
- 早期视频握手/ffmpeg 探测延迟、移动夹具等待、导航测试 URL 字符串断言及回归测试依赖路径失败均已纠正并复测。没有将失败轮记为通过。
- 最终 99/99 源码与服务器映射一致，证据见 `evidence/`。当前恢复包为 `geo-monitor-deploy/releases/20261015/unified-current/`，原运行状态、凭据和数据库不打包。

16:47 核对：DeepSeek 第一台 22/63、第二台 12/63，均正常登录、running/rate_wait、无待回传，采集 PID 仍为 30871 和 46395。豆包两路、文心、百度、元宝当天已完成。未改题目、轮数、11–19 分钟发送间隔、每日调度或用户暂停；仅重启状态服务、每日控制服务及 Dashboard，没有重启采集 worker。

## 部署和回退资料

服务器维护目录 `/opt/monitor/geo-capture/maintenance/20261017-scrcpy-public/` 包含 release.json、原代码备份、构建日志、QA JSON 和截图。Docker 回退镜像见 release.json 的 rollback 字段；回退前必须同时评估相应后台模块，不能覆盖现有运行队列。预览容器在正式验收后移除。

主机安装 Ubuntu 源 ffmpeg 4.4.2。scrcpy-server 与 Apache-2.0 LICENSE 位于 `/opt/monitor/geo-capture/vendor/`；server SHA256：`26cbc9ad0aced6c2282455bef4fb43462605c1f8758c74b4ab1dbf818c229daa`。

协议依据：[scrcpy 官方架构说明](https://github.com/Genymobile/scrcpy/blob/master/doc/develop.md)、[5.0 服务端选项](https://github.com/Genymobile/scrcpy/blob/v5.0/server/src/main/java/com/genymobile/scrcpy/Options.java)、[控制协议读取器](https://github.com/Genymobile/scrcpy/blob/v5.0/server/src/main/java/com/genymobile/scrcpy/control/ControlMessageReader.java)。
