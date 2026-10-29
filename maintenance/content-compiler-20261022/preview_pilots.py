"""Read-only original-budget affordability, using isolated compiled inputs."""
import sys,json,shutil,time
from pathlib import Path
D=Path('/opt/monitor/geo-capture/maintenance/20261022-content-compiler');S=D/'stage-v2'
sys.path[:0]=[str(S),str(S/'engine')]
from creation import runtime
from geo_source_cards.article_compiler import writer_prompt
from geo_source_cards.deepseek_api import request_payload
from geo_source_cards.api_budget import INPUT_MISS,OUTPUT
from geo_source_cards.runtime import atomic_json
rows=[]
for row in runtime.read(D/'preflight-results.json')['real_articles']:
 if row['status'] not in {'READY','READY_WITH_LIMITS'}:continue
 root=runtime.job_root(row['job']);original=root/'days/2026-10-21/jobs'/row['category']/f"{row['number']:02d}"/'writer'
 target=D/'pilot-preview'/row['job']/row['category']/f"{row['number']:02d}";target.mkdir(parents=True,exist_ok=True)
 for name in ('knowledge.json','product.json'):shutil.copy2(original/name,target/name)
 prompt=writer_prompt(target,original);budget=runtime.SharedBudget(root)
 meta={'date':'2026-10-21','category':row['category'],'number':row['number'],'consumer_rewrite':True}
 try:remaining=budget.remaining(meta,'writer')
 finally:budget.db.close()
 size=len(json.dumps(request_payload(prompt,6000)['messages'],ensure_ascii=False).encode('utf8'))+256
 writer_bound=size*INPUT_MISS/1000000+6000*OUTPUT/1000000
 rows.append({**{k:row[k] for k in ('job','category','number')},'input_byte_bound':size,'writer_reservation_upper':writer_bound,
              'remaining_original_article_budget':remaining,'affordable_writer':writer_bound<=remaining})
out={'at':time.time(),'new_paid_calls':0,'candidates':rows};atomic_json(D/'pilot-affordability.json',out)
print(json.dumps(out,ensure_ascii=False))
