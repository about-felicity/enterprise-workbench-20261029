import sys,json,time
from pathlib import Path
sys.path.insert(0,'/tmp')
import yuanbao_native_storage as ns
root=Path('/home/user/redroid-yuanbao/batches/geo-yuanbao-21x5-20261015')
sys.path.insert(0,'/home/user/redroid-doubao')
from unattended_core import Queue
q=Queue(root/'tasks.sqlite');task=q.next_task()
def shape(value,depth=0):
    if depth>5:return type(value).__name__
    if isinstance(value,dict):return {k:shape(v,depth+1) for k,v in value.items()}
    if isinstance(value,list):return {'length':len(value),'first':shape(value[0],depth+1) if value else None}
    return type(value).__name__
for index,path in enumerate(ns.databases()):
    with ns.open_readonly(path) as db:
        rows=[dict(r) for r in db.execute('select * from ChatMessages')]
        if not rows:continue
        # This isolated new store was empty before the controlled first send.
        value={t:[dict(r) for r in db.execute('select * from '+t)] for t in [*ns.REQUIRED,'ChatConversations']}
        out=root/'native-snapshot-first.json';out.write_text(json.dumps(value,ensure_ascii=False));out.chmod(0o600)
        summary=[]
        for row in rows:
            raw=json.loads(row['raw_data']) if row['raw_data'] else None
            summary.append({'speaker':row['speaker'],'status':row['status'],'message_index':row['message_index'],'raw_shape':shape(raw)})
        print(json.dumps({'store':index,'messages':summary,'entity_types':[(r['type'],shape(json.loads(r['object_json']))) for r in value['ChatMessageEntities']],'detail_flags':[{k:r[k] for k in ['end_conv','stop_generating','first_replied_at','last_replied_at']} for r in value['ChatConversationDetail']]}))
