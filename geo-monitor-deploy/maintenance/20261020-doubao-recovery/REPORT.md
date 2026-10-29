10:46最新复验：20/105均真实PG保真，新增第20题487字10来源、首问身份通过；正准备第21题。豆包1与每日控制服务active，未重启其他通道。以下19条是前一分钟历史检查时点。

# 豆包2 App低内存退出与原请求恢复（2026-10-20）

用户要求修复豆包2持续卡住。现场当天原批次geo-panel-doubao2-20261020-090001-6bcafb90为21题×5轮，16/105已processed，第17题“推荐一款爽肤水”原请求4ef05a5c-d849-4dd6-b1da-1f2e369f0210已服务器确认但本机回答停status24/loading“正在搜索”。09:22:51北京时间Android ApplicationExitInfo明确LOW_MEMORY，PSS1.2GB/RSS1.5GB；App进程已无且桌面Launcher前台，worker则持续读旧SQLite并报running_recovery。不是由登录失效证据得出，也不能称宿主机kernel OOM：容器memory.events oom/oom_kill=0、Docker OOMKilled=false。宿主机可用约3.7–5.4GB，swap接近占满。

只am start原豆包2 App后，原第17题同步为status21完成，600字11来源，保留原RID且send_click仅1次，已真实PG核对。检查UI时本助手打开侧栏，与worker继续准备下一题发生干扰；旧assert_fresh_chat仅检查“采集任务编号”标记，对纯问题不能确认新会话，随后第18题进入旧CID（16个先前用户turn）而被严格correlate拦截未入库。这是本次操作干扰及旧准备门禁共同暴露的问题，未放松关联检查。确认该18题原请求已ack、唯一回答status21且所有块完成后，将完整失败原始请求/回答归档至服务器backup/rejected-context-attempt0.json和failed_attempts；仅此题一次受控新尝试，原任务ID、问题、attempt0 baseline和日志保留。不是未知发送重试，不写入负样本。隔离仅豆包2实例worker运行时mask后停止，部署完unmask并恢复同批次，未修改用户当日配置、未建新批次；其他workers未重启。

修复：native_readback_guard.py每30秒检查准备后未完成请求的App进程；严格区分pid不存在与探测连接失败，只在进程确实不存在时am start原App补读，不force-stop、不新建对话、不点击发送；10分钟最多3次唤起并持久化退避，手动暂停/STOP不唤起，已完成结果不唤起。QuestionOnlyAndroid在准备和发送前确认真正空白入口、无侧栏/历史回答控件，关闭残留侧栏后正常创建新对话，点击发送前再次校验。后台仍保持原请求、原发送意图、两次完成快照和完整来源门槛。长时间等待写明原请求stalled并补充面板App退出/唤起/退避中文阶段。面板8803根路由真实返回新文案，无需重建前端。

豆包2容器动态memory3GiB→4GiB，memory+swap6GiB→7GiB，保持额外swap额度3GiB，未重启容器或禁用Android内存保护。限制随当前Docker容器配置持久，重建容器时需复用此资源设置。仅提高上限以降低回收风险，不保证App不会再次退出；进程监测用于恢复此类退出。

验证：新增5项（真实空白UI、进程缺失只唤起、存活/完成不唤起、暂停/停止/探测错误不唤起、重启后预算仍有效）及9项原问题/身份回归，本机和服务器各自通过；这两轮不得合并虚报为28个独立用例。真机严格空白入口检查通过。PG逐条核对19条正文/来源/引用，19/105已入库且第20题生成中；17原请求未重发、18修复尝试478字12来源、19为542字12来源，均唯一用户首问；错误上下文18原RID不在PG。真实回执继续同步，无待回传错误。acceptance.json为10:45时点，不代表105次已全部完成。

源码恢复映射增加新guard，124/124服务器哈希一致；服务器备份/opt/monitor/geo-capture/maintenance/20261020-doubao-recovery含原任务SQLite及被替换代码。repair_doubao_oom_20261020.py为有断言的一次性修复记录，不可重跑。新的UI检查或人工导航必须先隔离目标worker，避免再次与自动新会话准备争用界面。
