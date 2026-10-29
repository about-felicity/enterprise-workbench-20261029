历史现场快照：以下描述止于登录完成前；当前运行状态以 ../README.md 及验收报告为准。历史失败尝试保留，不作为现行操作手册。

# 元宝独立无头Android

2026-10-15新增。15:42微信二维码已实际显示，用户完成扫码；15:45扫码后的白屏已恢复为“安全验证／人脸识别”页面。当前仍未完成平台要求的身份校验，尚未证明采集与回传通过。不要将模拟器在线或出现输入框当作已登录／可采集。

## 运行位置

| 项目 | 当前值 |
|---|---|
| 服务器目录 | `/home/user/redroid-yuanbao` |
| 容器 | `yuanbao-hpe14-android13` |
| 独立数据卷 | `yuanbao-hpe14-android13-data` |
| Android | Android13，沿用已验证的Houdini14基础镜像，未复制豆包用户数据 |
| 限额 | 2 CPU、3GiB RAM |
| ADB | 服务器回环5559，经原SSH配置转发到Windows回环15559 |
| 官方包 | `com.tencent.hunyuan.app.chat`，2.88.0，versionCode66517035 |
| 语言 | 系统与应用简体中文；最初的英文界面是模拟器默认en-US导致 |

安装包来源为[腾讯元宝官网](https://yuanbao.tencent.com/)当前JavaScript中默认移动渠道5040对应的腾讯CDN，下载SHA256与HTTP元数据保存在服务器`apk-download.json`。这里的版本是本次官网实际分发版本，不推定其他应用商店渠道一致。

Windows投屏：[open-yuanbao.ps1](../open-yuanbao.ps1)。仅投屏窗口可见，SSH辅助进程隐藏；关闭投屏不关闭服务器模拟器。原豆包和业务服务未重启。

## 当前登录故障

用户输入短信验证码后，登录WebActivity停留白屏。私有日志确认X5的Sandboxed0／1／2渲染子进程循环启动、退出，目标页面为官网`/e/login`；同时存在RFix隔离进程的registerReceiver权限异常，不能仅据此认定它就是退出的唯一底层原因。

初次`setting_forceUseSystemWebview`配置没有生效：当前SDK的WebView构造流程没有读取该调试配置。尝试调用公开兼容API时诊断服务自身退出，调用未成功；尝试保留并移出可选X5文件后，SDK自动重新安装它，故同样未解决。以上失败证据与原文件均保留，不重复该操作。

有效的网页兼容调整来自当前APK实际加载流程：`TbsPVConfig.getDisabledCoreVersion()`读取`app_tbs_64/core_private/tbs_pv_config`的`disabled_core_version`；禁用当前精确版本47803后，SDK走系统WebView回退。15:04:43日志明确`isX5webview:false`、加载`com.android.webview 125.0.6422.113`及系统独立渲染进程；15:06服务协议全文截图验证网页确实显示。未接受协议、获取短信或跳过登录验证。登录页本身仍需用户最终验证。

后续实证：SDK刷新配置后会移除`disabled_core_version`，因此磁盘配置仅临时有效，不能视为持久修复。15:43用户扫码后再次白屏，观察到X5子进程循环；15:45成功调用官方`QbSdk.forceSysWebView()`并重建原有WebActivity后，原登录流程真实显示安全验证页面。持久兼容服务会在每个新WebView构造前调用此API，不再依赖会被覆盖的配置。

早期诊断入口：[精确禁用不兼容内核](../tools/disable_incompatible_x5.py)。原配置在服务器`compat/disabled-core-47803/tbs_pv_config.before`；若要回退，先退出元宝再恢复此文件，不恢复整份旧账号偏好。已知失败内核副本及逐文件哈希留在`compat/x5-core-before`和`compat/x5-quarantine.json`。

原日志、配置和shared_prefs备份只保存在服务器私有目录`diagnostics/login-20261015/`。没有清缓存、删除账号数据或重新安装App。截图证据为本地`artifacts/disabled-core-legal.png`，诊断元数据与原始日志区分保存。

维护工具：[可恢复WebView切换](../tools/repair_login_webview.py)。私有`change.json`记录配置是否原来存在；回退时先退出元宝，再恢复`debug.conf.before`，原来不存在则只移除本次新建的debug.conf。不要恢复整份旧shared_prefs覆盖后来成功的登录。

## 微信二维码与后续安全验证

微信签名请求、二维码图片回调（47554字节）及扫码轮询均成功。逐阶段观察定位到`Up.m.invokeSuspend -> com.tencent.qbar.b.b`的QBar样式解码没有返回，界面一直保留加载状态；不能仅凭这一点进一步断言卡在Houdini的具体指令或系统调用。

[wechat_qr_compat.py](../tools/wechat_qr_compat.py)只让这个样式解码协程返回App本来支持的失败结果，使`Up.n`自动调用`Up.s.U0`显示微信SDK原始二维码。15:42截图及用户实际扫码确认显示成功。没有修改微信签名、二维码内容、授权结果或登录回调。

服务器服务为`geo-yuanbao-wechat-qr-compat.service`，开机启用；仅连接元宝容器回环诊断端口，校验容器标签、独立数据卷、精确APK版本及SHA256，App升级后拒绝套用旧映射。诊断服务使用`--disable-preload`避免当前Redroid中的helper预加载崩溃。会跟随App进程重新附加；不会启动采集、提交验证码或代做身份验证。回退时停止并禁用该服务，正常退出并重开元宝即可解除运行时兼容调整，保留账号数据。

15:55进程更换后的实证补充：ART已有优化可能使`Up.m`替换被内联调用绕过，再次出现已收到46329字节二维码但没有显示。已对元宝单独进程执行ART去优化，15:57再次观察到`sdk_image_fallback_requested`及`sdk_bitmap_ready`并截图确认二维码正常；该兼容处理会在每次附加时应用。未对其他模拟器或系统全局执行去优化，长期采集性能仍待登录后的真实样本检验。

扫码后实际显示“安全验证／人脸识别／前往微信开始验证”。这证明当前元宝登录流程仍要求额外身份校验；尚无服务端风险原因码，不能断言是IP、模拟器或账号限制。二维码加载、网页内核兼容与平台身份校验是不同阶段。当前模拟器没有安装微信；没有擅自安装微信、迁移微信账号或绕过人脸验证。

官方`/e/login`页面公开脚本确认：`safeVerify/detail`返回可用验证类型，客户端优先选择waterwall、verifyPhone，其次face；face流程调用`generateFaceQR`取得`qrPicBase64/page/params`，由`queryFaceQR`轮询。移动App分支只显示跳微信小程序按钮。[show_official_verification_qr.js](../tools/show_official_verification_qr.js)为当前官方face组件显示其内存中已有的原始验证二维码，供手机微信完成核验；不会修改结果、验证码、请求、轮询或回调，也不会导出二维码内容。**15:59实机截图已确认官方小程序安全验证二维码显示成功**，且新建WebView直接正常显示页面，未再次人工重建。等待用户在手机微信完成本人验证，尚未确认服务端通过或App登录成功。这个阶段不能记为账号已登录。

私有证据：服务器`diagnostics/wechat-qr-20261015/`与`diagnostics/wechat-after-scan-20261015/`；日志只向操作输出阶段元数据，原始日志留在私有目录。二维码截图是临时授权材料，不公开发布。

## 采集接入进度与边界

已找到App原生SQLite表`ChatMessages`、`ChatMessagesContecnt`（原App拼写）、`ChatMessageEntities`、`ChatConversationDetail`。当前没有登录后的受控回答样本，尚不能可靠定义完成状态、正文／全部信源／引用的解析规则。

[native_storage.py](../native_storage.py)仅只读发现并校验表结构，不写App数据库；3项测试覆盖只读写入拒绝、其他数据库排除和表结构变化阻断。运行于本模拟器的生产读取需要root权限，不能泛扫其他容器或复制账号数据。

登录成功后，继续实现并实测：每题新会话、发送前落盘唯一任务编号、至少30秒间隔（默认45秒）、不重发未知发送、完整正文／全部信源／引用／搜索词和原始结果保留、相同outbox身份重试回传与processed核对。可复用现有豆包持久队列及GEO已支持的yuanbao接收模型，不能直接套用豆包的数据库字段或以可见截屏片段冒充完整回答。

在原生样本与GEO保真回执未验证前，不启用自动批次、不宣称采集已就绪，也不改变现有五通道控制状态。
