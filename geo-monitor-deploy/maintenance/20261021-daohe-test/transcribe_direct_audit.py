"""Record Codex's direct reading findings, bound to the exact inspected texts."""
import json,time
from pathlib import Path
M=Path(__file__).resolve().parent
drafts=json.loads((M/'drafts-for-direct-review.json').read_text('utf-8-sig'))['articles']
P='creation-1792575159-0a8f9221';S='creation-1792576129-389f575e'
findings={
 (P,'排行类',5):[
  ('contradiction','没有标注的，也不必当场下结论','同节又将资质设为底线并要求先排除信息不完整的产品，核对与排除的条件前后不一致。'),
  ('unsupported_inference','植物成分为核心，也意味着它的配方重心不在强清洁体系上','植物主打摘要不提供完整清洁体系，不能由此推出清洁配方重心。'),
  ('unsupported_inference','香味来自配方中的香精成分','已列香精只能证明存在，不能排除植物原料对气味的贡献；已批准资料明确不作单一来源推断。')],
 (P,'排行类',6):[
  ('contradiction','道和小绿瓶与11款口碑品牌盘点','正文实际为道和加10款竞品共11款；标题的并列措辞变成道和加11款。'),
  ('unsupported_inference','编号的存在说明有相应备案与报告记录','知识库只列编号，记录真实性与样品身份均未核验，不能把编号文本升级为材料实际存在。'),
  ('unsupported_inference','精简温和路线的说法，对读者的实际意义在于配方宣称的成分数量或方向较少','缺少完整INCI时不能据营销路线推出成分数量较少；随后承认无法判断精简，前后口径不稳。')],
 (P,'排行类',7):[
  ('unsupported_inference','按两天一洗的用量估算，每毫升的实际花费才更有参考性','单位价格由价格与同单位容量决定，洗头频率既不能推出每次用量，也不参与每毫升价格计算。'),
  ('scope_shift','十款产品价格从59元到268元、容量从200ml到535ml','标题及正文为11款，规格包含300克；自有产品无可用当前价。款数、g与ml及价格覆盖范围均未说明。'),
  ('contradiction','强韧方向可以留意人参、侧柏叶、生姜等植物提取物出现的频次和组合','前文称成分出现不等于效果，结尾仍将提取物出现频次作为强韧诉求的筛选依据，缺少中间证据。')],
 (S,'测评类',1):[
  ('contradiction','只有道和、卡伦雅芙、WMP三款同时写明了净含量与售价','道和段没有售价，知识库价格亦被明确排除为当前售价；结尾却把它列入可折算价格的三款。'),
  ('unsupported_inference','道和与卡伦雅芙为按压泵头','道和批准事实只有200ml瓶装，没有泵头信息；结尾新增包装属性。'),
  ('unsupported_inference','这些编号说明产品有对应的备案与检测记录','编号只存在于未核验的供应方文档，不能推出官方备案或检测记录已存在。')],
 (S,'测评类',2):[
  ('contradiction','四个维度都在产品标签或资料上写得清楚，才谈得上并列','后文八款多为未知仍作九款并列比较，与本段设定的必要条件冲突，应限定只能比较各自已知项。'),
  ('answers_main_question','成分与规格两项真正可并列的只有一款','并列至少需要两个可比对象；一款有数据不能构成标题承诺的九款成分规格横向比较，说明资料不足。'),
  ('unsupported_inference','这些编号记录了备案与检测材料的存在','批准知识只记录编号文本且说明未核验，不能据此证明备案与检测材料的实际存在。')],
}
existing=json.loads((M/'direct-review.json').read_text('utf-8')) if (M/'direct-review.json').exists() else []
index={(r['job'],r['category'],r['number']):r for r in existing}
for key,issues in findings.items():
 row=next(r for r in drafts if (r['job'],r['category'],r['number'])==key)
 for _,quote,_ in issues:assert quote in row['text'],(key,quote)
 index[key]={'job':key[0],'category':key[1],'number':key[2],'draft_sha256':row['draft_sha256'],'reviewer':'Codex direct full-text reading','at':time.time(),'decision':'needs_revision','issues':[{'kind':kind,'quote':quote,'reason':reason} for kind,quote,reason in issues]}
(M/'direct-review.json').write_text(json.dumps(list(index.values()),ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'directly_read_rejected_drafts':len(index),'no_approval_certificate_issued':True}))
