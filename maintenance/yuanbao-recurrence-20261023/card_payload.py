import json
from pathlib import Path
D=Path('/opt/monitor/geo-capture/maintenance/20261023-yuanbao-recurrence');rows=json.loads((D/'store-cards.json').read_text());found=[]
for table in rows:
 for r in table['rows']:
  if r.get('message_id')!='0RTB4lSYXbs_2':continue
  for col in ('extra','raw_data','object_json'):
   if not r.get(col):continue
   value=json.loads(r[col]);print(table['table'],col,str(value)[:1200])
   def walk(v,path=''):
    if isinstance(v,dict):
     for k,x in v.items():
      if k=='replaces':found.append({'table':table['table'],'column':col,'path':path+'.replaces','value':x})
      walk(x,path+'.'+k)
    elif isinstance(v,list):
     for i,x in enumerate(v):walk(x,path+'['+str(i)+']')
   walk(value)
(D/'stored-replacements.json').write_text(json.dumps(found,ensure_ascii=False,indent=2));print(json.dumps(found,ensure_ascii=False)[:11000])
