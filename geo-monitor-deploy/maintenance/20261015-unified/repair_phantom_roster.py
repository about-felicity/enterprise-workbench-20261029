"""One known delivered schema failure after a verified parser fix; preserve inputs."""
import json
from pathlib import Path
import sys
import time
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
from geo_source_cards.daily_editorial import repair_research
from geo_source_cards.reference_design import product_blocks,VERSION
root=runtime.job_root('creation-1792060761-3c2baae0')
assert runtime.pipeline_control.state(root).get('paused')
ticket=runtime.read(root/'queue/81fa80180b782980a738fd05/ticket.json')
assert ticket['state']=='needs_attention' and '• 二硫化硒洗发水' in ticket['error']
receipt=runtime.read(root/'queue'/ticket['id']/'receipt.json')
assert receipt.get('state') in {'failed','completed'}
value=runtime.read(root/ticket['location']/'research_input.json');blueprint=value['reference_design']
primary=next(s for r in value['observations'] for s in r['sources'] if s['url']==blueprint['primary_url'])
products=product_blocks(primary['article'])
assert len(products)==5 and not any(p['name'].startswith('•') for p in products)
assert '水杨酸' in products[0]['excerpt']
reason='已定位并修复本地解析器：功能说明bullet被误识为独立产品，截断LBR对应素材。按v3重新提取同一批次同一完整原文的5个真实品牌标题，保留source_contract哈希及全部质量/预算门槛；不是补造缺失证据。仅此已回执schema失败执行一次操作修复。'
result=repair_research(root,ticket,reason)
proof={'at':time.time(),'parser_version':VERSION,'old_products':[p['name'] for p in blueprint['products']],
       'new_products':[p['name'] for p in products],'source_contract':blueprint['source_contract'],'result':result}
runtime.atomic_json(root/'roster_parser_fix.json',proof)
runtime.resume(root)
print(json.dumps({'repaired':result,'version':VERSION},ensure_ascii=False))
