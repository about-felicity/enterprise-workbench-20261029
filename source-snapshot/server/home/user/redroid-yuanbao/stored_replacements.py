"""Recover missing rich metadata from the exact App-owned persisted first pair.

No navigation, HTTP request, question send or App database write is performed.
The raw render snapshot stays untouched; persisted evidence is a separate field.
"""
from contextlib import closing
import copy,hashlib,json,re
from native_core import NativeDataError,enum,text_entities
from native_storage import databases,open_readonly

MARKER=re.compile(r'!\[@replace_videoBoxV2&([^\]]+)\]\(https://yuanbao\)')

def fingerprint(value):return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True).encode()).hexdigest()

def identity(task,binding,native):
 q=native.get('question',{});m=native.get('message',{});c=native.get('content',{});render=native.get('render_snapshot',{}).get('h',{})
 trace=c.get('traceId');cid=binding.get('conversation_id');answer=binding.get('server_answer_id')
 if (binding.get('task_id')!=task.get('task_id') or not cid or not answer or not trace
     or task.get('request_id') not in (None,'',trace) or enum(q.get('speaker'))!='HUMAN' or enum(m.get('speaker'))!='AI'
     or str(q.get('serverIndex'))!='1' or str(m.get('serverIndex'))!='2' or m.get('contentCount')!=1
     or m.get('serverId')!=answer or m.get('pairId')!=q.get('id') or m.get('serverPairId')!=q.get('serverId')
     or '\n\n'.join(text_entities(native.get('question_entities',[])))!=task.get('wire_question')
     or enum(m.get('state'))!='COMPLETED' or enum(c.get('state'))!='COMPLETED' or c.get('isEof') is not True or native.get('conversation',{}).get('isBusy') is not False
     or native.get('render_snapshot_final') is not True or render.get('conversationId')!=cid or render.get('msgId')!=answer
     or render.get('traceId') not in (None,'',trace) or not c.get('contentId')):
  raise NativeDataError('Persisted rich metadata lacks exact native first-pair identity')
 return {'task_id':task['task_id'],'conversation_id':cid,'answer_id':answer,'question_id':q['serverId'],'request_id':trace,'content_id':c['contentId']}

