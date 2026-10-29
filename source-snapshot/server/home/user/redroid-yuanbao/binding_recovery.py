"""Accept only an App-local placeholder becoming the same server answer."""
from native_core import NativeDataError,text_entities

def promote(binding,task,previous,current,render):
    old=previous.get('message',{});new=current.get('message',{})
    oq=previous.get('question',{});nq=current.get('question',{})
    trace=previous.get('content',{}).get('traceId')
    h=render.get('h',{})
    valid=(binding.get('task_id')==task['task_id']
        and old.get('serverId')==binding.get('server_answer_id')
        and str(old.get('serverId','')).startswith('local_')
        and bool(new.get('serverId')) and not new['serverId'].startswith('local_')
        and bool(old.get('id')) and old['id']==new.get('id')
        and bool(oq.get('id')) and oq['id']==nq.get('id')==new.get('pairId')
        and new.get('serverPairId')==nq.get('serverId')
        and str(nq.get('serverIndex'))=='1' and str(new.get('serverIndex'))=='2'
        and str(new.get('contentCount'))=='1'
        and trace and trace==current.get('content',{}).get('traceId')==h.get('traceId')
        and render.get('v')==task['wire_question']
        and '\n\n'.join(text_entities(current.get('question_entities',[])))==task['wire_question']
        and h.get('conversationId')==binding.get('conversation_id')
        and h.get('msgId')==new.get('serverId')
        and h.get('questionServerMsgId')==nq.get('serverId'))
    if not valid:raise NativeDataError('Local-to-server answer identity is not proven')
    return {**binding,'server_answer_id':new['serverId'],
        'native_request_id':trace,'native_message_id':new['id'],'native_question_id':nq['id'],
        'local_placeholder_answer_id':old['serverId']}
