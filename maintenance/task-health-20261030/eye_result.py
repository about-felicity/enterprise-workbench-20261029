import sys,json
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
root=runtime.job_root('creation-1793344766-1768de1c')
for name in ['job.json','days/2026-10-30/day.json','api/active.json','rewrite_policy.json']:
 print('FILE',name,json.dumps(runtime.read(root/name),ensure_ascii=False)[:6000])
for p in (root/'days/2026-10-30').rglob('*.json'):
 if p.name in ['day.json']:continue
 if any(x in p.name for x in ['state','result','review','stop']):print('STATE',str(p.relative_to(root)),p.read_text()[:2000])
print('ARTICLES',json.dumps(runtime.articles(root,summary=True),ensure_ascii=False)[:2000])
