"""Transcribe direct full-text reading findings; do not approve or alter drafts."""
import json,time
from pathlib import Path
M=Path(__file__).resolve().parent;data=json.loads((M/'diagnostic-texts.json').read_text('utf-8-sig'))
P='creation-1792575159-0a8f9221';S='creation-1792576129-389f575e'
notes={
(P,'排行类',1):[
 ('unsupported_inference','200ml的包装也便于控制使用周期','只有容量而没有单次用量，不能推出使用周期可控；文章将小容量与周期判断直接相连。'),
 ('unsupported_inference','配方中的调理成分帮助维持头皮微生态平衡','这是成品作用主张，后文把它改称配方方向并不能补出成立的证据。')],
(P,'排行类',2):[
 ('unsupported_inference','这些编号说明产品走过了相应的备案与测试流程','知识库只记录未核验编号，不能由编号文本推出真实备案和测试流程已经完成。'),
 ('unsupported_inference','项目数量不至于让人眼花','缺少完整成分表时，不能由摘要的克制推出实际成分项目少、购买时阅读更容易。')],
(P,'排行类',3):[
 ('contradiction','道和小绿瓶及9款对照','正文是道和加8款共9款；标题并列表述却成为道和加9款。'),
 ('factual_mismatch','899与159','正文前面标的是89元，比较段变成899；数字错误改变价格比较。'),
 ('topic_drift','洗后的显色、持久或温和程度','洗发水正文混入无关品类的显色与持久术语；规则示例污染了当前主题。')],
(P,'排行类',4):[
 ('scope_shift','## 12. 不要频繁更换防脱洗发水','使用建议不是一款产品，标题12款及产品连续编号均被虚构条目抬高。'),
 ('unsupported_inference','属于不含大量植物提取物','只列生物素和胜肽不等于不含大量植物提取物，缺失信息被误写成排除结论。'),
 ('unsupported_inference','专利成分还能辅助舒缓头皮泛红','将未核验的成分/专利主张外推为具体作用，后面加不能推效果也不能修复该断言。')],
(P,'排行类',5):[
 ('contradiction','没有标注的，也不必当场下结论','同节又把资质设为底线并要求先排除信息不完整产品，核对与排除条件不一致。'),
 ('unsupported_inference','植物成分为核心，也意味着它的配方重心不在强清洁体系上','植物主打摘要不能证明清洁体系的配方重心。')],
(P,'排行类',6):[
 ('contradiction','道和小绿瓶与11款口碑品牌盘点','实际为道和加10款共11款；标题并列措辞多计一款。'),
 ('unsupported_inference','编号的存在说明有相应备案与报告记录','未核验编号文本不能证明备案与报告记录的实际存在。')],
(P,'排行类',7):[
 ('unsupported_inference','按两天一洗的用量估算，每毫升的实际花费才更有参考性','单位价格由价格和同单位净含量决定；频率不提供每次用量，也不参与每毫升价格计算。'),
 ('scope_shift','十款产品价格从59元到268元、容量从200ml到535ml','实际为11款且包括300克，自有产品没有可用当前价；数量、质量体积及售价覆盖范围未统一。'),
 ('contradiction','强韧方向可以留意人参、侧柏叶、生姜等植物提取物出现的频次和组合','前文不由成分出现推效果，结尾却将出现频次作为强韧诉求筛选依据，缺少支持桥梁。')],
(P,'测评类',1):[
 ('consumer_article','资料还提醒，老牌产品的配方现代化程度和成分透明度参差不齐','大量产品段评述资料和品牌方向，缺少实际同维度的具体属性比较，整体仍偏资料解读。')],
(P,'测评类',2):[
 ('scope_shift','也不能因为都写防脱就视作同类','配方组成不同不等于产品类别不同；不能互换成分的原则被错误扩大为不能作同类比较。'),
 ('unsupported_inference','御草朵的草本名单更长','两边只给部分主打成分，且列举数量没有支持更长的判断，不能比较完整名单长短。'),
 ('unsupported_inference','没有一款在所有维度上都占优','多项数据未知只能说明无法判断，不能推出没有任何一款全面占优。')],
(P,'测评类',3):[
 ('contradiction','而另一款的资料未展开这些','本段比较咖啡因产品，前面的卡诗段已明确成分、质地和250ml规格，后文却说另一款未展开。'),
 ('unsupported_inference','按摩释放描述的是使用流程中的一个动作','按摩触发活性成分释放包含机制主张，不能改称取用动作就免除证明。')],
(P,'测评类',4):[
 ('unsupported_inference','在意大容量和每毫升成本的读者会觉得200ml不占优势','后文明确道和售价未知；容量小不能推出单位价格没有优势。'),
 ('contradiction','它的配方组成、原料来源和实际使用体验在本次资料中都没有可比信息','霸王段前面刚列出三项草本组成，后文又说组成没有可比信息，结尾再将其列为具名成分可比款。')],
(P,'测评类',5):[
 ('scope_shift','## 12. 频繁更换洗发水','把使用建议列为第12款产品，混淆产品样本与购买习惯，并使标题产品数量虚增。'),
 ('order_error','## 1. 道和小绿瓶防脱洗发水\n\n为了让抽象的口径落地，可以看两组公开信息。露卡菲娅','自有产品标题之后先连续介绍其他产品，再回到自有样本，章节对象和展开顺序失配。')],
(S,'测评类',1):[
 ('contradiction','只有道和、卡伦雅芙、WMP三款同时写明了净含量与售价','道和没有售价，结尾却把它纳入可折算单位价格的三款。'),
 ('unsupported_inference','道和与卡伦雅芙为按压泵头','道和事实只给200ml瓶装，未给泵头；结尾新增了包装属性。')],
(S,'测评类',2):[
 ('contradiction','四个维度都在产品标签或资料上写得清楚，才谈得上并列','后文八款大部分维度未知仍作并列，违反自己设定的必要条件。'),
 ('answers_main_question','成分与规格两项真正可并列的只有一款','一款不能构成并列，资料不足以兑现九款成分规格横向比较。')],
}
assert len(notes)==14
rows=[]
for a in data['articles']:
 key=(a['job'],a['category'],a['number']);issues=notes[key]
 for _,quote,_ in issues:assert quote in a['text'],(key,quote)
 value={k:a[k] for k in ('job','category','number','title','flavor','text_sha256')}
 value.update(reviewer='Codex direct full-text reading',reviewed_at=time.time(),decision='needs_revision',issues=[{'kind':kind,'quote':quote,'reason':reason} for kind,quote,reason in issues],approval_certificate_issued=False)
 if key==(P,'测评类',1):value['logic_observation']='主线顺序与已知/未知边界较早稿已有改善，直接复核主要指出消费文章质量问题；不把这一项冒称为确定的逻辑矛盾。'
 rows.append(value)
(M/'direct-review-final.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'texts_read':len(rows),'revision_required':len(rows),'approval_certificates_issued':0}))
