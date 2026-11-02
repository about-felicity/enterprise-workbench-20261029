"""Import the supplied tab-separated traffic and explicit expense checkpoints."""
import csv,json
from pathlib import Path
root=Path(__file__).resolve().parents[2]
source=Path('C:/Users/Administrator/.codex/attachments/0bed97b8-3f53-41d9-b1ae-837fc1f6bd51/已粘贴的文本.txt')
rows=list(csv.reader(source.open(encoding='utf-8-sig'),delimiter='\t'));header=rows[0]
people=['佳佳','杨涛','小美','鑫悦','谭露']
rules=[
 ('梵玢焕活精华液','佳佳',[10,2,20,5],3600,[1271,1532,2142,2655,3403,3740,4136]),
 ('道和小红瓶','佳佳',[30,4,55,12],3600,[0,0,0,0,0,0,0]),
 ('梵玢祛痘精华','谭露',[10,2,30,28],4500,[666,1064,1497,2174,2747,3139,3736]),
 ('梵玢染发剂（含黑茶色）','杨涛',[30,6,35,5],14000,[2433,3808,5846,7754,10691,12034,14419]),
 ('科熙本染发剂','杨涛',[10,2,15,5],10000,[0,0,0,0,0,0,0]),
 ('科熙本控油蓬松洗发水','谭露',[20,2,10,5],6000,[810,1517,1868,2484,2870,3551,4090]),
 ('科熙本控油蓬松造型喷雾','谭露',[40,2,75,30],2000,[251,492,946,1206,1511,1740,1946]),
 ('梵玢洗发水','佳佳',[10,2,10,5],4000,[1130,1911,2613,3399,4105,4474,4997]),
 ('道和小绿瓶','佳佳',[10,5,10,10],4000,[0,0,0,0,0,0,0]),
 ('姿生怡手部保湿霜','小美',[5,1,10,5],0,[52,187,344,524,844,1122,1573]),
 ('梵玢睫毛精华液','鑫悦',[20,35,95,80],5000,[716,880,1336,1805,2170,2513,3152]),
 ('姿生怡眼霜','小美',[10,2,10,5],6500,[740,971,1432,1939,2496,2932,3820]),
 ('焕颜计小白罐','小美',[30,10,70,25],9000,[552,986,1596,2255,2838,3283,3807]),
 ('梵玢眉毛精华液','鑫悦',[40,50,90,50],5000,[602,818,1102,1774,2035,2261,2636]),
 ('梵玢护发精油','杨涛',[10,2,30,5],3000,[190,190,559,761,761,914,1134]),
]
by_name={r[0]:r for r in rows[1:]}
days=[7,9,13,16,20,23,27]
products=[]
for name,owner,targets,budget,costs in rules:
 row=by_name[name]
 daily={f'2026-10-{d:02d}':int(row[header.index(f'10月{d}日')].strip()) if row[header.index(f'10月{d}日')].strip() else None for d in range(1,32)}
 products.append({'product':name,'owner':owner,'priority':row[3].strip(),'daily_traffic_target':float(row[header.index('10月目标')]),'monthly_budget':budget,'mention_targets':dict(zip(['deepseek','doubao','wenxin','yuanbao'],targets)),'traffic':daily,'cumulative_expenses':{f'2026-10-{d:02d}':v for d,v in zip(days,costs)}})
reconciliation=[]
for person in people:
 owned=[p for p in products if p['owner']==person]
 for d in range(1,31):
  calculated=sum(p['traffic'][f'2026-10-{d:02d}'] for p in owned)
  supplied=int(by_name[person][header.index(f'10月{d}日')].strip())
  if calculated!=supplied:reconciliation.append({'person':person,'date':f'2026-10-{d:02d}','product_sum':calculated,'supplied_summary':supplied})
payload={'version':1,'month':'2026-10','people':people,'component_weights':{'traffic':50,'budget':10,'mention':30,'values':10},'model_weights':{'deepseek':30,'doubao':30,'wenxin':30,'yuanbao':10},'mention_cap':200,'budget_floor':80,'budget_cap':150,'values_score':100,'values_authorization':'用户确认：直接打满','products':products,'excluded_products':[r[0] for r in rows[10:] if r[0] not in {p['product'] for p in products}],'reconciliation':reconciliation,'source_notes':['黄色标记的9个产品不纳入任何绩效分项。','产品负责人以提及率与流量表为准；小白罐归小美，护手霜归小美。','费用表按10月1—27日节点导入；原表预算列标题仍写9月，第一版按所给10月节点对应预算。','费用只提供累计节点，未拆分、推算或补造每日花费。']}
out=root/'geo-monitor-deploy/server-source/monitor_core/performance_data_202610.json'
out.write_text(json.dumps(payload,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
print(json.dumps({'products':len(products),'excluded':len(payload['excluded_products']),'traffic_reconciliation_differences':reconciliation,'people':[{'name':n,'target':sum(p['daily_traffic_target'] for p in products if p['owner']==n),'budget':sum(p['monthly_budget'] for p in products if p['owner']==n)} for n in people]},ensure_ascii=False))
