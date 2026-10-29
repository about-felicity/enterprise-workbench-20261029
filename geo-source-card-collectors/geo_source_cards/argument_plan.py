"""Evidence-bound article plans shared by writers, repairers and reviewers."""
import hashlib,json,re

VERSION='argument-plan-v1'
FIELDS={'composition':r'成分|组成|配方|含有|添加',
        'net_content':r'\d+(?:\.\d+)?\s*(?:ml|毫升|克|g)\b|\d+(?:\.\d+)?\s*(?:毫升|克)',
        'price':r'\d+(?:\.\d+)?\s*元|[¥￥]\s*\d',
        'packaging':r'泵头|按压|滴管|刷头|软管|瓶装|罐装|袋装',
        'credentials':r'资质|备案|批准|国妆|报告编号|测试编号|证书|认证'}

def unavailable_identifiers(product):
    values=set()
    for fact in product.get('facts',[]):
        if fact.get('independently_verified') is True:continue
        text=fact.get('text','')
        if re.search(FIELDS['credentials'],text):values.update(re.findall(r'[A-Za-z]{0,5}\d{6,}(?:-\d+)?',text))
    return sorted(values)

def digest(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True).encode()).hexdigest()

def build(knowledge,product,source_units=None):
    from .consumer_prompts import reader_knowledge,reader_facts
    from .reference_design import clean_roster
    knowledge={**knowledge,'knowledge_units':knowledge.get('knowledge_units',[])}
    units,projected_outline,projection=reader_knowledge(knowledge,product,source_units)
    blueprint=clean_roster(knowledge.get('reference_design') or {})
    owned=product.get('name','') if knowledge.get('product_gate',{}).get('decision')!='NO_INSERT' else ''
    roster=list(dict.fromkeys(([owned] if owned else [])+[p['name'] for p in blueprint.get('products',[])]))
    ranking=blueprint.get('genre') in {'ranking','review','numbered_product_roundup'}
    facts={u['id']:{'text':u['content'],'status':u.get('verification','not_independently_verified')} for u in units}
    approved=reader_facts(product)
    facts.update({f['id']:{'text':f['text'],'status':f.get('evidence_class','supplied_product_record'),
                         **({'report':f['report']} if f.get('report') else {})} for f in approved})
    richer={u['id']:u for u in source_units or []};entries=[]
    for name in roster:
        if name==owned:ids=[f['id'] for f in approved]
        else:
            from .reference_design import roster_identity
            pos=next((i for i,p in enumerate((knowledge.get('reference_design') or {}).get('products',[]),1) if roster_identity(p['name'])==name),None)
            ids=[u['id'] for u in units if u.get('type')=='source_claim' and
                 (name in u['content'] or any(e.get('quote_id','').startswith(f'R{pos}_') for e in richer.get(u['id'],{}).get('evidence',[])))]
        def available(identifier,pattern):
            return any(re.search(pattern,c,re.I) and not re.search(r'未知|不详|未(?:提供|公开|写明|说明)|没有.{0,8}(?:资料|信息)',c)
                       for c in re.split(r'[，；;。]',facts[identifier]['text']))
        slots={key:{'state':'recorded' if any(available(i,pattern) for i in ids) else 'unknown',
                    'evidence_ids':[i for i in ids if available(i,pattern)]}
               for key,pattern in FIELDS.items()}
        entries.append({'name':name,'evidence_ids':ids,'fields':slots})
    sections=[];previous=None
    for section in projected_outline.get('sections',[]):
        topic=section['topic'];matches=[name for name in roster if re.sub(r'\s+','',name) in re.sub(r'\s+','',topic)]
        role='product' if len(matches)==1 else 'conclusion' if re.search(r'总结|收束|结尾|取舍',topic) else 'comparison' if re.search(r'横向|对照|比较',topic) else 'criteria' if re.search(r'标准|维度|依据|选购',topic) else 'explanation'
        row={'id':section['id'],'topic':topic,'role':role,'needs':[previous] if previous else [],
             'knowledge_ids':section.get('knowledge_ids',[])}
        if matches:row['product']=matches[0]
        sections.append(row);previous=section['id']
    return {'version':VERSION,'input_sha256':digest({'knowledge':knowledge,'product':product}),
            'genre':blueprint.get('genre'),'main_question':blueprint.get('primary_title',''),
            'answer_contract':'依据实际记录的差异说明有条件的选择；未知项保留未知，不产生效果冠军或未经证明的优势',
            'product_count':len(roster) if ranking else 0,'products':entries,'facts':facts,'sections':sections,
            'comparison_dimensions':[key for key in FIELDS if sum(e['fields'][key]['state']=='recorded' for e in entries)>=2],
            'unavailable_literal_identifiers':unavailable_identifiers(product),
            'unknown_policy':'unknown仅表示未提供，不能写成不含、没有、较差、已核验或与其他产品同样已知；recorded仅是资料记载，不是成品效果证明'}

def compact(plan,include_facts=False):
    result={k:v for k,v in plan.items() if k!='facts'}
    if include_facts:result['facts']=plan['facts']
    return result

