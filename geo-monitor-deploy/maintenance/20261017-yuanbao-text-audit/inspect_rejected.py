import json
from pathlib import Path
import sys
sys.path.insert(0,'/app')
from monitor_core.database import connection
import save_doubao_refs as saver
root=Path('/app/geo-capture/maintenance/20261017-yuanbao-text-audit')
with connection() as conn:
 rows=conn.execute("SELECT model_id,run_id,question,day,answer,product_ai_retry_count retries,product_ai_next_retry_at retry_at FROM monitor_runs WHERE payload->>'product_extraction_method'='pending_native_text_repair' AND product_ai_retry_count>0 ORDER BY day DESC").fetchall()
result=[]
for row in rows:
 value=dict(row)
 value['numbered_blocks']=saver.numbered_product_block_count(row['answer'])
 value['headings']=saver.extract_structured_product_headings(row['answer'],row['question'])
 result.append(value)
(root/'rejected-rows.json').write_text(json.dumps(result,ensure_ascii=False,default=str,indent=2))
print(json.dumps(result,ensure_ascii=False,default=str))
errors=[]
for line in (root/'reanalysis.log').read_text().splitlines():
 try:v=json.loads(line)
 except ValueError:continue
 if v.get('usage',{}).get('rejected_items'):errors.append(v['usage'])
print(json.dumps({'rejected_batches':errors},ensure_ascii=False))
