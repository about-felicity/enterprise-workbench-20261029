"""Bounded UI history reload of the same persisted request; never sends."""
import json,time,xml.etree.ElementTree as ET
from native_storage import databases,open_readonly,history_stores
from native_core import text_entities,enum

RECOVERABLE={'native_answer_fetch_failed','native_answer_interrupted'}


def pause_blocks_readback(marker):
    # The daily controller may drain an original request before resuming work.
    # A real user pause/stop still forbids all automatic UI recovery.
    return not (marker.get('source')=='daily_tasks' and marker.get('action')=='apply'
                and marker.get('allow_original_readback') is True)


def original_pair_matches(binding,task,native):
    cid=binding['conversation_id'];message=native.get('message',{});question=native.get('question',{})
    trace=native.get('content',{}).get('traceId')
    local_failed=(str(message.get('serverId','')).startswith('local_'+cid+'_')
        and str(question.get('serverId','')).startswith('local_'+cid+'_')
        and str(message.get('serverIndex'))=='1'
        and '\n\n'.join(text_entities(native.get('entities',[])))=='回答拉取失败，正在重试'
        and native.get('render_snapshot',{}).get('h',{}).get('traceId')==trace)
    if (binding.get('task_id')!=task['task_id'] or not trace
        or (task.get('request_id') and task['request_id']!=trace)
        or message.get('serverId')!=binding['server_answer_id']
        or message.get('pairId')!=question.get('id')
        or message.get('serverPairId')!=question.get('serverId')
        or enum(question.get('speaker'))!='HUMAN' or enum(message.get('speaker'))!='AI'
        or str(question.get('serverIndex'))!='1' or (str(message.get('serverIndex'))!='2' and not local_failed)
        or message.get('contentCount')!=1
        or '\n\n'.join(text_entities(native.get('question_entities',[])))!=task['wire_question']):return False
    return True


def memory_history(binding,task,native,entries):
    """A server Session title can precede the App's persisted history rows."""
    if not original_pair_matches(binding,task,native):return None
    cid=binding['conversation_id'];trace=native['content']['traceId']
    rows={(r.get('conversation_id'),r.get('title')) for r in entries if isinstance(r,dict)}
    titles={title for key,title in rows if key==cid and isinstance(title,str) and title.strip()}
    if len(titles)!=1:return None
    title=next(iter(titles));others=[]
    if any(key!=cid and value==title for key,value in rows):return None
    for path in databases():
        with open_readonly(path) as db:
            others.extend(r[0] for r in db.execute('select title from ChatConversationDetail where conversation_id!=? and title!=""',(cid,)))
    if title in others:return None
    return {'title':title,'other_titles':sorted(set(others)),'request_id':trace,
            'conversation_id':cid,'proof_source':'native_server_session_and_original_pair'}


def restore_after_exit(root,task,android,close_reader,event,history_entries,*,paused=False,stopping=False,clock=time.time,sleep=time.sleep):
    if paused or stopping or task.get('state')!='prepared':return None
    now=clock();path=root/(task['task_id']+'.history-restore-v3.json')
    state=json.loads(path.read_text()) if path.exists() else {}
    if now<state.get('next_at',0) or state.get('attempts',0)>=3:return None
    native=json.loads((root/(task['task_id']+'.native.json')).read_text());binding=json.loads((root/(task['task_id']+'.binding.json')).read_text())
    if not original_pair_matches(binding,task,native):return None
    device=android.device
    if device.app_current().get('package')!='com.tencent.hunyuan.app.chat':return None
    nodes=list(ET.fromstring(device.dump_hierarchy()).iter('node'))
    if any(n.get('class')=='android.widget.EditText' and n.get('text','') not in ('','发消息或按住说话...') for n in nodes):return None
    if not any(n.get('text')==task['wire_question'] or n.get('text','').startswith('Hi，') for n in nodes):return None
    drawer=device(description='抽屉页入口')
    if drawer.count!=1:return None
    from unattended_worker import atomic_json
    atomic_json(path,{'attempts':state.get('attempts',0)+1,'next_at':now+60,'same_request_no_resend':True})
    close_reader();android.tap(drawer);sleep(3)
    proof=memory_history(binding,task,native,history_entries())
    if not proof:proof=stored_drawer_proof(binding,task,native,device.dump_hierarchy())
    if not proof:
        device.press('back');return {'phase':'original_history_not_visible','reason':'original_server_title_pending','next_at':now+60}
    choice=device(text=proof['title'])
    if choice.count!=1:
        device.press('back');return {'phase':'original_history_not_visible','reason':'original_title_ambiguous','next_at':now+60}
    android.tap(choice);sleep(2);close_reader()
    event(task['task_id'],'native_original_history_restored_after_exit',json.dumps({'conversation_id':proof['conversation_id'],'request_id':proof['request_id'],'questions_sent':0}))
    return {'phase':'reloading_original_history','reason':'native_history_not_loaded','next_at':now+3}


