"""Bind the product roster to evidence IDs instead of trusting model grouping."""
import copy
import re

def neutral_properties(units, blueprint):
    """Keep compound medical units as risk; recover only explicit neutral clauses."""
    from .staged_editorial import UNVERIFIED_MEDICAL
    from .reference_design import clean_roster
    products=clean_roster(blueprint).get('products',[]);derived=[]
    next_id=max([int(m.group(1)) for u in units if (m:=re.fullmatch(r'KU(\d+)',u['id']))] or [0])+1
    unsafe=re.compile(r'机制|机理|功效|疗效|治疗|疾病|激活|促进|促生|刺激|抑制|修复|改善|防脱|生长|见效|抗敏|低敏|敏感|孕|儿童|炎症|抑菌|抗菌|过敏|安全|每[日天周月]')
    neutral=re.compile(r'列[明有出]|成分|组成|配方|规格|容量|包装|刷头|滴管|质地|为核心')
    for index,product in enumerate(products,1):
        prefix=f'R{index}_';name=product['name']
        for unit in units:
            if unit.get('kind')!='source_claim' or not UNVERIFIED_MEDICAL.search(unit.get('text','')) or name not in unit.get('text',''):continue
            prefixes={re.match(r'R([1-9]\d*)_',e).group(1) for e in unit.get('evidence',[]) if re.match(r'R([1-9]\d*)_',e)}
            if prefixes!={str(index)}:continue
            clauses=re.split(r'[，；;。！？]',unit['text'])
            safe=next((s.strip() for s in clauses if name in s and neutral.search(s) and not unsafe.search(s.replace(name,''))),None)
            if safe:
                derived.append({'id':f'KU{next_id:02d}','kind':'source_claim','text':safe+'。','evidence':[e for e in unit['evidence'] if e.startswith(prefix)],'derived_from':unit['id']});next_id+=1
                break
    return derived


def captured_neutral_details(answer, blueprint, spans):
    """Recover literal neutral clauses the model missed, from the same product span."""
    if blueprint.get('genre') not in {'ranking','review'}:return answer
    from .consumer_prompts import NEUTRAL,UNVERIFIED
    result=copy.deepcopy(answer);units=result.get('units',[])
    next_id=max([int(m.group(1)) for u in units if (m:=re.fullmatch(r'KU(\d+)',u['id']))] or [0])+1
    for index,p in enumerate(blueprint.get('products',[]),1):
        name=p['name'];kept=[]
        for key,item in spans.items():
            if not key.startswith(f'R{index}_'):continue
            quote=item['quote']
            for raw in re.split(r'[\n，；;。！？]',quote):
                text=raw.strip(' •·-*：:');neutral=text.replace(name,'')
                if not 8<=len(text)<=180 or not NEUTRAL.search(neutral) or UNVERIFIED.search(neutral):continue
                if re.search(r'认证|权威|专利|通过|不含|无添加|零添加|无风险|无刺激|全肤质|未(?:写|给|提供)|暂无|不详',neutral):continue
                if text in kept or text not in quote:continue
                kept.append(text)
                units.append({'id':f'KU{next_id:02d}','kind':'source_claim','text':(text if name in text else name+'：'+text)+'。','evidence':[key],'derived_from':'captured:'+key});next_id+=1
                if len(kept)>=3:break
            if len(kept)>=3:break
    result['units']=units
    return result


