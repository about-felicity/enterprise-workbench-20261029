# 2026年10月21日 创作下载与正文质量修复

用户反馈全量及单篇ZIP无法打开，正文反复出现“原文……”，要求重点修复文章质量。

## 已核实

初始159篇（新任务77、历史82）。原始公网、局域网、8804直连的全量ZIP及单篇ZIP均返回200，CRC通过，SHA与响应头一致；公网全量13231339字节、1811条目、159篇，路径最长132字符，未复现二进制损坏，不能编造用户坏文件的具体原因。Windows Downloads旧article.zip是19日的164字节零篇清单包，不能认定它就是21日用户截图下载的文件。

下载已改为前端验证类型、PK头、ZIP结束目录、可用时验证SHA；登录HTML、JSON错误、截断文件不保存为ZIP，面板显示具体错误。服务使用同一份bytes计算SHA并发送，避免重复读取间的文件变化；空筛选不再生成零篇假成功压缩包，直接提示。真实浏览器下载单篇CRC通过，Windows .NET ZIP reader读完12条目。错误注入3种均正确拦截，无页面JS异常。证据服务器maintenance/20261021-content-quality/qa/download.json、browser-package.zip。

正文根因不是显示问题：内部研究KU普遍带“原文称/原文建议”，产品approved事实把可用的名称、规格、成分与“知识库/未核验/不能推定”等内部备注写在同一text，写作模型会照搬。旧审稿缺硬性正文门槛，且来源未核验的功效、品类概括、医学机制仍可能被归为source_claim后流入写作。

## 已部署 v10

- consumer_voice.py：正文过程语言和反复审计套话硬性检查，首段需独立。
- consumer_prompts.py：产品中性事实子句与内部备注分离，PF编号/原资料不变；排除未验证机制/功效/风险知识，保留有证据的中性组成与比较子句，记录投影。完整文章采用结构化段落，同一text生成正文与事实映射；独立审稿仍单独请求。
- staged_editorial、daily_editorial：新正文只能引用投影允许的KU/PF，最终包保存consumer_projection.json；原研究、原Word、API回执、原稿和账本保留。
- 常规两类写作也使用上述投影；不只修补本次样稿。来源合同、用户配置与费用上限未放宽。
- CreationClient：仅针对完整JSON对象后附加固定`,"type":"json_object"}`这一已现场复现的无关格式标记做无付费投影；finish_reason必须stop，任意多余文本/第二对象/截断不接受，原响应保留。
- 旧稿不满足正文门槛时停止下载，面板说明保留原稿并待修订。只有重新审稿通过才替换成稿。

44项当前相关回归通过（consumer8、creation36，含下载服务与JSON投影），尚未称全仓测试通过。各次部署备份backup、backup-v2至backup-v10均保留；只重启创作API/worker，部署核对原任务control未变，主GEO采集未动。

## 实际执行记录与限制

初始pilot普通写作仍夹内部备注，后续精简合同修订先遇到篇幅、映射问题；结构化修订遇到旧KU中未经验证机制/功效与JSON格式标记，均被拦住，非无人值守全程通过。这些试验费用全部在原账本和原任务/单篇预算内，没有清账或提高¥0.35、¥5.25、¥10上限。

原截图文章是creation-1792479954-8a96bc88 / 2026-10-20/科普类/05。该文旧版本已quarantine保存。Codex手动编辑重写为2606汉字、3046总字符，并在原预算内单独调用独立审稿通过，没有新增付费writer请求。当前稿标题“眼霜能不能当面霜用 先分清用途与自己的护理需求”。Word SHA5870b00cf517d6acd109f728b22844f8b5a6ac0df781cafb4e11d3a85ae36e6b，draft SHA18584f4dfa38c5b2ce5180d8e93eade252497b0ada4f0f358cdbc0f4a8ff5b3c。Word最终四页均已打开PNG检查，最后一页两行自然分页留白，无裁切缺字。第一次渲染误读传输失败时的零字节文件产生空白页，已废弃；有效检查目录outputs/creation-quality-20261021/eye-pages-final，不使用eye-pages。

手动编辑阶段记录：/opt/monitor/geo-content/runtime/quality-repair/manual-eye-20261021/complete.json。原任务仍是我们维护产生的consumer_prompt_maintenance暂停，尚需在把旧失败票据标记为被本次有证据修订替代后恢复，仅可恢复本次维护暂停，不能恢复其他用户暂停。

另一原生产pilot是creation-1792526406-8f93ccca / 2026-10-21/科普类/04，目前旧稿仍在quarantine，尚需修订恢复。该root因我们此次pilot产生needs_attention暂停，不能把它与用户暂停混为一谈。原root20 budget拒绝发生在发送意图之前，已验证request/api_state/response文件和费用预留均不存在后将该ticket记needs_attention，active记SUBMITTED；原执行记录及proof在repair_evidence/consumer-budget-not-sent，未重发未知请求。

## 批量修订正在执行 不能重复启动

独立维护模块creation.quality_repair，一次性处理125篇严格正文规则命中的已保存稿件。保留原采集日期、研究、成稿备份和原费用范围，不重采集、不恢复原用户暂停；新修订在独立目录以原job/scope/日期/篇号计费，原上限照用。原任务完成后新增修订日志与content_revision.json，重审通过才原位替换，附带审核/溯源。两个线程共享事务账本，未知发送不重发；预算不足或审核失败保留原稿、保持不可下载。

