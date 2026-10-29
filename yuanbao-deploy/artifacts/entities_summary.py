import json,re
from pathlib import Path
v=json.loads(Path('/home/user/redroid-yuanbao/batches/geo-yuanbao-21x5-20261015/native-getters-first.json').read_text())
for group in ['entities','question_entities']:
 rows=[]
 for e in v[group]:
  typ=e['type']['text'];active={'type':typ,'id':e['entityId']}
  if typ=='TEXT':
   t=e['textEntity']['text'];active.update(length=len(t),head=t[:1100],tail=t[-300:],options_keys=list(json.loads(e['textEntity']['options'] or '{}')) if e['textEntity']['options'].startswith('{') else None)
  if typ=='SEARCH_GUIDE':
   s=e['searchEntity'];active.update(title=s['title'],doc_count=len(json.loads(s['docsJson'])),docs_count=len(s['docs']),citations=s['citations'])
  if typ not in ['TEXT','SEARCH_GUIDE']:
   active['nonempty_scalar_paths']=[k for k,val in e.items() if isinstance(val,str) and val]
  rows.append(active)
 print(json.dumps({group:rows},ensure_ascii=True))
