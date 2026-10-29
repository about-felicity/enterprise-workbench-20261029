import json
from pathlib import Path
W=Path(__file__).resolve().parents[2];B=Path(__file__).resolve().parent
live=json.loads((B/'live-verification.json').read_text('utf8'))
assert live['articles_visible']==7 and live['deployed_hashes_verified']==19
summary=('> **2026-10-24 最新：眉毛新知识库七问题已完成百度/文心14/14采集，七篇经自动生成、定点修复与事实审核后全部进入成稿，生产HTTP逐篇下载7/7通过。'
 'V2核心和跨日会话复用已上线，19份生产文件哈希一致，UI未改。原每日计划已切换至新知识库、七问题、目标七篇，每日01:00采集/04:00写作（北京时间）；'
 '旧今日任务暂停并保留历史。192项回归通过，累计86笔调用估算1.02920208元、未结算0，预算未提高。'
 '本轮有工程修复干预；尚未观察下一自然日完整运行，不宣称跨日无人干预验收完成。'
 '见[最终文章](outputs/brow-unattended-20261024/最终文章/阅读索引.md)及[上线报告](maintenance/brow-unattended-20261024/REPORT.md)。下方为历史记录。**\n\n')
for name in ['PROJECT_STATUS.md','CURRENT_PROJECT_HANDOFF.md','SOURCE_CONTROL.md']:
 p=W/name;old=p.read_text('utf8')
 if not old.startswith(summary):p.write_text(summary+old,encoding='utf8')
p=W/'geo-monitor-deploy/creation/README.md';old=p.read_text('utf8')
line=('2026-10-24 最新上线：新眉毛知识库七问题，14/14采集、7/7成稿、7/7生产HTTP Word下载通过；192项回归通过。'
 '审核改为有证据的事实错误拦截，风格建议不退稿，最多两轮精确片段修复并复审。新任务自动骨架复核、完整原始资料一次输入、预算内输出规划、按计划/渠道跨日复用会话已生效。'
 '原每日计划01:00采集、04:00写作、目标七篇；UI不变。下一自然日完整运行尚待观察。\n\n')
if line not in old:p.write_text(old.replace('# GEO内容创作中心\n\n','# GEO内容创作中心\n\n'+line+'以下为历史记录。\n\n',1),encoding='utf8')
p=B/'REPORT.md';old=p.read_text('utf8')
update='''## 最新结果：已上线（用户确认“对，开始”后）

- 原同一任务七篇全部完成并进入成稿，`day_status=complete`、当前待处理票据0。未将用户认可直接伪造成模型通过。
- 审稿返回具体正文引文、原始依据和修改要求。程序驳回可确定的误判：要求无需修改、原句与建议相同、明确停用/咨询提示、正确算术、原始资料直接支持的数字及未出现在正文里的促销标签。
- 真实问题用精确片段替换修正，未人工改写正文。最多两轮定点修复，历史一次全文重写计数未重置；修订后独立复审，最终证书仍绑定正文、产品、骨架和来源。
- 增加程序标题数量/明确评分产品清单及单价检查；第五篇标题已改为8款，错误的0.13元/ml已移除；第三篇无知识库依据的年龄个案已删除。
- 保留原始知识库，模型输入去掉已逐字包含在原文中的重复事实；额外确认事实仍保留。审核/修复输出按原剩余预算规划，已发送请求复用原参数。
- 一笔已知收到但截断的审稿响应限次补审；两笔明确未发送的预算预检拒绝在缩小输入后续接。原收据、原响应、调用身份、执行历史及费用全部保留；未重试未知请求。
- 192项Linux相关回归通过；此前跨日会话7项验证通过。生产19份文件实读SHA匹配部署清单，四个相关服务均active。
- 生产HTTP逐篇下载7/7通过，文件长度、SHA256、Word ZIP结构与成稿回执一致。七篇29页已渲染查看，正文无裁剪或空白页；第七篇有一处小标题跨页，按非阻断排版建议保留。
- 原每日计划已更新为新知识库和七问题，百度/文心各一轮，目标七篇；北京时间01:00采集，04:00开始写作。两渠道使用已经完成本轮采集的会话作为种子，任务日志不复制。今日旧知识库任务暂停留档。
- 累计86笔调用估算 **1.02920208元**，较此前55笔增加约0.30367664元；本次未结算预留0。单篇0.35元、每日本计划2.45元、共享日上限未提高。
- 最终文章：`outputs/brow-unattended-20261024/最终文章/`；压缩包：`七篇最终文章.zip`。
- 证据：`verification-final.json`、`deployed.json`、`activation.json`、`smoke-production.json`、`live-verification.json`。

**边界：系统已部署并启用自动运行，本次排错过程有人工工程干预。下一自然日（10月25日）完整定时采集→成稿还未实际发生，不能把本次结果等同于跨日无人干预验收。**

## 此前测试历史（已被上述上线结果更新）

'''
if '## 最新结果：已上线' not in old:p.write_text(old.replace('## 实际结果\n',update+'## 实际结果\n',1),encoding='utf8')
p=W/'outputs/brow-unattended-20261024/最终排版检查/render-verification.json';v=json.loads(p.read_text('utf8'))
v['visual_review']={'all_contact_sheets_inspected':True,'pages':29,'body_clipping_or_blank_pages':False,
 'nonblocking_layout_note':'第七篇第一页末尾的小标题与后文跨页，正文完整。'}
p.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf8')
print('Updated completion records; historical failures and raw article artifacts preserved.')
