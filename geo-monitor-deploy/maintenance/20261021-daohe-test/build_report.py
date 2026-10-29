"""Package diagnostic text and findings; never label rejected text as approved."""
import json,re,hashlib,zipfile,shutil
from pathlib import Path
from collections import Counter
M=Path(__file__).resolve().parent;W=Path.cwd();OUT=W/'outputs/daohe-test-20261021';OUT.mkdir(parents=True,exist_ok=True)
data=json.loads((M/'diagnostic-texts.json').read_text('utf-8-sig'));report=json.loads((M/'test-report.json').read_text('utf-8-sig'));reviews=json.loads((M/'direct-review-final.json').read_text('utf-8'));closing=json.loads((M/'closing-verification.json').read_text('utf-8-sig'));browser=json.loads((M/'browser-result.json').read_text('utf-8-sig'))
assert data['readable_texts']==14 and report['samples']==14 and report['ready']==0 and len(reviews)==14
assert report['reserved']==0 and closing['daily_cap_restored']==10 and closing['new_unknown_requests']==0
index={(r['job'],r['category'],r['number']):r for r in reviews};counts=Counter();manifest=[]
lines=['# 道和小绿瓶十四个样本真实测试报告','','**本轮测试未通过：排行7个样本、测评7个样本，合格可交付稿0篇。** 共12份正常落盘草稿，另2份为未通过结构校验的原始模型答复阅读视图。14份可读文本均已逐篇直接检查，不签发成稿合格证。','','这些文件用于定位问题，均标为待修订。生产下载继续拦截；本包不包含合格Word，也不能作为可发布文章包。','','## 实际执行与费用','','- 用户Word知识库导入；自拟7个问题，百度及文心各7/7采集完成。232个候选网页抓取后保留101篇完整媒体正文。','- 原任务分配排行7、测评5；补充两篇独立且未使用的比较原文，合计7+7。旧进程缓存错误的零付费准备记录另存，没有重发原未知请求。',f"- 本批结算¥{report['charged']:.8f}，未结算预留¥{report['reserved']:.2f}。单篇上限¥0.35、同一计划整批上限¥5.25均保留。",'- 单篇拦截按已结算加拟发请求的最坏费用判断，因此账单小于0.35元仍可能停止。没有另建任务绕过某篇已用额度。',f"- 共享日上限测试期间临时16元，现恢复10元；今日已结算¥{closing['ledger']['charged']:.8f}，原3笔未知预留¥{closing['ledger']['outstanding_reserved_today']:.5f}。本批新未知0，原11份控制SHA一致。",'- 恢复10元后，观察器因今日累计占用超过当前设置显示daily_budget_exceeded；保留提示、临时额度租约及账本，没有删账或重置基线。跨日无人值守仍未验收。','','## 样本结果','','| 测试编号 | 文本状态 | 标题 | 本样本结算 | 直接复核的首要问题 |','| --- | --- | --- | --- | --- |']
for a in data['articles']:
 key=(a['job'],a['category'],a['number']);review=index[key];assert review['text_sha256']==a['text_sha256']
 counts[a['category']]+=1;number=counts[a['category']];label=a['category']+str(number).zfill(2)
 safe=re.sub(r'[<>:"/\\|?*\x00-\x1f]','_',a['title'])[:48].rstrip(' .')
 relative=Path('待修订测试文本')/a['category']/(str(number).zfill(2)+'_待修订_'+safe+'.md')
 path=OUT/relative;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(a['text'].encode('utf-8'))
 assert hashlib.sha256(path.read_bytes()).hexdigest()==a['text_sha256']
 mode='落盘草稿未通过' if a['flavor']=='materialized_rejected_draft' else '原始模型答复阅读视图 未通过结构校验'
 entry={k:a[k] for k in ('job','category','number','title','flavor','text_sha256','reading_view_proof','primary_url','primary_title','charged')}
 entry.update(test_label=label,file=relative.as_posix(),approved=False,review=review);manifest.append(entry)
 title=a['title'].replace('|','／');reason=review['issues'][0]['reason'].replace('|','／')
 lines.append(f"| {label} | {mode} | {title} | ¥{a['charged']:.5f} | {reason} |")
assert dict(counts)=={'排行类':7,'测评类':7}
lines += ['','## 逐篇直接复核','','直接复核按最终文本SHA绑定，保留具体原句与断点，不把接口返回成功或关键词命中当作合格。自动审稿历史错误在执行结果JSON中保留；下列为Codex读完整文本后的具体判断。']
for entry in manifest:
 review=entry['review'];lines += ['',f"### {entry['test_label']} {entry['title']}",'',f"文本：[待修订测试文本]({entry['file']})；SHA256 `{entry['text_sha256']}`。"]
 if review.get('logic_observation'):lines += ['',review['logic_observation']]
 for issue in review['issues']:lines += ['',f"> {issue['quote']}",'',issue['reason']]
