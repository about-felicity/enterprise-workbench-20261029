import sys,json,hashlib,shutil,time
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime,recovery
from geo_source_cards.runtime import process_lock,atomic_json
from geo_source_cards.rewrite_v2 import structure_parser,full_writer
D=Path('/opt/monitor/maintenance/creation-formats-20261028')
items=[('creation-1793138057-6e622eb2','a8572d181d770bf2b351639d','cd29d2f7bc299fabaf58c393'),('creation-1793067139-f0f51240','8b7cf75e50166f9dc3eaca45','c8d78ef69d4560ca45d77f9e'),('creation-1793067131-091aa6e1','0f7d9529975fcbb3de1759d7','3a047c82f1dbfecef0b18aa2'),('creation-1793066668-d2f25dd3','c11eb1da90a272883a3bb12c','c97f0c6f8dfe585d4baef2aa')]
for jid,tid,rid in items:
 root=runtime.BASE/'runs'/jid;backup=D/jid
 with process_lock(root/'api/worker.lock',blocking=False):
  with process_lock(root/'coordinator.lock',blocking=False):
   tpath=root/'queue'/tid/'ticket.json';t=runtime.read(tpath);run=root/'api/runs'/rid
   assert t['state']=='needs_attention' and t['execution']['run_id']==rid
   receipt=tpath.with_name('receipt.json');assert runtime.read(receipt)['error_code']=='rewrite_v2_invalid_output'
   active=runtime.read(root/'api/active.json');assert not active or active['state']=='SUBMITTED'
   for p in run.rglob('api_state.json'):
    assert runtime.read(p)['state']=='RESPONDED' and p.with_name('response.json').is_file(),str(p)
   for name,digest in t['inputs'].items():
    assert hashlib.sha256((run/name).read_bytes()).hexdigest()==digest
    assert hashlib.sha256((root/t['location']/name).read_bytes()).hexdigest()==digest
   call=run/('skeleton-call' if t['stage']=='research' else 'call')
   raw=runtime.read(call/'response.json')
   if t['stage']=='research':structure_parser.validate(raw)
   else:
    answer=full_writer.normalize_answer(raw);assert set(answer)=={'draft_markdown'} and answer['draft_markdown'].startswith('# ')
   backup.mkdir(exist_ok=False)
   for p in [tpath,receipt,root/'api/active.json',root/'days'/t['meta']['date']/'day.json']:
    if p.exists():shutil.copy2(p,backup/p.name)
   receipt.rename(backup/'original-failed-receipt.json')
   marker=tpath.with_name('auto_repair_blocked.json')
   if marker.exists():marker.rename(backup/marker.name)
   atomic_json(tpath,{k:v for k,v in {**t,'state':'claimed'}.items() if k!='error'})
   atomic_json(root/'api/active.json',{'ticket':tid,'run_id':rid,'execution':t['execution'],'state':'REQUESTING'})
   daypath=root/'days'/t['meta']['date']/'day.json';day=runtime.read(daypath);atomic_json(daypath,{**day,'status':'producing'})
   atomic_json(backup/'recovery.json',{'at':time.time(),'same_run':rid,'raw_response_sha256':hashlib.sha256((call/'response.json').read_bytes()).hexdigest(),'reason':'lossless schema normalization; reuse original paid response'})
  runtime.resume(root,check_balance=False)
 print('RESUMED',jid,tid,flush=True)
