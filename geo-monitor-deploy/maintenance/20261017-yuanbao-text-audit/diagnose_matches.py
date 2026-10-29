import collections
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0,'/opt/monitor')
from monitor_core.owned_products import owned_product_recommendations, owned_products_for_question
spec=importlib.util.spec_from_file_location('candidate_cleaner','/tmp/geo-native-text-candidate-1017.py')
cleaner=importlib.util.module_from_spec(spec);spec.loader.exec_module(cleaner)
root=Path('/opt/monitor/geo-capture/maintenance/20261017-yuanbao-text-audit')
rows=json.loads((root/'today-before.json').read_text())
changed=collections.Counter();eyes=[]
for row in rows:
 raw=row['answer'] or '';clean=cleaner.clean_native_text(raw)
 candidates=owned_products_for_question(row['question'])
 before=owned_product_recommendations(raw,candidates)
 after=owned_product_recommendations(clean,candidates)
 if before!=after:changed[row['model_id']]+=1
 if row['model_id']=='yuanbao' and '眉毛' in row['question']:
  eyes.append({'run_id':row['run_id'],'sequence':row['sequence_no'],'before':before,'after':after,'review':row['review']})
query="""select coalesce(json_agg(t),'[]') from (
select model_id,count(*) runs,count(distinct day) days,min(day) first_day,max(day) last_day
from monitor_runs where answer like '%@mark_underline=%' or answer like '%@replace=%'
or answer like '%@replace_goods&%' group by model_id)t"""
scope=json.loads(subprocess.check_output(['docker','exec','monitor-postgres','psql','-U','monitor_app','-d','monitor','-Atc',query],text=True,timeout=30))
report={'changed_body_matches':changed,'eyebrow':eyes,'historical_scope':scope}
(root/'diagnosis.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print(json.dumps(report,ensure_ascii=False))