def stored_drawer_proof(binding,task,native,xml):
    if not original_pair_matches(binding,task,native):return None
    groups=history_stores(binding['conversation_id'])
    if len(groups)!=1:return None
    rows=groups[0];titles={r['title'] for r in rows if r['title']}
    visible=[n.get('text') for n in ET.fromstring(xml).iter('node') if n.get('text') in titles]
    if len(visible)<min(3,len(rows)) or visible!=[r['title'] for r in rows[:len(visible)]]:return None
    matches=[r for r in rows[:len(visible)] if r['id']==binding['conversation_id']]
    if len(matches)!=1 or visible.count(matches[0]['title'])!=1:return None
    return {'title':matches[0]['title'],'conversation_id':binding['conversation_id'],'request_id':native['content']['traceId'],
            'other_titles':[r['title'] for r in rows[:len(visible)] if r['id']!=binding['conversation_id']],
            'proof_source':'native_history_store_and_visible_order','visible_history_ids':[r['id'] for r in rows[:len(visible)]]}

def stored_history(binding,task,native):
    matches=[];trace=native.get('content',{}).get('traceId')
    for path in databases():
        with open_readonly(path) as db:
            cid=binding['conversation_id']
            messages=[dict(r) for r in db.execute('select * from ChatMessages where conversation_id=? order by message_index',(cid,))]
            if len(messages)!=2 or [r['speaker'] for r in messages]!=['human','ai']:continue
            if [r['message_index'] for r in messages]!=[1,2]:continue
            question=json.loads(messages[0]['raw_data'])
            if question.get('displayPrompt',question.get('speech'))!=task['wire_question']:continue
            contents=[dict(r) for r in db.execute('select * from ChatMessagesContecnt where conversation_id=? and message_id=?',(cid,messages[1]['message_id']))]
            if not trace or len(contents)!=1 or contents[0]['trace_id']!=trace:continue
            detail=db.execute('select title from ChatConversationDetail where conversation_id=?',(cid,)).fetchone()
            if not detail or not detail[0]:continue
            titles=[r[0] for r in db.execute('select title from ChatConversationDetail where conversation_id!=? and title!=""',(cid,))]
            matches.append({'title':detail[0],'other_titles':titles,'request_id':trace,'conversation_id':cid})
    return matches[0] if len(matches)==1 else None

