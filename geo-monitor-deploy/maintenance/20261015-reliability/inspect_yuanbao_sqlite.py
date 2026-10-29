import sys,json,time
from pathlib import Path
sys.path.insert(0,'/tmp')
import yuanbao_native_storage as ns
out=Path('/opt/monitor/geo-capture/maintenance/20261015-reliability/yuanbao-ack')
result=[]
for i,path in enumerate(ns.databases()):
 with ns.open_readonly(path) as db:
  tables={t:[dict(r) for r in db.execute('pragma table_info("'+t+'")')] for t in ns.REQUIRED}
  rows=[dict(r) for r in db.execute('select rowid,* from ChatMessages where conversation_id=?',('0RGfLig07CS',))]
  contents=[dict(r) for r in db.execute('select * from ChatMessagesContecnt where conversation_id=?',('0RGfLig07CS',))]
  detail=[dict(r) for r in db.execute('select * from ChatConversationDetail where conversation_id=?',('0RGfLig07CS',))]
  item={'store':i,'path':str(path),'schema':tables,'messages':rows,'contents':contents,'detail':detail}
  (out/('sqlite-history-'+str(i)+'.json')).write_text(json.dumps(item,ensure_ascii=False,indent=2))
  raw=[]
  for r in rows:
   try:v=json.loads(r['raw_data'])
   except Exception:v={'not_json':True}
   texts=[c.get('msg','') for s in v.get('speechesV2',[]) for c in s.get('content',[]) if c.get('type')=='text']
   raw.append({'message_id':r['message_id'],'speaker':v.get('speaker'),'create_time':v.get('createTime'),'index':v.get('index'),'prompt':v.get('displayPrompt'),'body_lengths':[len(x) for x in texts],'body_starts':[x[:85] for x in texts],'request_ids':[s.get('extra',{}).get('requestId') for s in v.get('speechesV2',[])],'speech_indexes':[s.get('speechIndex') for s in v.get('speechesV2',[])],'sub_cid':v.get('subConversationId')})
  result.append({'store':i,'raw':raw,'content_keys':[list(x) for x in contents],'detail':[{k:v for k,v in r.items() if k in ('first_replied_at','last_replied_at','title','conversation_id')} for r in detail]})
print(json.dumps({'at':time.time(),'stores':result},ensure_ascii=False,default=str))