当前批量单元：geo-creation-voice-repair-20261021.service。2026-10-21已启动，尚在跑，不要再次并行启动！旧pilot、pilot2、pilot3、pilot4均已退出。当前批量命令没有retry-known-failures，所以早期3个needs_attention不会重复收费；125篇清单中已有1篇新科普自动重写和重审完成，其余进行中。不要运行旧deploy/pilot/queue/manual-eye等一次性脚本。

清单：/opt/monitor/geo-content/runtime/quality-repair/20261021-consumer-voice/inventory.json；每篇status.json与attempt-N目录，summary.json只在批量结束更新。用本目录progress.py上传/tmp后只读检查实际状态和原每日账本，不依赖旧summary。

下载修复已验证，截图样稿已重写。全部旧稿尚未修完，不能最终告诉用户全部已经解决或无人值守永不出错。接下来继续核查批次进度、处理有具体原因的失败（不提高预算/不重试未知请求）、补齐两个被quarantine的原生产pilot（第一个样稿已补回，第二个仍缺）、对新稿抽查真实内容及Word排版，最后复验公网/筛选/单篇/Word下载，更新当前源码映射与正式报告。

## 后续记录 v12 覆盖上面的旧运行状态

2026-10-21 北京时间约10:44，当前已部署v12；backup-v11、backup-v12保留。

- 正文结构化JSON的标题款数、产品条目名称由原始outline/名单动态核对生成，保留原API输出；不把当前产品或固定篇数写死。原source location正确传入研究投影。篇幅补写不能锚定标题，避免破坏导语。
- 中性资料投影为纯函数；实际writer付款之前独立执行require_writer_material门槛，不因构建review/test prompt而发起写作或误报资料不足。
- 导出来源元数据建立有文件stat签名失效机制的64项LRU，只缓存小元信息、不缓存整篇采集全文。增加缓存读取次数、别名URL、更新失效及不留全文测试。v12实测status0.258秒，LAN全量bundle1.652秒；没有旧版对照测量，不能据此断言它就是用户ZIP问题的根因。
- 82项engine相关测试、37项creation相关测试通过，共119项；不是全仓测试。真实Chromium再次验证正常下载+登录HTML/JSON错误/截断文件3种拦截，页面无JS异常。
- 最新公网全量ZIP3537631字节、474条目、41篇，SHA c99548d1a5bffb3cae69f662f2d7025fac32219046ad903a1d229d8e792233c4；公网单篇73208字节、14条目，两者CRC通过、响应SHA一致。公网probe运行超过SSH25秒窗口但远端继续只读执行并保存report.json，最终成功；不要把本地SSH等待超时当作公网文件损坏。
- 上述公网ZIP已下载outputs/creation-quality-20261021/已校验成稿包_20261021.zip，Windows.NET读取全部474条目、11296583解压字节通过。没有拿错误页充当ZIP。
- 手动样稿20日科普05已完成，另一21日科普04也以其自己的冻结研究/产品资料做编辑修订，独立review通过，无新增付费writer。后者借用了同主题已编辑稿的组织，修订记录明确说明，不复制采集日期或API回执。Word SHA dabb8f3e0d56f60e153fa36b08f8ef8751da59b18160fffa1d83cde26e373102。后者未单独渲染，不作为已视觉QA的独立Word附件交付；可交付20日已QA的样稿。
- 两个原生产pilot各1个失败票据标记revision_requested并指向真正的新content_revision，未将旧失败结果标accepted；失败票据和原暂停都有backup。只恢复本轮维护产生且reason/revision/epoch精确匹配的两次暂停；用户其他暂停未动。
- 当前源码恢复映射150项全部与服务器SHA一致。source.zip/manifest已更新，新增consumer_voice/consumer_prompts/api_prompts/reference_prompts/staged_editorial映射。

## 批量修订当前已安全收尾 后续不得盲目重跑

v11批量遇到2笔network_delivery_unknown自动停止。v12只继续未发送/maintenance-held的独立文章、单线程，不重发那2笔；后续又1笔unknown。网络结果未知不能清除预留或重发原请求。随后hold_transport_pending.py只暂停未发送的89个sidecar，已发送请求正常收尾；不杀付费请求、不动原任务控制。

截至epoch1792550601，v12 unit已inactive/正常退出；125篇清单：7篇complete、3篇unknown_request、115篇needs_attention。115不是全都API失败，其中很多仍是consumer_contract_maintenance未发送，另外有源文缺竞品中性信息而在付款前拦截、原预算/篇幅/独立审稿未通过的稿件。详细原因在各key/status.json。不是“批量仍在后台修完”！需要进一步处理或等待外部接口可核对状态后继续，不能最终谎称全部旧稿已修复。

包括清单之外两篇手动修订，共9篇已修订重审。当前159篇中41篇可下载、118篇正文门槛不合格暂时拦截，旧文件与记录保留。其余原本通过的稿件不代表本轮都重新审过。

当日账本219调用、已结算¥3.46459988、3笔未结算；原¥0.35/篇、¥5.25/任务日、¥10共享日上限未提高，不清账/不免除历史尝试费用。API未知预留照保留。

后续边界：不要运行已执行的一次性manual/pilot/deploy/finish/drain脚本；不要再次启动retry-known-failures大批量。应先按状态区分未发送、已返回失败与unknown，只有确认从未发送的维护hold可在检查源文充足后继续；未知请求仅核对，不重发。当前系统修复的是新生成正文规则、下载验证和对旧不良稿的拦截，历史全部重写尚未完成。
