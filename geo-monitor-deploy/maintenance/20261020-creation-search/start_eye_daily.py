import base64,json,sys,time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import studio,runtime
report=Path('/opt/monitor/geo-capture/maintenance/20261020-eye-daily/task.json')
assert not report.exists(),'Already created; continue original task'
body=Path('/tmp/eye-knowledge.docx').read_bytes()
parsed=studio.import_word({'filename':'姿生怡眼霜知识库.docx','content_base64':base64.b64encode(body).decode()})
assert parsed['analysis']['name']=='姿生怡奢养铂金紧塑抗皱眼霜',parsed['analysis']['name']
facts=[
 '产品名称：姿生怡奢养铂金紧塑抗皱眼霜；品牌为姿生怡。资料来源为用户上传知识库，未独立核验。',
 '知识库列有规格15g/支，描述为眼部护理霜类产品；具体包装与信息以产品标签为准。',
 '文档列有备案编号粤G妆网备字2026022446；本次未独立核验备案或证件状态，不能据此推定功效获得认可。',
 '资料成分介绍提及乙酰基六肽-8、羟丙基四氢吡喃三醇、透明质酸钠、糖类同分异构体、水解胶原、麦角硫因、胶态铂及金；完整INCI和实际成品浓度未提供可核验附件。',
 '资料描述配有按摩头，不能从这一配置推出促进吸收、消肿、提拉或优于其他产品等结论。',
 '目标读者为关注眼周日常护理、包装、配方资料和眼霜选购的成年普通消费者。',
 '知识库含检测、专利、投保、销量、获奖及用户案例主张，均保留原文来源；不据此编造权威认证、亲测、效果概率或孕哺安全结论。',
 '不将知识库中见效时间、改善率、渗透率、临床人数或绝对安全承诺作为独立证实结论，也不从成分存在推断治疗或效果。'
]
kb=studio.save_product({'name':parsed['analysis']['name'],'brand':parsed['analysis']['brand'] or '姿生怡','audience':'关注眼周日常护理与眼霜选购的成年普通消费者','facts':facts,'import_id':parsed['import_id']})
questions=['有哪些值得推荐的保湿眼霜？','30岁左右想选抗皱眼霜，有哪些产品值得比较？','预算200元左右，眼霜怎么选，有哪些值得考虑的产品？','眼霜和面霜有什么区别，有必要单独用眼霜吗？','眼霜成分表怎么看，买眼霜前应该关注哪些信息？','眼霜太厚重、上妆容易卡粉，挑选时要注意什么？','带按摩头的眼霜和普通眼霜有什么区别，怎么选择更合适？']
today=datetime.now(ZoneInfo('Asia/Shanghai')).date().isoformat()
result=studio.save_plan({'product_id':kb['product_id'],'name':'姿生怡眼霜每日创作测试','questions':questions,'channels':['baidu_ai','wenxin_card'],'rounds':1,'capture_time':'01:00','writing_time':'04:00','start_date':today,'frequency':'daily','task_type':'collect_write','enabled':True,'max_per_category':10,'article_target':15,'article_budget_cny':.35,'task_budget_cny':5.25})
root=studio.capture_root(result['plan_id'])
with runtime.process_lock(root/'settings.lock',blocking=True):
 cfg=runtime.read(root/'settings.json');cfg.update(search_pool='creation_only',day_policy='today_first');runtime.atomic_json(root/'settings.json',cfg)
out={'at':time.time(),'plan_id':result['plan_id'],'product_id':kb['product_id'],'import_id':parsed['import_id'],'sha256':parsed['sha256'],'paragraphs':parsed['paragraphs'],'questions':questions,'article_target':15,'frequency':'daily','capture_time':'01:00','writing_time':'04:00','root':str(root),'start_date':today,'task_budget_cny':5.25}
runtime.atomic_json(report,out);print(json.dumps(out,ensure_ascii=False))
