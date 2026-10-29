import collections
import json
import re
import sys
sys.path.insert(0,'/app')
from monitor_core.database import connection
from monitor_core.native_text import decode_native_text
with connection() as conn:
 rows=conn.execute("SELECT run_id,day,answer,payload->>'answer_raw' raw FROM monitor_runs WHERE model_id='yuanbao' AND payload ? 'native_text_normalization'").fetchall()
counts=collections.Counter();examples=[]
for row in rows:
 clean,report=decode_native_text(row['raw'] or row['answer'])
 if report.get('unhandled_controls'):
  snippets=re.findall(r'.{0,20}@(mark_[A-Za-z0-9_]+|replace(?:_[A-Za-z0-9_]+)?|stylelink)(?=[=?&]).{0,180}',clean)
  counts.update(snippets)
  if len(examples)<6:examples.append({'run_id':row['run_id'],'day':str(row['day']),'remaining':[clean[max(0,m.start()-20):m.end()+100] for m in re.finditer(r'@(?:mark_|replace|stylelink)',clean)][:4]})
print(json.dumps({'counts':counts,'examples':examples},ensure_ascii=False))
