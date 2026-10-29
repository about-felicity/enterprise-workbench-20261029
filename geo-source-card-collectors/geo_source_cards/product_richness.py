"""Configurable product detail and supplier-summary evidence contracts."""
import re

def profile(value):
    if not value:return {}
    keys={'ranking_hanzi','science_hanzi','ranking_facts','science_facts'}
    if not isinstance(value,dict) or set(value)!=keys:raise ValueError('产品介绍配置字段不正确')
    for k,v in value.items():
        if type(v) is not int or not (200<=v<=2000 if k.endswith('hanzi') else 2<=v<=30):raise ValueError('产品介绍字数须200至2000，事实项须2至30')
    return dict(value)

def contract(product,ranking):
    p=profile(product.get('writing_profile'))
    if not p:return {}
    key='ranking' if ranking else 'science'
    report_count=sum(f.get('approved') is True and f.get('evidence_class')=='supplier_report_summary' for f in product.get('facts',[]))
    return {'target_hanzi':p[key+'_hanzi'],'minimum_hanzi':round(p[key+'_hanzi']*.8),'minimum_distinct_facts':p[key+'_facts'],'minimum_report_facts':min(report_count,2 if ranking else 1),
        'placement':'自有产品第一款完整独立介绍，可用三级小标题组织' if ranking else '在知识主题内自然举例，最多两个相关知识章节，不另起榜单',
        'dimensions':['定位与规格形态','配方组成的不同部分','有明确条件的品牌检测摘要','包装取用与标示用法','读者需求与选择理由'],
        'evidence_rule':'品牌检测摘要按报告号、方法、样品条件、指标与数值表达，简短归属为品牌提供；不称作者亲测，不把体外/称重/鸡胚结果换算为人体改善率。'}

def instruction(product,ranking):
    if not contract(product,ranking):return ''
    return ('\n本任务自有产品介绍以product_detail_contract为准，覆盖旧200字举例、450至650字介绍和约一成篇幅限制。'
        '围绕真实配方、规格和检测条件充分展开，每段不同信息，不反复核对标签或免责声明凑字。'
        '可引用已提供的supplier_report_summary，表述为品牌提供的报告摘要所记录的试验结果，不冒充独立验证。'
        '数据必须带指标和必要条件：相对保湿率不是皮肤含水量增幅，酶抑制率不是皱纹改善率，鸡胚评分不是人体零过敏保证。'
        '每项事实、数值用对应PF映射，达到不同事实数；来源简短归属一次，不逐句写资料/原文。')

def check(draft,product,ranking,claims,available):
    from .genre_length import hanzi
    c=contract(product,ranking)
    if not c:return [],{}
    allowed={f['id'] for f in available};ids=set();selected=[]
    for para in draft.split('\n\n'):
        if not para.strip() or para.lstrip().startswith('#'):continue
        linked={i for claim in claims if claim.get('text') and claim['text'] in para for i in claim.get('evidence_ids',[]) if i in allowed}
        if linked:ids.update(linked);selected.append(para)
    count=hanzi('\n'.join(selected));errors=[]
    if count<c['minimum_hanzi']:errors.append(f"自有产品实质介绍不足：{count}汉字，至少{c['minimum_hanzi']}（目标{c['target_hanzi']}）")
    if len(ids)<c['minimum_distinct_facts']:errors.append(f"自有产品事实覆盖不足：{len(ids)}项，至少{c['minimum_distinct_facts']}项")
    reports={f['id'] for f in available if f.get('evidence_class')=='supplier_report_summary'}
    if len(reports&ids)<c['minimum_report_facts']:errors.append('自有产品介绍使用的有条件检测摘要不足：至少'+str(c['minimum_report_facts'])+'项')
    if reports&ids and not re.search(r'品牌(?:所)?提供|品牌送检|品牌的.{0,10}(?:报告|检测)摘要',draft):errors.append('引用品牌检测摘要缺少简短来源归属')
    return errors,{'target':c,'actual_hanzi':count,'used_fact_ids':sorted(ids),'used_report_ids':sorted(reports&ids)}
