"""Move internal verification commentary out of reader-facing articles."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'outputs/multi-product-v2-20261024'
changes = {
'00': [
('它们为进一步核对产品身份和报告提供了线索，本文未独立验证这些编号的当前状态或原件。', ''),
('摘要没有附完整测试方案、样本规模和计算基准，本文保留这两个时间点与原始数值，不据此推算个人会减少多少掉发，也不将它们描述成效果随时间持续递增。', '这两个数值对应不同观察时间点，具体使用效果因人而异。'),
('另一组关于发缝宽度和发量的数据，在资料不同位置分别关联了2周和12周，周期记载存在冲突，因此不作为本文的选购依据。与其追求一个醒目的数字，更值得关注的是报告能否解释清楚测了谁、测了多久、与什么比较。\n\n', '')],
'01': [
('它们分别对应梳理、光泽和摩擦表现，不能直接改写成“76.99%的受损头发被修好了”。这份资料没有载明三项测试的样本规模、使用周期和完整测试条件，因此这些数字只能按品牌提供的测试摘要理解，也不适合拿来与其他产品直接排高低。', '三项指标分别对应梳理、光泽和摩擦表现，可以结合自己在意的护理需求来看；它们不等于受损发丝的修复比例，实际使用感受因发质而异。'),
('本文没有这款与其他九款的统一对照测试，因此不照搬参考文章中的修护百分比，也不据此判断谁更有效。', ''),
('本文不把不同容量、不同系列或不同时期的活动价混在一起算性价比，下单时以对应店铺的实际商品为准。', '比较性价比时，先看容量和系列，下单时再确认店铺的实际活动价。')],
'02': [
('，但摘要没有载明具体测试浓度', '')],
'03': [
('这些是品牌资料中的身份信息，本文未作独立注册状态核验。', ''),
('不过，成分名称本身不能替代成品测试。比如，资料没有给出烟酰胺的添加浓度，就不应替它补上一个“高浓度”数字；出现肽类成分，也不意味着可以推定具体的淡纹幅度。', '了解配方后，还可以继续看成品的测试表现。成分组合体现产品的设计思路，具体效果则要结合整瓶产品来判断。')]
}
record = {'request': '不要有这种表述“这些是品牌资料中的身份信息，本文未作独立注册状态核验。”',
          'scope': 'Reader-facing prose only; no new verification claimed. Source limitations retained here and in original knowledge/review records.',
          'changes': []}
for prefix, pairs in changes.items():
    path = next(OUT.glob(prefix+'-*-最终文章.md'))
    text = path.read_text(encoding='utf-8')
    for before, after in pairs:
        assert text.count(before) == 1, (path.name, before)
        text = text.replace(before, after)
        record['changes'].append({'article': path.name, 'before': before, 'after': after})
    path.write_text(text, encoding='utf-8')
(OUT/'editorial-asides-revision.json').write_text(json.dumps(record, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print('Updated 4 articles; internal qualifications preserved in editorial-asides-revision.json.')
