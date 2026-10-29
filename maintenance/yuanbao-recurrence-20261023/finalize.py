import hashlib,json,subprocess
from datetime import datetime,timezone,timedelta
from pathlib import Path
D=Path(__file__).resolve().parent;W=D.parents[1];read=lambda p:json.loads(Path(p).read_text('utf8'));sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert sha(D/'evidence.zip')=='52ef57d1973f7ce2c9e9484030befcf7a590577639e3fa8dfc5aa2f4f32ea440'
v=read(D/'evidence/verification-latest.json');test=read(D/'evidence/yuanbao-regression-summary.json');dep=read(D/'evidence/deployment.json');candidate=read(D/'candidate-manifest.json')
assert test['passed']==151 and not test['failures'] and v['mapping_files']==224 and not v['mapping_mismatches']
assert dep['article_budget_and_candidate_unchanged'] and dep['app_pid_unchanged']=='4403'
for n,h in candidate.items():assert sha(W/'yuanbao-deploy'/n)==h and dep['files']['/home/user/redroid-yuanbao/'+n]==h
snap=subprocess.run(['python','-X','utf8','-B',str(W/'maintenance/verify_snapshot.py')],cwd=W,capture_output=True,text=True)
assert snap.returncode==0;snapshot=json.loads(snap.stdout)
now=datetime.fromtimestamp(v['at'],timezone(timedelta(hours=8))).strftime('%Y-%m-%d %H:%M:%S')
h=v['health'];done=h['captured']+h['nontext_processed'];cases=[r for r in v['cases'] if r['state'] in {'completed','completed_nontext'}]
assert all(c['capture_retries']==0 and c['events'].get('send_click_intent_committed')==1 for c in cases)
rows='\n'.join(f"| {n} | `{digest}` |" for n,digest in candidate.items())
report=f'''# 元宝第125题视频卡片读取修复

核验时间：{now}（北京时间）。原批次 `geo-panel-yuanbao-20261023-090004-d6b66215`，21题×8轮、45秒间隔，批次和原问题未重建。

## 实际原因

本次从124/168停止在第125题“推荐一款护手霜”。App PID4403持续存活，4GiB上限生效，工作内存约1.1—1.2GiB；cgroup仍为历史oom=7、oom_kill=4，没有新增计数。本次证据不支持把它再次归为内存退出。

原请求 `876a3acdca7609a26c7eb286254afba7`、会话 `0RTB4lSYXbs`、回答 `0RTB4lSYXbs_2` 已全部绑定。原生 Message/Content 均COMPLETED、EOF=true、isBusy=false，但正文只有 videoBoxV2占位符。实际App界面显示“相关视频”、视频标题和作者；独立原生数据库中，同一AI消息的 `raw_data.speechesV2[].extra.replaces` 和 `ChatMessagesContecnt.extra.replaces` 均有同一份完整视频元数据。

旧读取器只消费Markdown视图的 `render_snapshot.i.replacesJson`，该字段一直为空。于是解析器一直返回 `native_video_card_pending`，worker超过900秒后仍等待原请求。前几次处理的内存退出/会话恢复路径不能覆盖这个分支。此前视频测试只覆盖了卡片已经出现在视图中的情况，漏掉了“视图没有、同请求数据库已有”的真实组合。

## 实际修复

- 新增 `stored_replacements.py`：仅在原生已完成、纯视频、最终渲染身份明确且卡片字段为空时，读取同会话/同回答/同content_id/同trace_id的原生存储。
- 同时核对原问题、首次HUMAN/AI配对、发送时间、两处独立替换元数据完全相同、正文占位ID与全部卡片ID相符。不按标题猜会话，不接受额外轮次或相互冲突的数据。
- `native_client.py`在EOF后接入只读补齐；`native_core.py`从独立的、带哈希与身份绑定的 `persisted_replacement_snapshot` 读取卡片。原渲染快照保持原样，没有假装原字段已加载。
- 所有视频条目和App提供的播放器/资源信息原样保留，继续走既有 `completed_nontext` 和审计回传；不伪造视频文字、不编造网页来源、不计入成功文字统计。
- 未更改发送器、问题、间隔、内存额度、未知发送保护或普通文字/来源完整性标准。新读取路径没有HTTP、UI导航或App数据库写入。

## 真实验证与运行状态

上线前先在隔离候选中读取第125题实际原请求：旧路径为 pending，补齐后为 nontext_complete，完整保留1张卡片/1个视频。随后备份源码和tasks.sqlite，仅停止/重启原元宝采集reader以加载修复；App/容器没有重启，PID前后均4403。没有清队列、重新发题或创建测试批次。

上线后第125题已经完成视频审计及processed回执，原send_click_intent_committed仍只有1条，capture_retries=0。第126—131题随后继续正常采集。截至上述核验时间：

- 完整文字回答 **{h['captured']}**，processed **{h['geo_processed']}**，PostgreSQL success **{h['geo_processed']}**，一致。
- 视频回答 **{h['nontext_processed']}**，单独processed，nontext_pending=0；不混入文字success统计。
- 共处理 **{done}/168**，当前第{h['progress']['ordinal']}题，阶段 `{h['progress']['phase']}`；service active，delivery_errors为空。
- 核验涉及的已完成题均只发送一次，未安排capture_retry。4GiB内存配置保留，本次无需再加内存。

真实证据在 `evidence/actual-probe.json`、`evidence/verification-latest.json`。原始UI层级、原生模型和数据库只读现场留在服务器私有维护目录 `/opt/monitor/geo-capture/maintenance/20261023-yuanbao-recurrence/`，本地只导出非敏感摘要，不复制登录数据或完整原生数据库。

## 回归、保护和恢复包

目标Linux已有worker venv执行：元宝60项（原46+新增14）通过，共享/豆包相关91项通过，共 **151项通过**。新测试覆盖真实缺口的解析前后差异、原请求身份、错误trace/content/会话、时间窗、额外轮次、元数据冲突、正文遗漏、卡片ID覆盖、原生EOF、只读性、缓存证据篡改和NativeClient实际接入。原有断言没有删除或放宽。

保留初轮失败日志：新增客户端夹具缺少精确问题字段v，修正夹具以满足真实身份校验后通过；扩大共享回归时缺少已有soak_sequence模块搜索路径，补充既有目录后91项通过。另一个隔离现场探针首次缺少未改动的native_models.js，补齐依赖后再真实验证，源码和原始任务未因此改动。

四份已部署文件选择性更新恢复映射，**224/224与服务器SHA一致**；源码快照 **{snapshot['files']}项字节核验通过**。没有运行全量打包，不把未部署的文章候选放入生产。`--live-local`另发现4份本地文章源码与生产快照的未部署差异，本轮未覆盖它们；快照文件自身全部匹配。

文章共享设置、费用账本2006行完整摘要和结构分析v3候选源码均保持部署前状态。本轮没有文章/DeepSeek或余额API请求；元宝仅继续原来已授权的后续问题。

## 修改文件与SHA256

| 文件（yuanbao-deploy下） | SHA256 |
| --- | --- |
{rows}

部署前源码和任务库备份：`{dep['backup']}` 以及同维护目录 `before-tasks.sqlite`。回退应仅恢复对应reader源码，保留当前任务库和已入库结果，不能用旧数据库覆盖后续进度。

## 尚未验收

本次已经验证真实原请求补齐、视频审计回传和后续6题连续推进；整批168题尚未跑完，跨日无人值守也未在本轮完成。数据库中元数据本身缺失或身份冲突时仍会保持待核对，不能为了推进队列把不完整结果算成功。不能据此承诺第三方App以后永不出现新格式或故障。
'''
(D/'REPORT.md').write_text(report,encoding='utf8')
line=f'> **{now}（北京时间）：元宝第125题停滞已修复。实际为纯视频已完成、Markdown卡片字段为空但原生存储已有完整元数据；新增严格同会话/消息/trace/首次问答的只读补齐。原题只发送1次、视频processed=1；后续126—131题继续，当前文字{h["captured"]}/processed{h["geo_processed"]}与PG一致，合计{done}/168。151项相关回归通过，224项恢复映射服务器SHA全一致；仅reader重启，App PID4403、4GiB内存及文章预算/候选保持。整批与跨日未验收。见[元宝视频卡片修复报告](maintenance/yuanbao-recurrence-20261023/REPORT.md)。**'
for name in ('CURRENT_PROJECT_HANDOFF.md','PROJECT_STATUS.md'):
 path=W/name;old=path.read_bytes();nl=b'\r\n' if b'\r\n' in old else b'\n';path.write_bytes(line.encode('utf8')+nl+nl+old)
verification={'at':now,'tests_passed':151,'new_tests':14,'real_original_request_recovered':True,'processed_total':done,'original_send_count':1,
 'capture_retries':0,'mapping_files':224,'mapping_mismatches':0,'snapshot_files':snapshot['files'],'snapshot_errors':0,
 'article_budget_and_candidate_unchanged':True,'article_api_calls':0,'new_extra_batches':0,'container_or_app_restarted':False,'reader_restarted':True,'all_day_acceptance_complete':False}
(D/'verification.json').write_text(json.dumps(verification,ensure_ascii=False,indent=2),encoding='utf8')
manifest={p.relative_to(D).as_posix():{'sha256':sha(p),'bytes':p.stat().st_size} for p in D.rglob('*') if p.is_file() and p.name!='evidence-manifest.json'}
(D/'evidence-manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(verification,ensure_ascii=False))
