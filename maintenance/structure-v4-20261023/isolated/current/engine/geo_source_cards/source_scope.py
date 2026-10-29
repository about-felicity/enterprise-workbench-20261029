"""Conservative, task-derived topic checks before paying for article research."""
import re
from collections import Counter

# These are generic containers and conversational words, not product identities.
GENERIC = ('精华液','精华乳','精华水','精粹水','护肤品','化妆品','产品','成分','配方','护理','日常','男士','女士','选购','选择','推荐','哪些','怎么','什么','可以','值得','应该','注意','信息','使用','适合','自己','比较','首次','第一次','购买','挑选','挑选','保持','清洁')

def anchors(questions, product):
    name = str(product.get('name','')).replace(str(product.get('brand','')),'')
    name = ''.join(re.findall(r'[\u4e00-\u9fff]+',name))
    counts = Counter()
    for question in questions:
        parts = re.findall(r'[\u4e00-\u9fff]+',question)
        terms = {p[i:i+n] for p in parts for n in range(2,8) for i in range(len(p)-n+1)}
        counts.update(terms)
    threshold = max(1,(len(questions)+1)//2)
    terms = [s for s,n in counts.items() if n>=threshold and s in name and not any(s in g for g in GENERIC)]
    maximal=[s for s in terms if not any(s!=other and s in other for other in terms)]
    result=set(maximal)
    for term in maximal:
        core=term
        for generic in GENERIC:core=core.replace(generic,'')
        if len(core)>=2:result.add(core)
    return sorted(result,key=lambda s:(-len(s),s))

def evaluate(source, terms):
    article=source.get('article',{});title=article.get('title') or source.get('title','');body=article.get('text','')
    if not terms:return {'status':'unscoped','anchors':[],'matched':[]}
    matched=[s for s in terms if s in title or (s in body[:1000] and sum(s in p for p in body.splitlines() if p.strip())>=2)]
    return {'status':'ready' if matched else 'off_topic','anchors':terms,'matched':matched}
