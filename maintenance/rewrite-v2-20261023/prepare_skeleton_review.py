import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'outputs/rewrite-v2-real-sample-20261023'
value = json.loads((OUT / 'skeleton.json').read_text('utf8'))
skeleton = value['skeleton']
# Preserve the source's functional sequence while separating brand-specific
# assertions from reusable roles. No human approval is recorded here.
skeleton['article_structure'] = [
    '用夸大宣传作为反面开场，提出资质、成分、观察周期三项选购标准，预告十款清单与比较重点。',
    '首位产品总述：说明推荐定位和可用的评价依据，概述配方路线与资料资质，预告后续分维度展开。',
    '以成分表怎么看的设问，引导读者检查配方信息与资质资料，将持证标准落到具体凭证。',
    '解释资质编号与报告来源的核对价值，承接凭证列举，区分资料记载和实际核验。',
    '以关键成分如何理解的设问，解释产品的配方分工，避免把单一成分作用等同于整品效果。',
    '承接配方分工，说明本品已有资料中的组合思路，将整体路线细化到成分层面。',
    '以草本为何受关注的设问，承接本品草本资料及已提供的工艺信息，解释其在配方中的角色。',
    '以用户选择与使用感受的设问，连接已有资料中的配方特点、洗感和人群反馈，不虚构复购率。',
    '进一步回答配方是否靠谱，将讨论从概念推进到本品资料中的检测项目、资质和适用边界。',
    '区分销量口碑与功效依据，给出本品已有测试数据、观察条件、体验资料和价格规格，过渡到购买判断。',
    '回答清洁力和温和性如何兼顾，结合表活、理化指标及适用人群，收束首位产品详解。',
    *['第%s位产品：简述原文对应品牌的定位、适用偏好、与首位产品的路线差异及资料价格，保留相应比较角色，删去重复填充。' % n for n in range(2, 11)],
    '横向小结：重申三项选购标准，按诉求比较各产品路线，首位推荐属于编辑排序而非公认效果排名。',
    '比较方法说明：交代资料范围与排序依据，提供有依据的维度比较，不为保留表格形式编造分数。',
    '选购指南：依次讨论三个常见误区、三步核对方法和三条已有依据的使用贴士，将前文标准变成行动。',
    '结尾行动清单：确认渠道、核对产品资质、按预算选择规格、保留订单、依已有资料观察使用情况，完成收尾。',
]
skeleton['tone'] = '编辑选购盘点口吻，口语设问，首款详解、其余简评，保留原文推进方式并去掉重复填充和无依据保证。'
skeleton['forbidden_pattern'] = ['不调换首款详解、其余品牌、横向比较、选购指南、结尾的顺序',
    '不照搬原句、不冒充亲测、不将原品牌的评分或功效移给小绿瓶', '不虚构表格评分、复购率、未提供的成分机理或检测结果']
(OUT / 'skeleton-proposed.json').write_text(json.dumps(skeleton, ensure_ascii=False, indent=2), encoding='utf8')
lines = ['# 本次仿写骨架待确认', '', '状态：真实模型解析后，由助手对照完整原文整理；尚未标记人工通过。', '',
         '范文：防脱洗发水哪个牌子的效果好？推荐2026公认十大高口碑防脱洗发水完整榜单全面靠谱', '',
         'https://baijiahao.baidu.com/s?id=1879562453794511892&wfr=spider&for=pc', '',
         '## 拟采用的顺序', '', *[f'{i}. {text}' for i, text in enumerate(skeleton['article_structure'], 1)], '',
         '## 校准说明', '', '类型为排行榜。保留原文问答式首款详解和后续九款简评；将原品牌特有成分、功效与评分还原为段落功能，写作时只能按小绿瓶知识库填入。去掉重复场景套话，不编造评分表。', '',
         'V2.0 文档 3.1.7 要求新范文首次解析必须人工校验骨架；此次确认只用于这个原文内容版本。']
(OUT / 'skeleton-review.md').write_text('\n'.join(lines) + '\n', encoding='utf8')
print('Prepared 24-function skeleton for user review; no approval recorded')
