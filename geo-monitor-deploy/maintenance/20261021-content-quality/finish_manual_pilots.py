"""Close only this maintenance's failed tickets after a real replacement receipt."""
import json,shutil,sys,time
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
from geo_source_cards.runtime import process_lock
from geo_source_cards.daily_editorial import file_hash

def finish(job,day,number,reason,revision,epoch):
 root=runtime.job_root(job);folder=root/'approved'/day/'科普类'/f'{number:02d}'
 receipt=runtime.read(folder/'receipt.json');review=runtime.read(folder/'semantic_review.json')
 assert receipt.get('word_sha256')==file_hash(folder/'article.docx')
 assert runtime.read(folder/'content_revision.json').get('review_draft_sha256')==file_hash(folder/'draft.md')
 assert review.get('draft_sha256')==file_hash(folder/'draft.md')
 backup=root/'repair_evidence'/('close-consumer-maintenance-'+day+'-'+str(number));assert not backup.exists()
 with process_lock(root/'coordinator.lock',blocking=True):
  control=runtime.read(root/'control.json')
  assert (control.get('reason'),control.get('revision'),control.get('paused_epoch'))==(reason,revision,epoch),control
  assert runtime.read(root/'api/active.json').get('state') in (None,'SUBMITTED')
  backup.mkdir(parents=True);shutil.copy2(root/'control.json',backup/'control.json')
  changed=[]
  for p in (root/'queue').glob('*/ticket.json'):
   t=runtime.read(p);m=t.get('meta',{})
   if (m.get('date'),m.get('category'),m.get('number'))!=(day,'科普类',number) or t.get('state') not in ('needs_attention','pending'):continue
   shutil.copy2(p,backup/(p.parent.name+'.json'))
   runtime.atomic_json(p,{**t,'state':'revision_requested','superseded_by_independent_revision':str(folder/'content_revision.json'),'updated_at':time.time()});changed.append(t.get('id',p.parent.name))
  runtime.atomic_json(backup/'proof.json',{'at':time.time(),'review':str(folder/'semantic_review.json'),'word_sha256':receipt['word_sha256'],'replaced_tickets':changed,'original_failed_outputs_accepted':False})
 # resume() rechecks API availability and also refuses any unknown active send.
 assert runtime.read(root/'control.json')==control
 print(json.dumps({'job':job,**runtime.resume(root),'superseded_failed_tickets':len(changed)}))

if __name__=='__main__':
 finish('creation-1792479954-8a96bc88','2026-10-20',5,'consumer_prompt_maintenance',15,1792545971.3016698)
