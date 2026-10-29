# 豆包提示区块导致完整性校验卡住 2026年10月21日

用户反馈豆包卡住。现场核查：豆包1今日原批次`geo-panel-doubao1-20261021-090003-e1d20b1d`为3/105，豆包2已105/105正常完成，不是两路都故障。

豆包1第4题“推荐一款二硫化硒洗发水”09:03:55约一次发送，原请求`d375664d-794e-4913-bdfc-240100e194c8`绑定CID`38448399816623106`。原生答status21、三个block全部finish=true：10025搜索11源、10000完整正文、10053 tips_block。最后一块为type1的纯文字AI/医疗安全提示。旧question_only_core只接受text/search区块，因此一直DataError Unknown answer block，60秒重读并没有进展。这次不是登录失效、只有商品卡或缺信源，也没有本次OOM证据。

## 修复

- 只增加已核实的原生10053/type1纯文本tips schema：类型、字段及非空文本校验；文本逐字加入body_parts/body_markdown，并单独native_tips、原raw_answer_blocks全量保留。不把提示当信源、品牌结论或独立回答。
- 未完成、未知schema、未知block、未知pc_event仍保持原严格阻断；没有放宽全局门槛。
- 原生无网络信源的已验证完整回答，如包含这种提示，零信源证明也逐块核验并比对完整正文；不把声明有源却缺失的回答当零源成功。
- worker native_validation_backoff现带实际校验原因，面板能显示具体错误，而非只剩通用退避状态。
- 没改今日21题×5轮、45秒间隔、任务日期或批次；只重新加载豆包1worker。豆包2、元宝、网页渠道及App/容器不重启。共享代码对其他在跑进程不强制重载。

## 验证

13项相关question-only/零信源测试通过，覆盖真实tips区块保留、原始块不变、未完成不接受、未知提示type/其他未知块继续阻断及零源proof。真实第4题在staging按原SQLite读取完整通过，才部署。

原任务队列SQLite及源码备份保留于服务器`/opt/monitor/geo-capture/maintenance/20261021-doubao-stall/backup`，原生三块现场native-rows.json、绑定与baseline保留。无清队列、无重新采集。停止原worker曾达到systemd停止超时，处于已prepared原题只读校验，systemd终止后重启；没有重启App、没有丢弃原发送意图或补发。

第4题已经真实采集并入库：642字符、11信源、提示保留；send_click_intent_committed=1、capture_retries=0；原请求不变。processed回执验证通过，PG run `doubao-674e38952d02d863f42a`，day2026-10-21，answer逐字等于完整body.strip、source_capture_complete=true，SHA `8180b67289ab7cc6257fedd09fe0c0c3b31395ee94cbdb2392be3795b6a49495`。verify epoch1792552719时4/105已入库，第5题preparing，delivery_errors=[]。

这是解析兼容修复，不是保证未来任何新块都可自动识别。未知结构仍保留现场并给出具体原因，不静默丢内容或重复提问。inspect/deploy/verify脚本固定本次原批次；deploy已经执行，不可重跑或当日常恢复器使用。
