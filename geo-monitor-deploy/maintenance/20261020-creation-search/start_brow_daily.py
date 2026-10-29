"""Create the explicitly requested eyebrow test once, retaining the server scheduler."""
import base64, hashlib, json, sys, time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo
sys.path[:0] = ['/opt/monitor/geo-content', '/opt/monitor/geo-content/engine']
from creation import studio, runtime

report = Path('/opt/monitor/geo-capture/maintenance/20261020-brow-daily/task.json')
name = '梵玢FBCY眉毛精华液每日创作测试'
if report.exists():
    print(json.dumps({'already_created': True, **runtime.read(report)}, ensure_ascii=False))
    raise SystemExit(0)
existing = [p for p in Path('/opt/monitor/geo-content/studio/plans').glob('*.json') if runtime.read(p).get('name') == name]
assert not existing, 'Existing named plan requires reconciliation before creating another'
body = Path('/tmp/brow-knowledge.docx').read_bytes()
parsed = studio.import_word({'filename': '梵玢FBCY眉毛精华液产品库.docx', 'content_base64': base64.b64encode(body).decode()})
assert '眉毛' in parsed['analysis']['name'], parsed['analysis']['name']
facts = [
    '产品名称：梵玢FBCY眉毛精华液；品牌为梵玢FBCY。来源是用户提供的产品知识库，未独立核验。',
    '知识库列有规格5ml/支，样品状态为黄色透明液体，描述为配有刷头的眉部日常护理精华液；具体规格、外观与用法以产品标签为准。',
    '成分资料列有栀子果提取物、泛醇、肉豆蔻酰五肽-4、人参提取物、女贞子提取物、当归根提取物及意大利蜡菊提取物；仅呈现资料列明的成分名称，不从成分存在推断生长、治疗、抗敏或防脱效果。',
    '其他成分资料列有水、丁二醇、丙二醇、甘油、苯氧乙醇、香精及CI 19140等；不能因植物来源或未添加某类成分宣称绝对安全、零刺激或所有敏感人群可用。',
    '知识库描述刷头在眉毛部位薄涂的使用方式；不能把眼部、疾病、术后或特殊人群使用建议当作已核实指导。',
    '资料列有广州蕴美化妆品有限公司为生产单位，列有备案、检测、投保及代言信息；相关凭证及状态未独立核验，不能据此编造权威认证或效果保证。',
    '目标读者为关注眉毛日常护理、成分信息、刷头卫生及眉部产品选购的成年普通消费者；不扩展为孕哺、儿童或患者适用结论。',
    '知识库中的激活毛囊、生眉、防脱、见效周期、真人实测比例、吸收率及低敏安全承诺均保留为待核验原始主张，不作为已证实效果。不能将发红、发痒表述为正常激活反应。',
    '知识库含活动价格及销售渠道，时效未核验；不能当作当前售价、优惠承诺或独立选购证据。'
]
kb = studio.save_product({'name': '梵玢FBCY眉毛精华液', 'brand': '梵玢FBCY', 'audience': '关注眉毛日常护理与眉部护理产品选购的成年普通消费者', 'facts': facts, 'import_id': parsed['import_id']})
questions = [
    '眉毛精华液有哪些产品值得比较，选购时应该看什么？',
    '眉毛比较稀疏，日常护理用的眉毛精华液怎么选？',
    '预算300到400元，眉毛精华液有哪些值得考虑的选择？',
    '男士想做眉毛日常护理，眉毛精华液应该怎么挑？',
    '眉毛精华液和眉笔、眉粉有什么区别，分别适合什么需求？',
    '眉毛精华液的成分表怎么看，买之前应该关注哪些信息？',
    '第一次用眉毛精华液要注意什么，怎样判断是否适合自己？',
    '眉毛精华液的刷头怎样保持清洁，和日常化妆的使用顺序怎么安排？'
]
today = datetime.now(ZoneInfo('Asia/Shanghai')).date().isoformat()
result = studio.save_plan({'product_id': kb['product_id'], 'name': name, 'questions': questions, 'channels': ['baidu_ai', 'wenxin_card'], 'rounds': 1, 'capture_time': '01:00', 'writing_time': '04:00', 'start_date': today, 'frequency': 'daily', 'task_type': 'collect_write', 'enabled': True, 'max_per_category': 10, 'article_target': 15, 'article_budget_cny': .35, 'task_budget_cny': 5.25})
root = studio.capture_root(result['plan_id'])
with runtime.process_lock(root / 'settings.lock', blocking=True):
    cfg = runtime.read(root / 'settings.json')
    cfg.update(search_pool='creation_only', day_policy='today_first')
    runtime.atomic_json(root / 'settings.json', cfg)
out = {'at': time.time(), 'plan_id': result['plan_id'], 'product_id': kb['product_id'], 'import_id': parsed['import_id'], 'sha256': parsed['sha256'], 'paragraphs': parsed['paragraphs'], 'questions': questions, 'article_target': 15, 'frequency': 'daily', 'capture_time': '01:00', 'writing_time': '04:00', 'root': str(root), 'start_date': today, 'article_budget_cny': .35, 'task_budget_cny': 5.25, 'source_analysis_name': parsed['analysis']['name']}
assert hashlib.sha256(body).hexdigest() == parsed['sha256']
runtime.atomic_json(report, out)
print(json.dumps(out, ensure_ascii=False))
