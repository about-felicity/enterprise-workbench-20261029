import json
from pathlib import Path
import subprocess

def sql(query):
 return subprocess.check_output(['docker','exec','monitor-postgres','psql','-U','monitor_app','-d','monitor','-Atc',query],text=True,timeout=20).strip()
root=Path('/home/user/redroid-deepseek-account2/batches/geo-panel-deepseek2-20261017-134730-bf1a1e9e')
receipt=json.loads(next((root/'receipts').glob('*.json')).read_text())
rid=receipt['stored_run_id'];assert rid.isalnum()
row=json.loads(sql("select row_to_json(r) from monitor_runs r where run_id='"+rid+"' limit 1"))
payload=row.get('payload') or {}
def summary(value):
 if isinstance(value,list):return {'count':len(value),'item_keys':list(value[0]) if value and isinstance(value[0],dict) else []}
 if isinstance(value,dict):return {'keys':list(value)}
 return value
out={'stored_run_id':rid,'run':{k:v for k,v in row.items() if k not in {'payload','answer'}},
     'payload_analysis':{k:summary(v) for k,v in payload.items() if any(x in k for x in ['analysis','product','brand','status','quarant'])},
     'payload_keys':list(payload)}
out['stored_sources']=int(sql("select count(*) from monitor_sources where model_id='deepseek' and run_id='"+rid+"'"))
out['stored_products']=int(sql("select count(*) from monitor_products where model_id='deepseek' and run_id='"+rid+"'"))
print(json.dumps(out,ensure_ascii=False))
print(sql("select table_name from information_schema.tables where table_schema='public' and table_name like 'monitor_%' order by table_name"))
