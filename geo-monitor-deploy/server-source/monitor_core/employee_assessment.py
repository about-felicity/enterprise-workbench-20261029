"""Auditable employee cards: supplied traffic/expenses + live GEO observations."""
from __future__ import annotations
import calendar,json
from datetime import date,datetime
from pathlib import Path
from zoneinfo import ZoneInfo
from .performance import OCTOBER_RULES,_person_result

PEOPLE=('佳佳','杨涛','小美','鑫悦','谭露')
WEIGHTS={'traffic':50,'budget':10,'mention':30,'values':10}
COEFFICIENTS=((70,.5),(80,.8),(90,1),(95,1.5),(100,2),(105,2.5),(110,3),(115,3.5),(120,4),(float('inf'),5))

def coefficient(score):
    if score is None:return None
    return next(value for upper,value in COEFFICIENTS if score<upper)

def load_config(month):
    from .performance_store import month_config
    return month_config(month)

def _mention_summary(rows):
    """Use the exact GEO board aggregation, including raw answer denominators."""
    from .analytics import owned_product_recommendation_summary
    return owned_product_recommendation_summary(rows,['deepseek','doubao','wenxin','yuanbao'])

def snapshot(person,products,day,mention,config):
    days=[f'{day[:7]}-{d:02d}' for d in range(1,int(day[-2:])+1)]
    observed=[d for d in days if all(p['traffic'].get(d) is not None for p in products)]
    target=sum(p['daily_traffic_target'] for p in products)
    actual=sum(p['traffic'][d] for p in products for d in observed)
    traffic_score=actual/(target*len(observed))*100 if target and observed else None
    checkpoints=sorted(set.intersection(*(set(p['cumulative_expenses']) for p in products)))
    eligible=[d for d in checkpoints if d<=day]
    expense_day=eligible[-1] if eligible else None
    budget=sum(p['monthly_budget'] for p in products)
    expense=sum(p['cumulative_expenses'][expense_day] for p in products) if expense_day else None
    month_days=calendar.monthrange(int(day[:4]),int(day[5:7]))[1]
    planned=budget*int(expense_day[-2:])/month_days if expense_day else None
    raw_budget=planned/expense*100 if expense and planned is not None else None
    budget_score=max(config['budget_floor'],min(config['budget_cap'],raw_budget)) if raw_budget is not None else None
    scores={'traffic':traffic_score,'budget':budget_score,'mention':mention['score'],'values':config['values_score']}
    contribution={k:round(v*WEIGHTS[k]/100,4) if v is not None else None for k,v in scores.items()}
    total=sum(contribution.values()) if all(v is not None for v in contribution.values()) else None
    traffic_day=observed[-1] if observed else None
    partial=bool(len(observed)!=len(days) or expense_day!=day or mention['observed_items']<mention['target_items'] or not config.get('targets_confirmed',True))
    return {'date':day,'score':round(total,2) if total is not None else None,'coefficient':coefficient(total),
        'provisional':partial,'scores':{k:round(v,4) if v is not None else None for k,v in scores.items()},'contributions':contribution,
        'traffic':{'actual':actual,'target':target*len(observed),'daily_target':target,'observed_days':len(observed),'missing_days':[d for d in days if d not in observed],
                   'latest_date':traffic_day,'today_actual':sum(p['traffic'][day] for p in products) if day in observed else None},
        'budget':{'monthly':budget,'planned':round(planned,4) if planned is not None else None,'actual':expense,'latest_date':expense_day,
                  'raw_score':round(raw_budget,4) if raw_budget is not None else None,'floor':config['budget_floor'],'cap':config['budget_cap'],
                  'checkpoint_days':int(expense_day[-2:]) if expense_day else None,'month_days':month_days,'daily_expense':None},
        'mention':mention,'products':[{'product':p['product'],'priority':p['priority'],'traffic_today':p['traffic'].get(day),
          'traffic_total':sum(p['traffic'][d] for d in observed),'daily_target':p['daily_traffic_target'],'monthly_budget':p['monthly_budget'],
          'expense_total':p['cumulative_expenses'].get(expense_day) if expense_day else None,'expense_checkpoints':{d:v for d,v in p['cumulative_expenses'].items() if d<=day}}
          for p in products]}

def build_assessment(daily_rows,*,month='2026-10',as_of=None,today=None):
    from .performance_store import available_months
    config=load_config(month)
    today=today or datetime.now(ZoneInfo('Asia/Shanghai')).date()
    last=date(int(month[:4]),int(month[5:7]),calendar.monthrange(int(month[:4]),int(month[5:7]))[1])
    cutoff=date.fromisoformat(as_of) if as_of else min(today,last)
    if cutoff.strftime('%Y-%m')!=month or cutoff>today:raise ValueError('请选择考核月内、不晚于今天的截止日期')
    rows=[r for r in daily_rows if month+'-01'<=str(r.get('date',''))<=cutoff.isoformat()]
    products=config['products'];names={p['product'] for p in products}
    rows=[r for r in rows if r.get('product') in names]
    rules=[]
    for p in products:
        question=next(rule['question'] for rule in OCTOBER_RULES if rule['product']==p['product'])
        rules.append({'product':p['product'],'question':question,'article_owner':p['owner'],'targets':p['mention_targets']})
    history={name:[] for name in PEOPLE}
    for number in range(1,cutoff.day+1):
        day=f'{month}-{number:02d}'
        summarized=_mention_summary(r for r in rows if r['date']<=day)
        index={(r['question'],r['product']):r for r in summarized}
        for name in PEOPLE:
            owned=[p for p in products if p['owner']==name]
            model_weights=config.get('person_model_weights',{}).get(name,config['model_weights'])
            mention=_person_result(name,'文章负责人',model_weights,[r for r in rules if r['article_owner']==name],index,config['model_weights'],round_scores=False)
            history[name].append(snapshot(name,owned,day,mention,config))
    people=[{'name':name,'product_count':len([p for p in products if p['owner']==name]),'current':history[name][-1],'daily':list(reversed(history[name]))} for name in PEOPLE]
    return {'version':1,'month':month,'as_of':cutoff.isoformat(),'max_as_of':min(today,last).isoformat(),'generated_at':datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),
       'available_months':available_months(),
       'targets_confirmed':config.get('targets_confirmed',True),'manual_data_revision':config.get('manual_data_revision',0),
       'component_weights':WEIGHTS,'people':people,'product_count':len(products),'excluded_products':config['excluded_products'],
       'notes':config['source_notes']+['卡片与每日进展均为截至所选日的月度累计参考绩效，不是将累计费用拆成每日费用。',
          '流量按淘宝产品搜索数、多链接求和；流量分＝有效日期累计流量÷（日目标×有效天数）×100%。',
          '预算分＝（月预算×费用节点已过天数÷当月天数）÷节点累计花费×100%，限制80%～150%。',
          '提及分＝各产品实际提及率÷目标提及率（单项最高200%）；小美、谭露按DeepSeek/豆包/文心/元宝10%/40%/40%/10%，其余三人按30%/30%/30%/10%加权。',
          '文心沿用现有看板口径：文心与百度卡片均有有效数据时各占50%，无文心有效数据时不计分。',
          '缺采集数据不记为0%，有有效回答且未提及才计0%；缺失模型沿用有效权重归一化。',
          '价值观按用户确认直接计100%；完整精度计算后才显示和划分绩效系数。'],
       'reconciliation':config.get('reconciliation',[])}
