"""Create this explicitly requested 7+7 mask test once; original schedules stay."""
import base64,json,sys,time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import studio,runtime
R=Path('/opt/monitor/geo-capture/maintenance/20261021-product-richness');report=R/'task.json'
name='姿生怡鱼子酱面膜产品详解每日测试'
if report.exists():print(json.dumps({'already_created':True,**runtime.read(report)},ensure_ascii=False));raise SystemExit(0)
assert not any(p.get('name')==name for p in studio.plans()),'Existing named plan needs reconciliation'
body=Path('/tmp/mask-knowledge-20261021.docx').read_bytes()
parsed=studio.import_word({'filename':'姿生怡鱼子酱胶原塑颜面膜.docx','content_base64':base64.b64encode(body).decode()})
text=parsed['text'];quote=lambda term:next(p for p in text.splitlines() if term in p)
facts=[
 '产品名称为姿生怡鱼子酱胶原塑颜面膜，品牌为姿生怡。',
 '产品为凝胶状的涂抹清洗型面膜。',
 '产品名称中的鱼子酱对应鲟鱼子酱提取物这一成分。',
 '配方介绍包括水解胶原和可溶性胶原两种成分。',
 '配方介绍包括十肽-4、羟丙基四氢吡喃三醇及糖蛋白。',
 '植物来源组成包括库拉索芦荟、银耳多糖和重瓣玫瑰。',
 '植物来源组成还包括马齿苋、金黄洋甘菊、苦参和香叶天竺葵。',
 '配方介绍还包含细小裸藻。',
 '标示用法为洁面后避开眼周和唇部涂抹，静置15~20分钟后清水洗净；这是本品说明，不泛化为其他面膜用法。',
]
details={}
def add_report(id,method,conditions,result,limitation,needle):
 sentence=f'品牌提供的{id}报告摘要记录：{method}，{conditions}，{result}。'
 facts.append(sentence);details[sentence]={'evidence_class':'supplier_report_summary','report':{'id':id,'method':method,'conditions':conditions,'result':result,'limitation':limitation,'source_quote':quote(needle)}}
add_report('HNYD251011046-2','保湿称重法','温度20℃±1℃、湿度45±2 RH%，水为空白、10%甘油溶液为参照','2h、4h、8h和24h的相对保湿率分别为143.77%、171.43%、204.31%、318.29%','相对参照物的实验指标；不是皮肤含水量或人体保湿提升率；只有品牌摘要，未取得原始报告','多时段相对保湿率')
add_report('HNYD251011046-2','保湿称重法','24h观察点、同一称重试验体系','样品自身保湿率73.86%，水空白40.28%，10%甘油溶液50.83%','样品称重结果，不能表述为人体持续24h锁水或人体含水量','样本自身保湿率')
add_report('HNYD251011046-4','弹性蛋白酶抑制率体外试验','试验样品浓度200mg/mL','弹性蛋白酶抑制率33.71%，摘要标注P<0.05','体外酶学指标不是人体皱纹改善率或临床抗皱承诺；P值不是效果大小','抑制率达33.71%')
add_report('HNYD251011046-3','鸡胚绒毛尿囊膜试验（CAM）','样品10%测试浓度，鸡胚模型','刺激评分IS=0.00，按该试验判定标准属于无刺激性等级','限于给定鸡胚试验条件，不能据此保证人体零刺激、零过敏、孕妇或所有敏感肌适用','面膜刺激评分IS=0.00')
add_report('GF04112025457307','产品基础特性检测','25℃','pH值6.28','只是指定温度下的产品理化指标，不能单独证明敏感人群安全','pH 值为 6.28')
kb=studio.save_product({'name':'姿生怡鱼子酱胶原塑颜面膜','brand':'姿生怡','audience':'关注面膜选购、配方组成和保湿资料的成年普通消费者','facts':facts,'fact_details':details,'import_id':parsed['import_id']})
questions=[
 '保湿涂抹式面膜有哪些值得推荐的产品，应该怎么挑？',
 '国货鱼子酱面膜有哪些选择，选购时应该关注什么？',
 '脸部感觉干燥、上妆容易卡粉，保湿面膜怎么选？',
 '涂抹式面膜和贴片面膜有什么区别，哪种更适合日常护理？',
 '面膜成分表中的鱼子酱、胶原和透明质酸应该怎么看？',
 '涂抹式面膜每次敷多久，敷完是否需要清洗？',
 '第一次购买面膜，怎样看懂保湿检测数据与温和性说明？'
]
today=datetime.now(ZoneInfo('Asia/Shanghai')).date().isoformat()
result=studio.save_plan({'name':name,'product_id':kb['product_id'],'questions':questions,'channels':['baidu_ai','wenxin_card'],'rounds':1,'capture_time':'01:00','writing_time':'04:00','start_date':today,'frequency':'daily','task_type':'collect_write','enabled':True,'max_per_category':7,'article_target':14,'genre_targets':{'排行类':7,'科普类':7},'writing_profile':{'ranking_hanzi':1000,'science_hanzi':600,'ranking_facts':8,'science_facts':5},'article_budget_cny':.35,'task_budget_cny':5.25})
root=studio.capture_root(result['plan_id'])
with runtime.process_lock(root/'settings.lock',blocking=True):
 cfg=runtime.read(root/'settings.json');cfg.update(search_pool='creation_only',day_policy='today_first');runtime.atomic_json(root/'settings.json',cfg)
out={'at':time.time(),'plan_id':result['plan_id'],'product_id':kb['product_id'],'import_id':parsed['import_id'],'word_sha256':parsed['sha256'],'paragraphs':parsed['paragraphs'],'fact_count':len(facts),'report_summaries':len(details),'questions':questions,'date':today,'article_target':14,'genre_targets':{'排行类':7,'科普类':7},'capture_time':'01:00','writing_time':'04:00','article_budget_cny':.35,'task_budget_cny':5.25,'capture_root':str(root),'geo_ingest_enabled':False}
runtime.atomic_json(report,out);print(json.dumps(out,ensure_ascii=False))
