import json,sys
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
root=runtime.job_root('creation-1793344766-1768de1c')
for p in root.rglob('auto_repair_blocked.json'):print('BLOCK',str(p.relative_to(root)),p.read_text()[:4500])
for p in (root/'queue').glob('*/ticket.json'):
 t=runtime.read(p)
 if t.get('state') in ['failed','rejected'] or t.get('error'):print('TICKET',json.dumps({k:t.get(k) for k in ['id','state','stage','location','error','meta']},ensure_ascii=False)[:2200])
