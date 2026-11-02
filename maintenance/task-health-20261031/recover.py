import hashlib,json,shutil,sys,time
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime,studio,materials
from creation.client import CreationClient,recover_transport_json
from geo_source_cards.runtime import atomic_json,process_lock
from geo_source_cards.api_worker import Worker
from geo_source_cards.rewrite_v2.integration import execute

audit=Path('/opt/monitor/geo-content/maintenance/recovery-20261031');audit.mkdir(parents=True,exist_ok=True)
pid='plan-4c988f3863344f52aff3aa2b1f96beb2';day='2026-10-31'
path=studio.day_path(pid,day)
with process_lock(path.with_suffix('.lock'),blocking=True):
 task=runtime.read(path)
 if task.get('error','').startswith('建立创作任务需要处理：Unterminated string'):
  p=task['plan'];counts=[len(materials.records(day,q,p['channels'],studio.capture_root(pid))) for q in p['questions']]
  assert all(counts),counts
  backup=audit/'spray-day-before.json';assert not backup.exists(),'Already recovered spray task'
  shutil.copy2(path,backup)
  task.pop('error',None);task['status']='waiting_writing';atomic_json(path,task)
  print('SPRAY_UNBLOCKED',counts,flush=True)

for jid,rid in [('creation-1793400211-f3855aab','e6154840a210bc391de15473'),('creation-1793397144-33d4e53e','c06ff7ed0ce26c6097e4fb97')]:
 root=runtime.job_root(jid);record=audit/jid
 if (record/'result.json').exists():print('ALREADY_RECOVERED',jid,flush=True);continue
 with process_lock(root/'api/worker.lock',blocking=False):
  tickets=[(p,runtime.read(p)) for p in (root/'queue').glob('*/ticket.json')]
  selected=[(p,t) for p,t in tickets if t.get('execution',{}).get('run_id')==rid]
  assert len(selected)==1
  ticket_path,ticket=selected[0]
  assert ticket['state']=='needs_attention' and ticket.get('error')=='API generation rejected: invalid_response'
  active=runtime.read(root/'api/active.json');assert not active or active.get('state')=='SUBMITTED'
  assert not runtime.read(root/'control.json').get('paused')
  record.mkdir(exist_ok=True)
  original_files={str(p):hashlib.sha256(p.read_bytes()).hexdigest() for p in (root/'approved').rglob('*') if p.is_file()}
  atomic_json(record/'approved-before.json',original_files)
  shutil.copy2(ticket_path,record/'ticket-before.json')
  if active:shutil.copy2(root/'api/active.json',record/'active-before.json')
  run=root/'api/runs'/rid
  for name,expected in ticket['inputs'].items():
   assert Path(name).name==name
   assert hashlib.sha256((run/name).read_bytes()).hexdigest()==expected,'Archived input changed: '+name
  for state_path in run.rglob('api_state.json'):
   state=runtime.read(state_path)
   if state.get('state')!='INVALID_RESPONSE':continue
   answer=runtime.read(state_path.parent/'answer.json')
   assert state.get('error_type')=='JSONDecodeError' and answer.get('finish_reason')=='stop'
   result,reason=recover_transport_json(answer['content'])
   atomic_json(record/(state_path.parent.name+'-state-before.json'),state)
   atomic_json(state_path.parent/'json_response_projection.json',{'reason':reason,'raw_answer_preserved':True,'raw_content_sha256':hashlib.sha256(answer['content'].encode()).hexdigest(),'new_paid_requests':0,'downstream_validation_required':True})
   atomic_json(state_path.parent/'response.json',result)
   atomic_json(state_path,{**state,'state':'RESPONDED','finished_epoch':time.time(),'usage':answer.get('usage'),'format_projection':reason})
  budget=runtime.SharedBudget(root)
  class ReplayClient(CreationClient):
   paid=0
   def complete(self,prompt,directory,**kwargs):
    folder=Path(directory)
    if (folder/'response.json').is_file():return runtime.read(folder/'response.json')
    # Only the previously unstarted independent skeleton review may be paid.
    if ticket['stage']!='research' or folder!=run/'skeleton-review-call' or self.paid or (folder/'api_state.json').exists():raise RuntimeError('Unexpected new paid request blocked during replay')
    self.paid+=1
    return super().complete(prompt,directory,**kwargs)
  client=ReplayClient(runtime.KEY,budget=budget)
  try:
   answer=execute(client,root,ticket,run)
   atomic_json(run/'answer.json',answer)
   worker=Worker(root,client)
   assert worker.identity==ticket['client']
   receipt=ticket_path.with_name('receipt.json')
   assert runtime.read(receipt).get('error_code')=='invalid_response'
   # Archive the failed receipt so the ordinary validator can accept this same execution.
   receipt.rename(record/'receipt-before.json')
   ticket={**ticket,'state':'claimed'};ticket.pop('error',None);atomic_json(ticket_path,ticket)
   replay={'state':'RESPONDED','run_id':rid,'ticket':ticket['id'],'execution':ticket['execution']}
   atomic_json(root/'api/active.json',replay)
   result=worker.finish(ticket,replay)
   assert all(Path(p).is_file() and hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in original_files.items())
   result.update(new_paid_calls=client.paid,original_articles_unchanged=True)
   atomic_json(record/'result.json',result);print('RECOVERED',jid,json.dumps(result,ensure_ascii=False),flush=True)
  finally:
   client.session.close();budget.db.close()
