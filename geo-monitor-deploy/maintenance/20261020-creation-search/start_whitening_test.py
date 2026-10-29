"""Import the user's Word through studio APIs and start one bounded end-to-end test."""
import base64,json,sys,time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import studio,runtime
report=Path('/opt/monitor/geo-capture/maintenance/20261020-creation-search/whitening-test.json')
assert not report.exists(),'Test already created; continue original plan'
body=Path('/tmp/creation-whitening-test.docx').read_bytes()
imported=studio.import_word({'filename':'美白知识库新的.docx','content_base64':base64.b64encode(body).decode()})
text=imported['text'];assert text.splitlines()[0]=='焕颜计小白罐美白精华霜'
facts=[
 '产品名称：焕颜计小白罐美白精华霜。产品信息来自用户上传知识库，未进行独立核验。',
 '知识库将该产品描述为面部精华霜，规格50克；资料提供了烟酰胺、燕麦提取物、苦参根提取物、粉防己提取物等成分信息，未提供完整INCI及成分浓度。',
 '资料列有特殊化妆品注册证号国妆特字202411819。文档同时注明注册证不作为对产品所称功效的认可；本次未独立核验证号和证件状态。',
 '资料建议早晚洁面爽肤后使用，日间搭配防晒。首次使用应先局部试用；具体用法以产品标签为准。',
 '目标读者为关注肤色暗沉、肤色不均及面霜选择的成年普通消费者。',
 '不将资料中的首选、全肤质安心、254%提升、用户案例或短期改善承诺视为已独立证实的事实，不编造亲测、销量、排名、价格对比或用户评价。',
 '文档报告和成分材料不能推导为人人有效、对疾病的治疗结论，不能用专利存在推导本产品功效已获权威认可。'
]
kb=studio.save_product({'name':'焕颜计小白罐美白精华霜','brand':'焕颜计','audience':'关注肤色暗沉、肤色不均及美白面霜选择的成年普通消费者','facts':facts,'import_id':imported['import_id']})
now=datetime.now(ZoneInfo('Asia/Shanghai'));day=now.date().isoformat();start=now.strftime('%H:%M')
result=studio.save_plan({'product_id':kb['product_id'],'name':'焕颜计美白面霜全流程测试','questions':['美白淡斑面霜有哪些值得推荐的？','皮肤暗沉、肤色不均，应该怎么选美白面霜？'],'channels':['baidu_ai','wenxin_card'],'rounds':1,'capture_time':start,'writing_time':start,'start_date':day,'frequency':'once','task_type':'collect_write','enabled':True,'max_per_category':1,'article_budget_cny':.35,'task_budget_cny':2})
root=studio.capture_root(result['plan_id'])
with runtime.process_lock(root/'settings.lock',blocking=True):
 cfg=runtime.read(root/'settings.json');cfg['search_pool']='creation_only';runtime.atomic_json(root/'settings.json',cfg)
out={'at':time.time(),'plan_id':result['plan_id'],'product_id':kb['product_id'],'import_id':imported['import_id'],'document_sha256':imported['sha256'],'original_extracted_name':imported['analysis']['name'],'confirmed_name':'焕颜计小白罐美白精华霜','paragraphs':imported['paragraphs'],'root':str(root),'date':day,'task_budget_cny':2,'max_articles':4,'frequency':'once'}
runtime.atomic_json(report,out);print(json.dumps(out,ensure_ascii=False))
