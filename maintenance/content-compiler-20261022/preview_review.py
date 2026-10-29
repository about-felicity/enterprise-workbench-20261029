import sys,json,shutil,time
from pathlib import Path
D=Path('/opt/monitor/geo-capture/maintenance/20261022-content-compiler');S=D/'stage-v2'
sys.path[:0]=[str(S),str(S/'engine')]
from creation import runtime
from geo_source_cards.api_prompts import build_prompt
from geo_source_cards.deepseek_api import request_payload
from geo_source_cards.api_budget import INPUT_MISS,OUTPUT
from geo_source_cards.runtime import atomic_json
root=runtime.job_root('creation-1792575159-0a8f9221');ticket=runtime.read(D/'pilot-review-published.json')['ticket'];job=runtime.read(root/'queue'/ticket/'ticket.json')
original=root/job['location'];preview=D/'review-payload-preview';preview.mkdir(exist_ok=True)
for name in job['inputs']:shutil.copy2(original/name,preview/name)
prompt=build_prompt(job,preview);budget=runtime.SharedBudget(root)
try:remaining=budget.remaining(job['meta'],'review')
finally:budget.db.close()
size=len(json.dumps(request_payload(prompt,1800)['messages'],ensure_ascii=False).encode('utf8'))+256
upper=size*INPUT_MISS/1000000+1800*OUTPUT/1000000
out={'at':time.time(),'new_paid_calls':0,'input_byte_bound':size,'reservation_upper':upper,'remaining':remaining,'affordable':upper<=remaining}
atomic_json(D/'review-affordability.json',out);print(json.dumps(out))
