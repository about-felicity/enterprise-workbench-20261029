"""High precision local checks; semantic suspicions remain reviewable findings."""
import re
from .article_logic import segments
from .argument_plan import issues as roster_issues,build


def findings(text,knowledge,product):
    result=roster_issues(text,knowledge,product)
    ledger=build(knowledge,product);products=ledger['products']
    for paragraph in segments(text):
        value=paragraph['text']
        if re.search(r'假设|如果|例如|举例',value):continue
        for p in products:
            if p['name'] not in value:continue
            for hit in re.finditer(re.escape(p['name'])+r'.{0,12}?(?:售价|到手价|价格为|单价为)\s*[¥￥]?(\d+(?:\.\d+)?)\s*元',value):
                prices={float(v) for i in p['fields']['price']['evidence_ids'] for v in re.findall(r'(\d+(?:\.\d+)?)\s*元',ledger['facts'][i]['text'])}
                if float(hit[1]) not in prices:result.append({'kind':'unsupported_fact','paragraph_ids':[paragraph['id']],
                    'reason':'具体产品价格不在本款可写价格记录中：'+hit.group(),'repair':'删除无依据价格或按当前有效记录修正','evidence_ids':p['fields']['price']['evidence_ids']})
    return [{**v,'certainty':'confirmed','severity':'major'} for v in result]


def semantic_candidates(text):
    result=[]
    for p in segments(text):
        t=p['text']
        if (re.search(r'成分|植萃|质地|外观|配方',t) and re.search(r'相符|所以|因此|表明|说明|带来|保证',t)
            and re.search(r'功效|效果|温和|防脱|清洁|修护|保湿',t) and not re.search(r'不能|不代表|不等于|不足以|无法据此',t)):
            result.append({'kind':'unsupported_inference','paragraph_ids':[p['id']],'certainty':'needs_check','severity':'major',
                'reason':'段落将材料/外观记录与成品表现相连接，需独立核对是否存在支持因果或相符判断的材料',
                'repair':'核查原始材料；仅保留其支持的属性或用途，不由组成与外观推出表现'})
    return result
