"""Prepare the actual failed sample for inspection, never promote it to approved."""
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'outputs/rewrite-v2-real-sample-20261023'
EVIDENCE = OUT / 'evidence/real-sample'
RUN = EVIDENCE / 'runs/creation-1792742400-a2c61023'
WRITER = RUN / 'days/2026-10-23/jobs/排行类/01/writer'
REVIEW = WRITER.parent / 'review/result.json'
status = json.loads((EVIDENCE / 'status.json').read_text('utf8'))
review = json.loads(REVIEW.read_text('utf8'))
assert review['pass'] is False and review['compliance_check'] is None
assert not list((RUN / 'approved').glob('**/receipt.json'))
for name, target in [('draft.md', '小绿瓶仿写样稿_待修订.md'), ('article.docx', '小绿瓶仿写样稿_待修订.docx')]:
    shutil.copy2(WRITER / name, OUT / target)
cost = sum(c['charged'] for c in status['costs'])
usages = [json.loads(c['usage']) for c in status['costs']]
draft = (WRITER / 'draft.md').read_text('utf8')
checks = {word: word in draft for word in ['43.96%', '33.96%', '27.53%', '14200', '5.9', '140mm', '16.0%', '158', 'G20211805', 'GT00332022056002']}
result = {'status': 'needs_revision', 'new_paid_calls': len(usages), 'estimated_cost_cny': cost,
          'total_tokens': sum(u['total_tokens'] for u in usages), 'draft_count': 2,
          'independent_style_pass': False, 'independent_compliance_executed': False,
          'accepted_article_count': 0, 'production_deployed': False,
          'draft_numeric_presence_only_not_fact_validation': checks,
          'word_sha256': hashlib.sha256((WRITER / 'article.docx').read_bytes()).hexdigest()}
(OUT / 'sample-verification.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf8')
report = f'''# 小绿瓶 V2 真实仿写测试

日期：2026-10-23。结论：真实模型已生成初稿和一次全文重写稿，重写稿仍未通过风格审核，合格成品为 0 篇。当前 Word 是供查看的待修订样稿，未进入正式下载库。

## 本次输入

- 知识库：用户提供的《2.道和小绿瓶防脱洗发水知识库(1).docx》，全文 5636 字符，原文件 SHA256 为 df61fc18e67a880af382eade2822aafaf019e067edebc10d24c543ba3ce43ee7。
- 范文：10 月 21 日采集的《防脱洗发水哪个牌子的效果好？推荐2026公认十大高口碑防脱洗发水完整榜单全面靠谱》，正文 7601 字符。
- 链接：https://baijiahao.baidu.com/s?id=1879562453794511892&wfr=spider&for=pc
- 骨架：用户看过待确认稿后回复“可以继续”，已记录确认；保留 24 项语义功能。

## 实际运行结果

共 {len(usages)} 次真实模型调用，账本估算 ¥{cost:.6f}，合计 {result['total_tokens']} tokens。单篇预算仍为 ¥0.35，没有调整预算或清除旧账。两次 Writer 都一次输出完整文章，没有分节拼接。

首次解析多带 type=json_object 元数据，已保留原答复并在本地完成格式兼容，无新增解析调用。首稿的风格接口返回通过，同时把可选建议写入错误字段，因此未被接纳。助手逐字检查后另行退稿：核心测试数字被泛化、重复核验提醒、局限遗漏及不当价格比较；该人工辅助审阅记录与原模型答复分别保存。

重写后 43.96%、33.96%、pH 5.9、140mm、16.0%、158 元及编号均进入正文，2 周／12 周的内部冲突被注明。但这只证明数字进入正文，不代表每个主张已经通过事实审核。

独立风格复审未通过；系统因此跳过事实合规调用。一次全文重写额度已用完，任务停在 needs_attention，没有第三次 Writer 调用，也没有合格回执。此结果不能宣称完成了双维审核。

## 助手直接阅读后的主要问题

1. 竞品仍沿用“某品牌偏体验，小绿瓶偏证据”的重复对比句式；原文未提供同口径的资料，不能得出本品资质、证据或体验更优。
2. 首款详解仍多次重复“未核验／你自己核对”，削弱选购文章的流畅度；来源范围可以集中交代。
3. 正文“含商业合作关联”没有本次材料中的实际合作事实作依据。后续通用生成提示已改为说明自有产品推广定位，不编造合作身份；这版稿件尚未重新生成。
4. 不能机械接受审稿模型的每条建议。其要求对 2 周／12 周冲突“明确取舍”不能作为擅选周期的依据；保留冲突、避免确定效果才符合原始材料。该建议没有被自动执行。
5. 竞品的具体型号、功效和价格均来自旧范文，未在本次独立联网核实，当前稿不能作为可直接发布的独立测评。

## 验证边界

程序回归结果见 maintenance/rewrite-v2-20261023/linux-verification.json；使用真实队列和真实 API 的样例结果为 0/1 合格。UI 文件未为本次重构修改，已测试原有文章列表、下载接口、Word 和归档兼容路径。代码仍为本地候选及服务器隔离目录，未部署生产。

本次总 token 已明显超过文档 5k 目标；仅原文解析输入就达 5267 tokens，完整保留长原文和知识库时不能宣称这个目标已达成。由于存在人工停顿、格式修复和两版稿件，亦不能声称全流程三分钟验收通过。缓存复用后单篇成本尚未做第二篇真实验证。

独立复审原始结果见 evidence/real-sample/runs/creation-1792742400-a2c61023/days/2026-10-23/jobs/排行类/01/review/result.json；原始请求、答复、费用、版本和骨架确认均在 evidence 内保留。
'''
(OUT / '测试结果与问题.md').write_text(report, encoding='utf8')
print(json.dumps(result, ensure_ascii=False, indent=2))