def validate_records(task,binding,native,messages,contents,entities):
 expected=identity(task,binding,native)
 if (len(messages)!=2 or [r['speaker'] for r in messages]!=['human','ai'] or [r['message_index'] for r in messages]!=[1,2]
     or [r['message_id'] for r in messages]!=[expected['question_id'],expected['answer_id']]
     or any(r['conversation_id']!=expected['conversation_id'] for r in messages)):
  raise NativeDataError('Persisted rich metadata belongs to another pair/turn')
 human,answer=[json.loads(r['raw_data']) for r in messages]
 if (human.get('displayPrompt',human.get('speech'))!=task['wire_question'] or answer.get('id')!=expected['answer_id']
     or answer.get('conversationId')!=expected['conversation_id'] or answer.get('speaker')!='ai' or answer.get('status')!=0):
  raise NativeDataError('Persisted question/answer differs from original request')
 created=messages[0].get('create_time');sent=task.get('prepared_at')
 if not isinstance(created,(int,float)) or not isinstance(sent,(int,float)) or abs(created-sent)>10:
  raise NativeDataError('Persisted first-pair creation time differs from original send')
 if len(contents)!=1:raise NativeDataError('Ambiguous persisted answer content')
 content=contents[0]
 if any(content.get(k)!=v for k,v in {'conversation_id':expected['conversation_id'],'message_id':expected['answer_id'],'content_id':expected['content_id'],'trace_id':expected['request_id']}.items()):
  raise NativeDataError('Persisted rich metadata trace/content identity changed')
 speeches=[s for s in answer.get('speechesV2',[]) if s.get('traceID')==expected['request_id']]
 if len(speeches)!=1:raise NativeDataError('Persisted original speech trace is missing or ambiguous')
 cards=json.loads(content.get('extra') or '{}').get('replaces')
 if not isinstance(cards,list) or not cards:return None
 if speeches[0].get('extra',{}).get('replaces')!=cards:raise NativeDataError('Persisted message/content replacement metadata conflicts')
 if not entities or [e['entity_index'] for e in entities]!=list(range(len(entities))):raise NativeDataError('Persisted answer entities incomplete or reordered')
 chunks=[]
 for e in entities:
  if any(e.get(k)!=v for k,v in {'conversation_id':expected['conversation_id'],'message_id':expected['answer_id'],'content_id':expected['content_id']}.items()) or e['type']!='text':raise NativeDataError('Persisted rich answer entity identity/type changed')
  value=json.loads(e['object_json'])
  if value.get('type')!='text' or not isinstance(value.get('msg'),str):raise NativeDataError('Unsupported persisted video body')
  chunks.append(value['msg'])
 persisted='\n\n'.join(chunks);native_body='\n\n'.join(text_entities(native.get('entities',[])))
 markers=MARKER.findall(native_body)
 if not markers or MARKER.sub('',native_body).strip():raise NativeDataError('Persisted video fallback cannot hide an unfinished text answer')
 ids={card.get('id') for card in cards if isinstance(card,dict)}
 if None in ids or any(not isinstance(i,str) or not i for i in ids):raise NativeDataError('Invalid persisted replacement identity')
 # Compare by original placeholders plus whitespace, not by a guessed title.
 stripped=re.sub(r'\[\]\(@replace=([^\)]+)\)','',persisted).strip()
 if stripped:raise NativeDataError('Persisted answer has extra uncollected text')
 stored_ids=re.findall(r'\[\]\(@replace=([^\)]+)\)',persisted)
 if not stored_ids or len(stored_ids)!=len(markers) or any(not (m==i or m.endswith('_'+i)) for m,i in zip(markers,stored_ids)) or set(stored_ids)!=ids:
  raise NativeDataError('Persisted video placeholders differ from the original native answer')
 proof={'version':'native-stored-replacements-v1','identity':expected,'cards':copy.deepcopy(cards),
        'records_sha256':fingerprint({'messages':messages,'contents':contents,'entities':entities})}
 proof['sha256']=fingerprint(proof);return proof

def enrich(task,binding,native,*,paths=None):
 body='\n\n'.join(text_entities(native.get('entities',[])))
 if not MARKER.search(body) or MARKER.sub('',body).strip() or native.get('render_snapshot',{}).get('i',{}).get('replacesJson'):return native
 expected=identity(task,binding,native);matches=[]
 for path in (databases() if paths is None else paths):
  with closing(open_readonly(path)) as db:
   messages=[dict(r) for r in db.execute('select * from ChatMessages where conversation_id=? order by message_index',(expected['conversation_id'],))]
   if not messages:continue
   contents=[dict(r) for r in db.execute('select * from ChatMessagesContecnt where conversation_id=? and message_id=?',(expected['conversation_id'],expected['answer_id']))]
   entities=[dict(r) for r in db.execute('select * from ChatMessageEntities where conversation_id=? and message_id=? order by entity_index',(expected['conversation_id'],expected['answer_id']))]
   proof=validate_records(task,binding,native,messages,contents,entities)
   if proof:matches.append(proof)
 if not matches:return native
 if len({v['sha256'] for v in matches})!=1:raise NativeDataError('Multiple conflicting persisted video snapshots')
 return {**native,'persisted_replacement_snapshot':matches[0]}

def cards_for(task,binding,native):
 proof=native.get('persisted_replacement_snapshot')
 if not proof:return []
 if (proof.get('version')!='native-stored-replacements-v1' or proof.get('identity')!=identity(task,binding,native)
     or proof.get('sha256')!=fingerprint({k:v for k,v in proof.items() if k!='sha256'}) or not proof.get('records_sha256')):
  raise NativeDataError('Stale or unbound persisted replacement evidence')
 return proof['cards']
