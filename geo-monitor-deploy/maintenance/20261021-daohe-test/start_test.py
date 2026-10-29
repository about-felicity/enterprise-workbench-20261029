import base64,sys,json,time
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import studio,runtime
M=Path('/opt/monitor/geo-capture/maintenance/20261021-daohe-test');M.mkdir(exist_ok=True,parents=True);record=M/'task.json'
state=runtime.read(record)
if state.get('plan_id'):print(json.dumps({'already_created':True,**state},ensure_ascii=False));raise SystemExit(0)
questions=['防脱洗发水有哪些值得参考的品牌，普通消费者怎么选？','头皮容易出油又担心掉发，防脱洗发水怎么挑？','100到200元预算的防脱洗发水有哪些选择？','草本防脱洗发水横向测评应该比较哪些维度？','道和小绿瓶防脱洗发水怎么样，成分和规格有哪些特点？','防脱洗发水测评里的检测数据和真实使用感受该怎么看？','防脱洗发水和普通洗发水怎么比较，选购时要注意什么？']
facts=[
'产品名称为道和小绿瓶防脱洗发水，品牌为道和时尚。',
'产品规格为200ml/瓶，属于清洁头皮与发丝的洗发类产品。',
'成分介绍列有何首乌（POLYGONUM MULTIFLORUM）根提取物和当归（ANGELICA SINENSIS）提取物。',
'成分介绍还列有丹参（SALVIA MILTIORRHIZA）根提取物和三七（PANAX NOTOGINSENG）根提取物。',
'清洁调理成分介绍列有月桂醇聚醚硫酸酯钠和椰油酰胺丙基甜菜碱。',
'辅助成分介绍列有聚二甲基硅氧烷。',
'辅助成分介绍另列有氯化钠和香精。',
'辅助成分介绍列有苯氧乙醇及微量羟苯甲酯；微量是文档表述，未提供可核验成品浓度。',
'成分特点中标注不含酒精。',
'品牌资料记录产品pH值5.9；测试条件与原始报告未附，不能单独推断人体温和性或适用人群。',
'香气被品牌描述为草本清香，成分介绍同时列有香精；不能据此认定香气全部来自植物原料。',
'知识库列有国妆特字G20211805、人体测试编号GT00332022056002、报告编号2217461-1及YT2324850-1；相关状态、样品身份和原件未独立核验，不作为已核实资质或效果证据。',
'知识库含优惠价格、购买渠道及组合装活动，时效未核验，不作为当前售价。',
'知识库含防脱有效率、脱发计数、头发数量、控油时长、见效周期及特殊人群适用主张；原始测试方案、样本和报告未附，不作为已证实效果或医学使用指导。',
'完整INCI未提供可核验标签附件；不能由部分列出的主打成分推出真实配方精简、复杂、温和或防脱效果。']
if not state.get('import_id'):
 parsed=studio.import_word({'filename':'2.道和小绿瓶防脱洗发水知识库(1).docx','content_base64':base64.b64encode(Path('/tmp/daohe-shampoo-knowledge.docx').read_bytes()).decode()})
 state.update(import_id=parsed['import_id'],word_sha256=parsed['sha256'],paragraphs=parsed['paragraphs']);runtime.atomic_json(record,state)
if not state.get('product_id'):
 kb=studio.save_product({'name':'道和小绿瓶防脱洗发水','brand':'道和时尚','audience':'关注防脱洗发类产品选购、配方和规格资料的成年普通消费者','facts':facts,'import_id':state['import_id']})
 state.update(product_id=kb['product_id'],product_version=kb['version']);runtime.atomic_json(record,state)
now=datetime.now(ZoneInfo('Asia/Shanghai'));clock=now.strftime('%H:%M');clock='09:01' if clock=='09:00' else clock
p=studio.save_plan({'name':'道和小绿瓶 排行与测评各7篇一次测试','product_id':state['product_id'],'questions':questions,'channels':['baidu_ai','wenxin_card'],'rounds':1,'capture_time':clock,'writing_time':clock,'start_date':now.date().isoformat(),'frequency':'once','task_type':'collect_write','enabled':True,'max_per_category':7,'article_target':14,'genre_targets':{'排行类':7,'测评类':7},'writing_profile':{'ranking_hanzi':600,'science_hanzi':400,'ranking_facts':6,'science_facts':4},'article_budget_cny':.35,'task_budget_cny':5.25})
root=studio.capture_root(p['plan_id'])
with runtime.process_lock(root/'settings.lock',blocking=True):
 cfg=runtime.read(root/'settings.json');cfg.update(search_pool='creation_only',day_policy='today_first');runtime.atomic_json(root/'settings.json',cfg)
state.update(plan_id=p['plan_id'],date=now.date().isoformat(),created_at=now.isoformat(),questions=questions,article_target=14,genre_targets={'排行类':7,'测评类':7},capture_root=str(root),article_budget_cny=.35,task_budget_cny=5.25,daily_budget_cny=runtime.pipeline_control.settings(runtime.SHARED)['daily_budget_cny'],original_budget_preserved=True)
runtime.atomic_json(record,state);print(json.dumps(state,ensure_ascii=False))
