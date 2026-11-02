import ast,hashlib,json,os,shutil,sys,time
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
from creation.client import CreationClient
from geo_source_cards.runtime import atomic_json,process_lock
from geo_source_cards.api_worker import Worker
base=Path('/opt/monitor/geo-content')
source=base/'engine/geo_source_cards/rewrite_v2/full_writer.py'
before=source.read_text()
old="    if isinstance(answer, dict) and set(answer) == {'draft_markdown', '_note'} and isinstance(answer['_note'], str):\n        return {'draft_markdown': answer['draft_markdown']}"
new="    if isinstance(answer, dict):\n        for note in ('_note', 'draft_markdown_note'):\n            if set(answer) == {'draft_markdown', note} and isinstance(answer[note], str):\n                return {'draft_markdown': answer['draft_markdown']}"
assert old in before or new in before
after=before.replace(old,new)
tree=ast.parse(after);fn=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='normalize_answer')
space={};exec(compile(ast.Module(body=[fn],type_ignores=[]),'<test>','exec'),space)
normalize=space['normalize_answer']
for note in ['_note','draft_markdown_note']:
 x={'draft_markdown':'# Title\n\nBody',note:'memo'}
 assert normalize(x)=={'draft_markdown':x['draft_markdown']} and note in x
 for bad in [dict(x,unexpected=True),dict(x,**{note:{}})]:assert normalize(bad)==bad
work=base/'maintenance/recovery-20261102/writer';work.mkdir(parents=True,exist_ok=True)
if before!=after:
 shutil.copy2(source,work/'full_writer.py.before')
 temp=source.with_suffix('.repair.tmp');temp.write_text(after);temp.chmod(0o644);os.replace(temp,source)
print('PATCH',hashlib.sha256(source.read_bytes()).hexdigest(),flush=True)
from geo_source_cards.rewrite_v2.integration import execute
root=runtime.job_root('creation-1793573228-f5e64267');rid='f35db76158e1fd6d726b8b32'
if (work/'result.json').exists():print('ALREADY_RECOVERED');raise SystemExit
with process_lock(root/'api/worker.lock',blocking=False):
 selected=[(p,runtime.read(p)) for p in (root/'queue').glob('*/ticket.json') if runtime.read(p).get('execution',{}).get('run_id')==rid]
 assert len(selected)==1
 ticket_path,ticket=selected[0];assert ticket['state']=='needs_attention'
 active=runtime.read(root/'api/active.json');assert active.get('state')=='SUBMITTED'
 run=root/'api/runs'/rid
 assert runtime.read(run/'call/api_state.json')['state']=='RESPONDED'
 assert runtime.read(run/'call/answer.json')['finish_reason']=='stop'
 for name,expected in ticket['inputs'].items():assert hashlib.sha256((run/name).read_bytes()).hexdigest()==expected
 originals={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/'approved').rglob('*') if p.is_file()}
 shutil.copy2(ticket_path,work/'ticket-before.json');shutil.copy2(root/'api/active.json',work/'active-before.json')
 class ReplayClient(CreationClient):
  def complete(self,prompt,directory,**kwargs):
   p=Path(directory)/'response.json'
   assert p.is_file(),'New paid request prohibited'
   return runtime.read(p)
 budget=runtime.SharedBudget(root);client=ReplayClient(runtime.KEY,budget=budget)
 try:
  answer=execute(client,root,ticket,run);atomic_json(run/'answer.json',answer)
  worker=Worker(root,client);assert worker.identity==ticket['client']
  receipt=ticket_path.with_name('receipt.json');assert receipt.exists()
  receipt.rename(work/'receipt-before.json')
  ticket={**ticket,'state':'claimed'};ticket.pop('error',None);atomic_json(ticket_path,ticket)
  replay={'state':'RESPONDED','run_id':rid,'ticket':ticket['id'],'execution':ticket['execution']}
  atomic_json(root/'api/active.json',replay)
  result=worker.finish(ticket,replay)
  assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in originals.items())
  atomic_json(work/'result.json',{**result,'new_paid_requests':0,'original_articles_preserved':True})
  print('RECOVERED',json.dumps(result,ensure_ascii=False),flush=True)
 finally:client.session.close();budget.db.close()