lines += ['','## 通用代码修复与验证','','修复均按体裁、章节、证据和队列状态实现，引擎中没有为道和新增品牌分支。本次产品及问题只存在于测试配置。',
'','1. 标题写实测但正文有明确比较维度的多产品来源，按通用结构识别测评；旧任务分类快照保留。',
'2. 写作输入提供固定S编号和主题顺序，成稿解析逐项校验实际顺序；仅编号齐全但次序改变仍退回。独立逻辑退回可进行有界修订。',
'3. 测评研究提纲保留比较维度和条件式结论角色；两份已付费研究响应通过正常证据与结构校验本地恢复，新增付费0。',
'4. 排除频繁更换、正确使用等行为标题，不能因为含产品类别词就计成一款产品。',
'5. 未核验的备案、认证及报告编号不进入可用PF，防止拆句时丢掉限制条件；原始资料保留。',
'6. 通用推理规则只在当前资料涉及的条件下应用，移除跨品类显色等示例词，避免规则反过来污染正文。',
'7. 单篇预算在发送前不足时，只退回该篇；整批和共享预算仍会暂停，未知发送保护保留。',
'8. 对完整响应中两种唯一可解析的单闭合符号错误做无损格式投影，保留原答复，仍执行完整事实、章节与逻辑验收。',
'9. 成分表、标签、说明书和报告的原文属于消费者核对对象，不再被一概当成生产过程措辞；真正的参考文章解读继续拦截。',
'','最终阶段回归：引擎111项、创作69项，共180项通过。恢复映射170/170项服务器SHA一致；服务器源码281份，本地总快照479个文件、475个唯一哈希条目一致。',
'','本批有人工排错、多次代码修订、修复和补充素材，不是最终版本一次成功的验收。后续仍需在完整新批次证明质量稳定；不能用本次回归测试数量宣称所有文章的逻辑已经完善。',
'','## 浏览器与文件检查','',f"真实Chromium：本批合格列表0，14个样本的Word接口均HTTP400，空筛选HTTP{browser['empty_filter_http']}，页面JavaScript错误{len(browser['page_errors'])}。",'','本批无合格Word，所以合格Word版面渲染和合格稿ZIP的CRC校验不适用；没有将未验收Word提供为成品。本地诊断ZIP另行检查CRC及14份文本SHA，只含待修订文本、报告与诊断记录。',
'','## 当前限制','','- 多篇仍出现不支持的推论、范围变换、数量错误、前后口径冲突或资料解读过重；不能恢复为合格下载。','- 两篇没有形成正常落盘正文，阅读视图保留模型原顺序，未修复其章节和产品身份问题。','- 历史197份待修订文本没有因为本次代码部署就自动改好。','- 19日空筛选零篇ZIP原因已确认；21日原坏ZIP仍需原文件才能归因。','- 试验文本里的产品与报告主张不是本报告对其真实性或效果的背书。']
report_path=OUT/'十四篇测试报告.md';report_path.write_text('\n'.join(lines)+'\n',encoding='utf-8')
result={'purpose':'Diagnostic inspection only','sample_count':14,'materialized_drafts':12,'unvalidated_response_views':2,'approved_count':0,'by_genre':dict(counts),'charged':report['charged'],'articles':manifest}
(OUT/'诊断清单.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
for source,name in [('test-report.json','执行结果.json'),('direct-review-final.json','逐篇直接复核.json'),('browser-result.json','浏览器验证.json'),('closing-verification.json','预算与未知请求核对.json')]:shutil.copyfile(M/source,OUT/name)
archive=OUT/'道和小绿瓶14份待修订测试文本与问题报告.zip'
files=[report_path,OUT/'诊断清单.json',OUT/'执行结果.json',OUT/'逐篇直接复核.json',OUT/'浏览器验证.json',OUT/'预算与未知请求核对.json']+[OUT/a['file'] for a in manifest]
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for path in files:z.write(path,path.relative_to(OUT).as_posix())
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None
 m=json.loads(z.read('诊断清单.json'));assert m['sample_count']==14 and m['approved_count']==0
 for a in m['articles']:assert hashlib.sha256(z.read(a['file'])).hexdigest()==a['text_sha256']
summary={'samples':14,'drafts':12,'raw_response_views':2,'approved':0,'charged':report['charged'],'diagnostic_zip_crc_ok':True,'text_hashes_verified':14,'archive_bytes':archive.stat().st_size}
(M/'final-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8');print(json.dumps(summary,ensure_ascii=False))
