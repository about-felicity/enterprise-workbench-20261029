import collections
import json
from pathlib import Path
import re
import subprocess
import sys

def sql(query):
 return subprocess.check_output(['docker','exec','monitor-postgres','psql','-U','monitor_app','-d','monitor','-Atc',query],text=True,timeout=45).strip()

query="""select coalesce(json_agg(t),'[]') from (
select model_id,run_id,sequence_no,question,answer,status,
payload->'products' products,payload->>'product_review_status' review,
payload->>'product_extraction_method' extraction,serial
from monitor_runs where day='2026-10-17')t"""
rows=json.loads(sql(query))
counts={}
for row in rows:
 model=row['model_id'];value=counts.setdefault(model,collections.Counter())
 value['runs']+=1;body=row['answer'] or ''
 value['mark_underline']+=bool('@mark_underline' in body)
 value['replace_tokens']+=bool(re.search(r'@replace(?:=|_)',body))
 value['unicode_replacement']+=bool('\ufffd' in body)
 value['pending_analysis']+=row['review']!='ai_verified'
directory=Path('/opt/monitor/geo-capture/maintenance/20261017-yuanbao-text-audit');directory.mkdir(parents=True,exist_ok=True)
(directory/'today-before.json').write_text(json.dumps(rows,ensure_ascii=False))
print(json.dumps({'counts':counts,'total':len(rows)},ensure_ascii=False))
selected=[r for r in rows if r['model_id']=='yuanbao' and ('眉毛' in r['question'] or r['sequence_no']==48197)]
print(json.dumps(selected[:10],ensure_ascii=False))
