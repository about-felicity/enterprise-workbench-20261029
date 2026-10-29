import sys,json
from pathlib import Path
sys.path.insert(0,'/tmp')
from yuanbao_native_core import parse_result
sys.path.insert(0,'/home/user/redroid-doubao')
from unattended_core import Queue
from unattended_worker import atomic_json
root=Path('/home/user/redroid-yuanbao/batches/geo-yuanbao-21x5-20261015');queue=Queue(root/'tasks.sqlite');task=queue.next_task()
metadata=json.loads((root/'native-model-first.json').read_text())
context=next(r['value']['h'] for r in metadata if r['kind']=='markdown' and r['value']['h'].get('conversationId'))
binding={'conversation_id':context['conversationId'],'server_answer_id':context['msgId']}
native=json.loads((root/'native-getters-first.json').read_text())
print(json.dumps({'question_speaker':native['question']['speaker']}))
result=parse_result(task,binding,native)
if result['status']!='complete':raise RuntimeError('Not complete')
atomic_json(root/(task['task_id']+'.binding.json'),binding)
queue.complete(task['task_id'],result)
print(json.dumps({'completed':queue.summary(),'body_length':len(result['body_markdown']),'sources':len(result['sources']),'citations':len(result['citations'])}))
