"""Correlate hydrated native models without guessing from render order."""
import frida
from native_core import NativeDataError,enum,text_entities

def missing_exact_model(error):
 return isinstance(error,frida.RPCException) and str(error).split('\n')[0] in {
  'Error: Exact native message is missing','Exact native message is missing'}

def validate_candidate(task,baseline,render,raw):
 h=render.get('h',{});q=raw.get('question',{});m=raw.get('message',{});trace=raw.get('content',{}).get('traceId')
 valid=(h.get('conversationId') not in baseline['conversations']
  and render.get('v')==task['wire_question']
  and '\n\n'.join(text_entities(raw.get('question_entities',[])))==task['wire_question']
  and m.get('serverId')==h.get('msgId') and q.get('serverId')==h.get('questionServerMsgId')
  and m.get('pairId')==q.get('id') and q.get('pairId')==m.get('id')
  and m.get('serverPairId')==q.get('serverId')
  and enum(q.get('speaker'))=='HUMAN' and enum(m.get('speaker'))=='AI'
  and str(q.get('serverIndex'))=='1' and m.get('contentCount')==1
  and bool(trace) and trace==h.get('traceId')
  and (not task.get('request_id') or trace==task['request_id']))
 if not valid:raise NativeDataError('Initial native request identity is not proven')
 return True

def select_candidate(matches):
 if len(matches)==1:return matches
 # Multiple view models are acceptable only when the CID and trace agree,
 # there is exactly one real server answer, and all others are local placeholders.
 cids={k[0] for k in matches};traces={v.get('h',{}).get('traceId') for v in matches.values()}
 server={k:v for k,v in matches.items() if not k[1].startswith('local_')}
 if len(cids)==1 and len(traces)==1 and None not in traces and '' not in traces and len(server)==1:return server
 raise NativeDataError('Multiple new native conversations match the exact question')
