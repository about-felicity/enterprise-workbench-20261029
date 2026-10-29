import json,sys
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
from geo_source_cards.genre_prompts import quote_chunks
root=runtime.job_root('creation-1792479954-8a96bc88');active=runtime.read(root/'api/active.json');t=runtime.read(root/'queue'/active['ticket']/'ticket.json');p=root/t['location'];v=runtime.read(p/'research_input.json')
source=next(s for row in v['observations'] for s in row['sources'] if s['url']==v['reference_design']['primary_url'])
for product in v['reference_design']['products']:
 print(json.dumps({'name':product['name'],'excerpt':product['excerpt'],'length':len(product['excerpt']),'quote_count':len(list(quote_chunks(product['excerpt'],source['article']['text'])))},ensure_ascii=False))
print(json.dumps({'active':active,'meta':t['meta'],'call_files':[x.name for x in (root/'api/runs'/active['run_id']/'call').glob('*')]},ensure_ascii=False))
