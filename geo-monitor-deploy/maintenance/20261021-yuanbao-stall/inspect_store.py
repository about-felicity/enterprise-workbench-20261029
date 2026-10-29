import json,sys
from pathlib import Path
sys.path.insert(0,'/home/user/redroid-yuanbao')
from native_storage import databases,open_readonly
cid='0RPgFhBs0yO';out=[]
for p in databases():
 with open_readonly(p) as db:
  cols=[r[1] for r in db.execute('pragma table_info(ChatMessages)')]
  rows=[dict(x) for x in db.execute('select * from ChatMessages where conversation_id=?',(cid,))]
  for row in rows:
   raw=row.pop('raw_data',None)
   try:raw=json.loads(raw)
   except (ValueError,TypeError):raw={}
   row['raw_keys']=list(raw)
   row['raw_identity']={k:v for k,v in raw.items() if k in ('id','serverId','pairId','serverPairId','serverIndex','createTime','status','state','message_id','contentCount','isLocalMessage')}
  out.append({'columns':cols,'rows':rows})
Path('/opt/monitor/geo-capture/maintenance/20261021-yuanbao-stall/store.json').write_text(json.dumps(out,ensure_ascii=False,indent=2));print(json.dumps(out,ensure_ascii=False)[:8000])
