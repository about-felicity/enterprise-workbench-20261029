"""Read-only audit of the stopped model calls; writes reports in this run only."""
import hashlib,json,re,zipfile
from pathlib import Path
ROOT=Path('/opt/monitor/geo-content/runtime/acceptance/20261023-rank01-staged/rank01-staged-20261023T120816-e50a98ac')
read=lambda p:json.loads(Path(p).read_text('utf-8-sig'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
summary=read(ROOT/'summary.json');cost=read(ROOT/'cost_ledger.json');auth=read(ROOT/'preflight.json')
assert summary['settings_restored'] and summary['protected_inputs_unchanged']
assert cost['model_request_count']==2 and cost['reserved_unknown_cny']==0
assert read(Path('/home/user/geo-editorial/runtime-api/settings.json'))==auth['settings_before']
assert read(ROOT/'job.json')==read(Path('/opt/monitor/geo-content/runtime/runs/creation-1792575159-0a8f9221/job.json'))
calls=[]
for row in cost['model_requests']:
 p=Path(row['directory']);answer=read(p/'answer.json');request=read(p/'request.json');content=answer['content']
 assert answer['finish_reason']=='length' and request['max_tokens']==2400
 ids=list(dict.fromkeys(re.findall(r'AS\d{3}',content)))
 calls.append({'path':str(p),'finish_reason':answer['finish_reason'],'max_tokens':request['max_tokens'],'usage':answer['usage'],'partial_structure_ids':ids,'response_characters':len(content),'response_tail':content[-200:]})
audit={'status':'technical_failure','model_calls':calls,'reason':'Both actual structure responses reached the frozen analyzer output cap and were incomplete; bounded known-failure retry also truncated. The local fallback is explicitly degraded and cannot satisfy the required real structure-analysis acceptance.','fallback_is_not_model_result':True,'article_generated':False,'facts_review_executed':False,'logic_review_executed':False,'arbitration_executed':False,'new_unknown_requests':0,'protected_inputs_reverified':all(Path(p).is_file() and sha(p)==v for p,v in auth['protected_before'].items()),'settings_restore_reverified':True,'isolated_job_limits_restored_to_original':True,'no_further_api_calls_by_audit':True}
(ROOT/'final-audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
rows=[]
for i,v in enumerate(calls):
 rows.append(f"| {i+1} | {v['usage']['prompt_tokens']} | {v['usage']['completion_tokens']} / 2400 | length | {cost['ledger_after']['run_rows'][i]['charged']:.8f} |")
report=f'''# 排行01首轮真实执行结果

执行身份：`{ROOT.name}`  
冻结候选：`candidate-b2-repair-entry-v2-20261023`  
原任务：`{cost['same_job_id']}`  
原计费范围：`{cost['same_scope']}`，原文章日期 2026-10-21、排行类 01。

本轮实际调用了 DeepSeek，最终为 **technical_failure（技术失败）**。预算预检通过，但两次结构分析答复均达到 2400 token 输出上限并被截断；没有进入正文生成。因此没有本轮文章 Word 或 Markdown，也没有事实审稿、逻辑审稿或仲裁结果，不能判断文章合格。

## 预算与实际调用

首阶段发送前保守预留上界为 **{auth['stage1_upper_cny']:.6f} 元**，覆盖结构分析、14 个写作组成部分和两项独立审稿，共 17 个初始请求。每次实际发送前均通过既有 SharedBudget.reserve 和本轮新增支出、剩余必要阶段预留检查。未提前发送仲裁请求。

| 请求 | 输入 tokens | 输出 tokens / 上限 | finish_reason | 账本已知费用 元 |
| --- | ---: | ---: | --- | ---: |
{chr(10).join(rows)}

计费模型请求共 **2 次**；两次均有真实 usage、请求 ID 与答复，不属于发送结果未知。新增已知费用 **{cost['known_cost_cny']:.8f} 元**，新增未知请求预留 **0 元**，本轮 7.20 元授权余量 **{cost['incremental_remaining_cny']:.8f} 元**。以上是现有计价规则根据真实 usage 得出的账本费用，供应商账单金额未另行核对。

历史单篇累计从 0.65319432 元变为 **{cost['ledger_after']['article_used_cny']:.8f} 元**；原 scope 累计从 4.62478644 元变为 **{cost['ledger_after']['scope_used_cny']:.8f} 元**。原有 3 条未知请求保持原状，未重发、未清零。

## 实际阻断证据

冻结 `structure_analyzer.analyze` 用真实保存的完整原文构建请求，每次 `max_tokens=2400`，最多 2 次已知失败尝试。两个实际答复分别输出 2399 和 2400 tokens，`finish_reason=length`，状态均为 `INVALID_RESPONSE / output_incomplete`。`known_failure.json` 与原始 `answer.json` 均已保存。

候选模块随后生成带 `degraded=true` 的程序降级结构。隔离执行器识别这一状态后停止，没有使用降级结构冒充本轮模型结构分析，也没有改动冻结代码提高输出上限或新增第三次请求。

本轮问题定位为：**当前真实原文的结构分析输出需求超过冻结 Analyzer 的 2400 token 上限，候选有限重试仍使用同一上限，未能恢复。** 本轮不修改实现或继续付费执行。是否只需提高结构输出预算、或还存在后续文章质量问题，尚未真实验证。

## 已保存与未执行的产物

- `article/writer/structure_calls/attempt-0/`、`attempt-1/`：本轮真实请求、原始答复、finish_reason、usage、请求状态及失败记录。
- `article_structure.json`：**程序降级结构**，不是合格的本轮模型分析结果。
- `claim_ledger.json`：当前真实材料离线编译的可写声明；未被正文写作消费，不代表文章事实审查通过。
- `preflight.json`、`reservation-audit.json`、`cost_ledger.json`：预算预检、逐请求预留及真实结算记录。
- `final-audit.json`：停止后的文件保护、配置恢复和实际失败核验。
- `summary.json`、`failure.json`、`runner.log`：执行终态和失败位置。
- `rank01_first_draft.docx`、`rank01_first_draft.md`、`section_manifest.json`、`review_fact.json`、`review_logic.json` 未产生；对应阶段没有开始，不创建空文件。
- 仲裁未开始：事实与逻辑审稿未执行，没有可仲裁的真实审稿意见。

## 配置、生产及任务保护

共享临时单篇上限 8.00 元已恢复为 **0.35 元**；每日上限始终为 **10.00 元**。隔离 job 的临时 8/12 元限额已恢复为原任务配置；执行期副本保存在 `job-effective-during-run.json`。

停止后重新读取共享设置，与执行前完整配置一致。冻结候选、原任务控制、原稿、输入与旧验收控制文件的全部保护 SHA 再次一致。生产代码未修改、未部署；测评02及其余任务未启动；未执行内容返修、未重置旧修订次数，未创建新任务或计费 scope。

完整文件路径、字节数和 SHA256 见 `SHA256.json`。服务器执行目录：`{ROOT}`。本地下载目录：`C:/Users/78567/Desktop/隐身浏览器/outputs/{ROOT.name}`。

本轮交付的是 **真实请求失败证据及费用记录**，真实文章质量验收未完成。
'''
(ROOT/'acceptance_summary.md').write_text(report,encoding='utf8')
manifest={str(p.relative_to(ROOT)):{'sha256':sha(p),'bytes':p.stat().st_size} for p in ROOT.rglob('*') if p.is_file() and p.name not in {'SHA256.json'} and not p.name.endswith('.lock')}
(ROOT/'SHA256.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
archive=ROOT.parent/(ROOT.name+'.zip')
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for p in ROOT.rglob('*'):
  if p.is_file() and not p.name.endswith('.lock'):z.write(p,str(p.relative_to(ROOT)))
with zipfile.ZipFile(archive) as z:assert z.testzip() is None
print(json.dumps({'archive':str(archive),'archive_sha256':sha(archive),'files':len(manifest)+1,'protected':audit['protected_inputs_reverified'],'core_sha256':{n:sha(ROOT/n) for n in ('acceptance_summary.md','cost_ledger.json','final-audit.json','article_structure.json','claim_ledger.json','SHA256.json')}},ensure_ascii=False))
