import json,sys
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation.runtime import read
root=Path('/opt/monitor/geo-content/runtime/runs/creation-1792479954-8a96bc88')
for p in (root/'queue').glob('*/ticket.json'):
 t=read(p)
 if t['state']!='needs_attention':continue
 loc=root/t['location'];writer=loc.parent/'writer' if t['stage']=='review' else loc
 draft=(writer/'draft.md').read_text() if (writer/'draft.md').exists() else ''
 kb=read(writer/'knowledge.json');bp=kb.get('reference_design',{})
 print(json.dumps({'ticket':t['id'],'stage':t['stage'],'state':t['state'],'error':t.get('error'),'meta':t['meta'],'location':t['location'],'receipt_state':read(p.parent/'receipt.json').get('state'),'title':draft.splitlines()[:1],'expected_products':len(bp.get('products',[]))+1},ensure_ascii=False))
