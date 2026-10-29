"""Navigate one new history candidate after a pre-binding App exit; never send.

History title/time authorize read-only navigation, not answer acceptance. The
normal reader must still prove the exact question, first pair and creation time.
"""
from contextlib import closing
import json,sqlite3,time,xml.etree.ElementTree as ET
from pathlib import Path
from native_storage import app_directory,open_readonly

def history_index():
    groups=[]
    for path in app_directory().glob('files/dtmp/Users/*/Database/history_conversation.db'):
        with closing(open_readonly(path)) as db:
            cols={r['name'] for r in db.execute('pragma table_info(conversation_list)')}
            if not {'id','title','deleted_at','top_time','last_replied_at'}<=cols:raise ValueError('Native history schema changed')
            rows=[dict(r) for r in db.execute('select id,title,last_replied_at from conversation_list where coalesce(deleted_at,0)=0 order by coalesce(top_time,0) desc,last_replied_at desc,id')]
            groups.append(rows)
    return groups

def send_proof(root,task):
    if task.get('state')!='prepared' or task.get('request_id') or task.get('capture_retries',0):return None
    if any((root/(task['task_id']+'.'+suffix+'.json')).exists() for suffix in ('binding','native')):return None
    before=root/(task['task_id']+'.pre-send.json')
    if not before.exists():return None
    base=json.loads(before.read_text());created=base.get('created_at')
    if base.get('protocol')!='question-only-v1' or not isinstance(created,(int,float)) or not isinstance(base.get('conversations'),list):return None
    with closing(sqlite3.connect(root.joinpath('tasks.sqlite').as_uri()+'?mode=ro',uri=True)) as db:
        clicks=[r[0] for r in db.execute("select time from events where task_id=? and event='send_click_intent_committed'",(task['task_id'],))]
        relaunches=[r[0] for r in db.execute("select time from events where task_id=? and event='native_app_relaunch_for_readback'",(task['task_id'],))]
    if len(clicks)!=1 or not created<=clicks[0] or abs(clicks[0]-task['prepared_at'])>2:return None
    # A slow live response must never trigger history navigation. This recovery
    # is only for a recorded process exit followed by read-only App relaunch.
    if not any(at>=clicks[0] for at in relaunches):return None
    return base,clicks[0]

def candidate(groups,base,sent,claimed):
    matches=[]
    for rows in groups:
        possible=[r for r in rows if r['id'] not in set(base['conversations'])|set(claimed)
                  and isinstance(r.get('last_replied_at'),(int,float)) and sent-10<=r['last_replied_at']<=sent+120
                  and isinstance(r.get('title'),str) and r['title'].strip()]
        for row in possible:
            matches.append({'conversation_id':row['id'],'title':row['title'],'rows':rows})
    return matches[0] if len(matches)==1 else None

def recover(root,task,observed,android,close_reader,event,*,paused=False,stopping=False,index=history_index,clock=time.time,sleep=time.sleep):
    root=Path(root)
    if paused or stopping or observed.get('status')!='absent':return None
    proof=send_proof(root,task)
    if not proof:return None
    base,sent=proof;now=clock();path=root/(task['task_id']+'.unbound-history.json')
    state=json.loads(path.read_text()) if path.exists() else {}
    if now<sent+20 or now<state.get('next_at',0) or state.get('attempts',0)>=2:return None
    from unattended_worker import atomic_json
    # Persist unsuccessful probe backoff too, including across worker restarts.
    atomic_json(path,{**state,'next_at':now+60})
    ledger=root.parent.parent/'question-only-conversations.sqlite';claimed=[]
    if ledger.exists():
        with closing(sqlite3.connect(ledger.as_uri()+'?mode=ro',uri=True)) as db:
            claimed=[r[0] for r in db.execute("select cid from bindings where container='yuanbao-hpe14-android13'")]
    chosen=candidate(index(),base,sent,claimed)
    if not chosen:return {'phase':'original_history_not_visible','reason':'unbound_history_candidate_unproven','next_at':now+60}
    device=android.device
    if device.app_current().get('package')!='com.tencent.hunyuan.app.chat':return None
    nodes=list(ET.fromstring(device.dump_hierarchy()).iter('node'))
    if any(n.get('class')=='android.widget.EditText' and n.get('text','') not in ('','发消息或按住说话...') for n in nodes):return None
    if not any(n.get('text','').startswith('Hi，') or n.get('text')==task['wire_question'] for n in nodes):return None
    drawer=device(description='抽屉页入口')
    if drawer.count!=1:return None
    # Commit before touching UI. Navigation is bounded and survives restarts.
    record={'attempts':state.get('attempts',0)+1,'next_at':now+600,'candidate_conversation_id':chosen['conversation_id'],
        'candidate_title':chosen['title'],'sent_at':sent,'baseline_at':base['created_at'],
        'original_request_confirmed':False,'new_questions_sent':0,'status':'navigation_intent'}
    atomic_json(path,record);close_reader();android.tap(drawer);sleep(2)
    titles={r['title'] for r in chosen['rows'] if r['title']}
    visible=[n.get('text') for n in ET.fromstring(device.dump_hierarchy()).iter('node') if n.get('text') in titles]
    expected=[r['title'] for r in chosen['rows'][:len(visible)]]
    if len(visible)<min(3,len(chosen['rows'])) or visible!=expected or visible.count(chosen['title'])!=1:
        device.press('back');return {'phase':'original_history_not_visible','reason':'unbound_drawer_order_unproven','next_at':now+600}
    target=device(text=chosen['title'])
    if target.count!=1:device.press('back');return None
    android.tap(target);sleep(2);close_reader();atomic_json(path,{**record,'status':'opened_for_identity_check'})
    event(task['task_id'],'native_unbound_history_opened',json.dumps({'conversation_id':chosen['conversation_id'],'original_request_confirmed':False,'questions_sent':0}))
    return {'phase':'reloading_original_history','reason':'unbound_request_identity_pending','next_at':now+3}