def refresh_original(root,task,observed,android,close_reader,event,*,paused=False,stopping=False,history_entries=None,clock=time.time,sleep=time.sleep):
    if paused or stopping or task.get('state')!='prepared' or observed.get('reason') not in RECOVERABLE:return None
    now=clock()
    if now-(task.get('prepared_at') or now)<120:return None
    path=root/(task['task_id']+'.history-refresh.json')
    state=json.loads(path.read_text()) if path.exists() else {}
    if now<max(state.get('next_at',0),state.get('next_probe',0)) or state.get('attempts',0)>=2:return None
    from unattended_worker import atomic_json
    # Failed proof discovery also backs off across restarts; do not scan the
    # Java heap and SQLite stores every three seconds while history is absent.
    atomic_json(path,{**state,'next_probe':now+60})
    native=json.loads((root/(task['task_id']+'.native.json')).read_text())
    binding=json.loads((root/(task['task_id']+'.binding.json')).read_text())
    if '\n\n'.join(text_entities(native.get('question_entities',[])))!=task['wire_question']:return None
    if observed['reason']=='native_answer_fetch_failed' and not binding['server_answer_id'].startswith('local_'):return None
    if observed['reason']=='native_answer_interrupted':
        if (enum(native.get('message',{}).get('state'))!='INTERRUPTED'
            or enum(native.get('content',{}).get('state'))!='INTERRUPTED'
            or native.get('conversation',{}).get('isBusy')):return None
    proof=stored_history(binding,task,native)
    if not proof and observed['reason']=='native_answer_interrupted' and history_entries:
        proof=memory_history(binding,task,native,history_entries())
    if not proof and not original_pair_matches(binding,task,native):return None
    from unattended_worker import atomic_json
    device=android.device
    # A cached model is not enough: the original question must still be on
    # screen, with an empty composer. Never navigate away from someone typing.
    xml=ET.fromstring(device.dump_hierarchy())
    if any(n.get('class')=='android.widget.EditText' and n.get('text') not in ('','发消息或按住说话...') for n in xml.iter('node')):return None
    if not any(n.get('text')==task['wire_question'] for n in xml.iter('node')):
        # Failed placeholders may occupy the bottom of a long answer. Only
        # reveal the question in the current chat; never send or choose a chat.
        if observed['reason']!='native_answer_fetch_failed' or (not state.get('reveal_attempts') and not any(n.get('text')=='回答拉取失败，正在重试' for n in xml.iter('node'))):return None
        if state.get('reveal_attempts',0)>=3:return None
        if device.app_current().get('package')!='com.tencent.hunyuan.app.chat':return None
        atomic_json(path,{**state,'next_probe':now+60,'reveal_attempts':state.get('reveal_attempts',0)+1})
        width,height=device.window_size()
        device.swipe(int(width*.5),int(height*.3),int(width*.5),int(height*.72),.3);sleep(1)
        xml=ET.fromstring(device.dump_hierarchy())
        if not any(n.get('text')==task['wire_question'] for n in xml.iter('node')):return {'phase':'revealing_original_question','reason':'native_answer_fetch_failed','next_at':now+60}
        if any(n.get('class')=='android.widget.EditText' and n.get('text') not in ('','发消息或按住说话...') for n in xml.iter('node')):return None
    # Commit only after the viewport/composer guards, before any navigation.
    atomic_json(path,{'attempts':state.get('attempts',0)+1,'next_at':now+600,'proof':proof,'same_request_no_resend':True})
    close_reader()
    def tap_unique(selector):
        if selector.count!=1:raise RuntimeError('Original history navigation is ambiguous')
        android.tap(selector)
    tap_unique(device(description='抽屉页入口'));sleep(1)
    xml=ET.fromstring(device.dump_hierarchy())
    if not proof:
        proof=stored_drawer_proof(binding,task,native,ET.tostring(xml,encoding='unicode'))
        if not proof:
            device.press('back');return {'phase':'original_history_not_visible','reason':'original_history_identity_pending','next_at':now+600}
        atomic_json(path,{'attempts':state.get('attempts',0)+1,'next_at':now+600,'proof':proof,'same_request_no_resend':True})
    visible={n.get('text') for n in xml.iter('node') if n.get('text')}
    choices=sorted(set(proof['other_titles'])&visible-{proof['title']})
    if proof['title'] not in visible or not choices:device.press('back');return {'phase':'original_history_not_visible','reason':'original_history_reload_deferred','next_at':now+600}
    # Leave and reopen the original, because tapping the already-active row
    # does not reload its stale in-memory placeholder.
    tap_unique(device(text=choices[0]));sleep(1)
    tap_unique(device(description='抽屉页入口'));sleep(1)
    tap_unique(device(text=proof['title']));sleep(2)
    event(task['task_id'],'native_original_history_reloaded',json.dumps({'conversation_id':proof['conversation_id'],'request_id':proof['request_id'],'questions_sent':0}))
    return {'phase':'reloading_original_history','reason':observed['reason'],'next_at':now+3}