def canonical_title(title,count):
    """Distinguish a total count from the additional products after 与/及."""
    def replace(match):
        prefix=match.group(1) or ''
        return prefix+str(max(0,count-1) if prefix else count)+'款'
    return re.sub(r'((?:与|及|加上)\s*)?(?:\d+|[一二三四五六七八九十]+)款',replace,title)

def title_counts_match(title,count):
    digits={c:i for i,c in enumerate('零一二三四五六七八九')}
    def number(value):
        if value.isdigit():return int(value)
        if '十' in value:
            a,b=value.split('十',1);return (digits.get(a,1)*10)+digits.get(b,0)
        return digits.get(value)
    return all(number(value)==(count-1 if prefix else count) for prefix,value in
        re.findall(r'((?:与|及|加上)\s*)?(\d+|[一二三四五六七八九十]+)款',title))

def review_view(ledger):
    """Lossless fact values/statuses with duplicate planning scaffolding removed."""
    statuses={};reports={};facts={}
    for identity,value in ledger['facts'].items():
        facts[identity]=value['text'];statuses.setdefault(value['status'],[]).append(identity)
        if value.get('report'):reports[identity]=value['report']
    return {'product_count':ledger['product_count'],'facts':facts,'evidence_status':statuses,'supplier_report_conditions':reports,
        'products':[{'name':p['name'],'known':{key:v['evidence_ids'] for key,v in p['fields'].items() if v['state']=='recorded'},
                     'unknown':[key for key,v in p['fields'].items() if v['state']=='unknown']} for p in ledger['products']],
        'unknown_policy':ledger['unknown_policy'],'unavailable_literal_identifiers':ledger.get('unavailable_literal_identifiers',[])}

WRITER_RULES='''先执行argument_plan：每节只推进其role指定的问题，承接needs中的前文，逐款部分只用本款evidence_ids。文章开头提出的问题与结尾回答保持一致，统一比较维度，不额外设定“所有维度齐全才可比较”等资料无法满足的条件。不同产品缺少某项资料时，仅该项不能比较，其他已知项目仍可比较。不得把配方不同说成产品不属于同类。
旧稿仅是待纠错文本，不是事实来源；旧稿里不在本次事实表的属性不可沿用。unavailable_literal_identifiers中的编号必须删除，不因加上‘资料记载’或‘未核实’就保留。products.fields中的unknown不补造：价格未知不能比较单位价格，只有容量不能推算使用周期；包装未知不能新增泵头；部分主打成分不证明完整成分表长短。组成、规格和包装是记录字段，不能直接推出成品效果、温和性、成本或适用人群。原始编号记录不证明资质已核验。正文只兑现有实际资料的比较维度，结尾不新增事实、标准或结论。标题总款数使用product_count；“本品与N款对照”中的N是总数减一。使用建议不计产品。'''

def issues(text,knowledge,product):
    from .article_logic import segments
    ps=segments(text);blueprint=knowledge.get('reference_design') or {};result=[]
    for paragraph in ps:
        forbidden=[value for value in unavailable_identifiers(product) if value.casefold() in re.sub(r'\s+','',paragraph['text']).casefold()]
        if forbidden:result.append({'kind':'unsupported_inference','paragraph_ids':[paragraph['id']],
            'reason':'正文保留了已排除的未核验标识：'+','.join(forbidden),'repair':'删除这些编号及由编号推出的资质、测试或报告存在结论，改用实际可用事实'})
    if not ps or blueprint.get('genre') not in {'ranking','review','numbered_product_roundup'}:return result
    from .reference_design import clean_roster
    roster=clean_roster(blueprint).get('products',[])
    owned=knowledge.get('product_gate',{}).get('decision')!='NO_INSERT'
    count=len({p['name'] for p in roster}|({product['name']} if owned and product.get('name') else set()))
    for p in ps:
        text=p['text'];wrong=False
        if p['id']==ps[0]['id']:wrong=not title_counts_match(text,count)
        # Explicit roster totals only. Capacities, steps, years and a subset
        # introduced as 其余/另外/其中 are not the full product roster.
        for m in re.finditer(r'(?:这|本次|本文|一共|共计|总共|合计)(?:[的所]?[对比介绍整理盘点选出收录涵盖测评推荐中涉及\s]{0,8})([一二三四五六七八九十百两零〇\d]+)款',text):
            token=m[1];digits={'零':0,'〇':0,'一':1,'二':2,'两':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9}
            if token.isdigit():actual=int(token)
            elif token=='十':actual=10
            elif '十' in token:
                left,right=token.split('十',1);actual=digits.get(left,1)*10+digits.get(right,0)
            else:actual=digits.get(token)
            if actual is not None and actual!=count:wrong=True
        if wrong:result.append({'kind':'contradiction','paragraph_ids':[p['id']],
             'reason':f'明确产品总数与实际{count}款清单不一致',
             'repair':'核对包含自有产品的最终名单，修正全文对应总数；子集和容量数字不改'})
    return result