def bind(answer, blueprint):
    from .reference_design import clean_roster
    blueprint=clean_roster(blueprint)
    from .product_identity import matches,name
    if blueprint.get('genre') == 'science' and 'units' in answer:
        result = copy.deepcopy(answer)
        from .staged_editorial import UNVERIFIED_MEDICAL
        for unit in result['units']:
            if unit['kind'] in {'source_claim', 'opinion'} and UNVERIFIED_MEDICAL.search(unit.get('text', '')):
                unit['kind'] = 'risk'
        usable = {u['id'] for u in result['units'] if u['kind'] in {'source_claim', 'opinion'}}
        sections = []
        for section in result['sections']:
            section['knowledge_ids'] = [k for k in section['knowledge_ids'] if k in usable]
            if section['knowledge_ids'] and not UNVERIFIED_MEDICAL.search(section['topic']):
                sections.append(section)
        if len(usable) < 4 or len(sections) < 4:
            raise ValueError('Science research needs four supported non-medical knowledge sections')
        result['sections'] = sections
        if result.get('gate', {}).get('section_id') not in {s['id'] for s in sections}:
            result['gate'] = {'decision': 'NO_INSERT', 'section_id': sections[-1]['id'], 'reason': '原插入位置缺乏可用知识证据'}
        sections = result['sections']
        branded = [s for s in sections if matches(s['topic'],blueprint)]
        if branded:
            kept = [s for s in sections if s not in branded]
            if len(kept) < 4:
                raise ValueError('Science research needs four knowledge sections before product integration')
            target = next((s for s in kept if any(w in s['topic'] for w in ('清洁','洗头','配方','洗护'))), kept[-1])
            result['sections'] = kept
            result['gate'] = {'decision':'LIGHT_MENTION','section_id':target['id'],'reason':'在相关知识段内举品牌资料例子，不另设广告章节'}
        return result
    if blueprint.get('genre') not in {'ranking','review'} or 'units' not in answer:
        return answer
    result = copy.deepcopy(answer)
    # Ranking research needs the roster and comparative opinions. Extra general
    # mechanism/statistics units are unused by this outline and can introduce
    # unsupported guidance even when the model ignored the extraction contract.
    result['units'] = [u for u in result['units'] if u['kind'] != 'source_claim'
                       or any(re.match(r'R[1-9]\d*_', e) for e in u['evidence'])]
    from .staged_editorial import UNVERIFIED_MEDICAL
    properties=neutral_properties(result['units'],blueprint)
    for unit in result['units']:
        if unit['kind'] in {'source_claim','opinion'} and UNVERIFIED_MEDICAL.search(unit.get('text','')):
            unit['kind'] = 'risk'
    result['units'].extend(properties)
    usable = [u for u in result['units'] if u['kind'] in {'source_claim', 'opinion'}]
    opinions = [u['id'] for u in usable if u['kind'] == 'opinion']
    if not opinions:
        raise ValueError('Ranking research needs an evidence-linked comparison unit')
    model_sections = result.get('sections', [])
    non_product = [s for s in model_sections if not matches(s.get('topic',''),blueprint) and not any(p['name'] in s.get('topic', '') for p in blueprint['products'])]
    opening = non_product[0]['topic'] if non_product else '选购前需要了解的问题'
    closing = non_product[-1]['topic'] if len(non_product) > 1 else '结合自己的需求作选择'
    if blueprint.get('genre')=='review':
        # These are section roles, backed by the retained comparative opinions.
        # Generic model headings must not erase the requested review contract.
        opening='统一比较维度与资料边界'
        closing='同口径对比与条件式取舍'
    sections = [{'id':'S1','topic':opening,'knowledge_ids':opinions[:2]},
                {'id':'S2','topic':name(blueprint),'knowledge_ids':opinions[:1]}]
    for index, product in enumerate(blueprint['products'], 1):
        linked = [u['id'] for u in usable if any(e.startswith(f'R{index}_') for e in u['evidence']) and u['kind']=='source_claim']
        if not linked:
            raise ValueError('Missing product-specific evidence: '+product['name'])
        sections.append({'id':f'S{len(sections)+1}', 'topic':product['name'], 'knowledge_ids':linked})
    sections.append({'id':f'S{len(sections)+1}','topic':closing,'knowledge_ids':opinions[:2]})
    result['sections'] = sections
    result['gate'] = {'decision':'LIGHT_MENTION','section_id':'S2','reason':'自有产品第一推荐位，具体事实使用独立品牌PF证据'}
    return result
