"""Read-only native task and event diagnostic without configuration secrets."""
import json, sqlite3, time, sys
from pathlib import Path
base=Path('/opt/monitor/geo-capture')
p=json.loads((base/'soak12h_current.json').read_text())
m=json.loads((Path(p['root'])/'manifest.json').read_text())
root=Path('/home/user/redroid-doubao/batches')/m['jobs']['doubao1']['batch']
with sqlite3.connect((root/'tasks.sqlite').as_uri()+'?mode=ro',uri=True) as db:
    db.row_factory=sqlite3.Row
    task=db.execute("select task_id,ordinal,question,state,attempts,prepared_at,request_id,error from tasks where state='needs_attention' order by ordinal limit 1").fetchone()
    if not task:print(json.dumps({'attention':False}));raise SystemExit(0)
    task=dict(task)
    events=[dict(x) for x in db.execute('select * from events where task_id=? order by time',(task['task_id'],))]
    files=[{'name':x.name,'size':x.stat().st_size} for x in root.glob(task['task_id']+'*')]
    result={'at':time.time(),'batch':root.name,'root':str(root),'task':task,'events':events,'files':files}
    sys.path.insert(0,'/home/user/redroid-doubao/geo-batch-code')
    from question_only_core import message_text
    snapshot=json.loads((root/(task['task_id']+'-attempt-0.pre-send.json')).read_text())
    result['baseline_created_at']=snapshot['created_at'];result['candidates']=[]
    for index,item in enumerate(snapshot['databases']):
        with sqlite3.connect(Path(item['database']).as_uri()+'?mode=ro',uri=True) as native:
            native.row_factory=sqlite3.Row
            for row in native.execute('select rowid,* from im_message where rowid>? and user_type=1 order by rowid',(item['max_rowid'],)):
                if message_text(row)!=task['question']:continue
                cid=row['conversation_id']
                selected={k:row[k] for k in row.keys() if k in ('rowid','local_message_id','conversation_id','local_index','message_id','server_index') or any(x in k.lower() for x in ('time','status'))}
                selected.update(database_index=index,baseline_max_rowid=item['max_rowid'],cid_in_baseline=cid in item['conversations'],user_turns=native.execute('select count(*) from im_message where conversation_id=? and user_type=1',(cid,)).fetchone()[0])
                selected['prior_completed_tasks']=[{'task_id':x['task_id'],'ordinal':x['ordinal'],'same_question':json.loads(x['result_json']).get('wire_question')==task['question'],'same_cid':json.loads(x['result_json']).get('conversation_id')==cid,'same_question_blocks':json.loads(x['result_json']).get('raw_question_blocks')==json.loads(row['content'])} for x in db.execute("select task_id,ordinal,result_json from tasks where state='completed' and json_extract(result_json,'$.question_id')=?",(row['local_message_id'],))]
                result['candidates'].append(selected)
    target=base/'maintenance/20261015-reliability/doubao1-attention-diagnostic.json'
    target.write_text(json.dumps(result,ensure_ascii=False,indent=2))
    print(json.dumps(result,ensure_ascii=False))
