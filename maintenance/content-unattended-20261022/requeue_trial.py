"""One authorized release recheck of yesterday's known-delivered 14 samples.

Preserves the original job/article billing scopes and every API request. Never
use this as a periodic retry script; publication is idempotent per release.
"""
import sys,json,sqlite3,hashlib,shutil,time
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
from geo_source_cards.runtime import atomic_json,atomic_write,process_lock
from geo_source_cards.daily_editorial import publish_ticket
from geo_source_cards.staged_editorial import check,research_for_writer
from geo_source_cards.paragraph_repair import prepare,MARKER
D=Path('/opt/monitor/geo-capture/maintenance/20261022-content-unattended');marker=D/'trial-requeued.json'
assert not marker.exists(),'Already requeued; inspect existing queue, do not repeat'
baseline=runtime.read(D/'preview.json');ledger='/home/user/geo-editorial/runtime-api/api/costs.sqlite'
def unknowns():
 with sqlite3.connect('file:'+ledger+'?mode=ro',uri=True) as db:return sorted(r[0] for r in db.execute('select id from costs where charged is null'))
assert unknowns()==baseline['unknown_ids']
roots=[runtime.job_root(j) for j in ('creation-1792575159-0a8f9221','creation-1792576129-389f575e')]
for root in roots:
 assert hashlib.sha256((root/'control.json').read_bytes()).hexdigest()==baseline['control_sha256'][root.name]
 assert runtime.read(root/'api/active.json').get('state') in (None,'SUBMITTED')
 for p in (root/'api/runs').rglob('api_state.json'):
  assert runtime.read(p).get('state') not in {'REQUESTING','REQUEST_UNKNOWN'} or (p.parent/'response.json').is_file(),str(p)
saved=D/'trial-before';saved.mkdir(exist_ok=True);published=[]
for root in roots:
 with process_lock(root/'coordinator.lock',blocking=True):
  shutil.copytree(root/'queue',saved/root.name/'queue')
  shutil.copy2(root/'control.json',saved/root.name/'control.json')
  jobs=[runtime.read(p) for p in (root/'queue').glob('*/ticket.json')]
  for writer in sorted((root/'days/2026-10-21/jobs').glob('*/*/writer')):
   category=writer.parent.parent.name;number=int(writer.parent.name)
   candidates=[j for j in jobs if j.get('stage') in {'writer','review'} and j['meta'].get('category')==category and j['meta'].get('number')==number]
   assert candidates,(category,number)
   old=max(candidates,key=lambda j:j.get('created_at',''))
   assert old.get('state') in {'needs_attention','revision_requested','accepted'},old['state']
   shutil.copytree(writer,saved/root.name/category/f'{number:02d}'/'writer')
   reason='已授权的通用创作流程升级：使用原事实和原计费范围修复已知失败稿；新稿必须重审，不重发任何未知请求。'
   if (writer/'draft.md').is_file():
    checks=check(research_for_writer(writer),writer)
    reason+='\n'+'; '.join(checks['failures'])
    files=prepare(writer,reason)
   else:files=[]
   inputs=['writing_prompt.md','writing_job.json','knowledge.json','product.json','writing_task.txt','category.json','batch_rules.md']
   inputs += [n for n in ('draft.md','claim_map.json','knowledge_to_sections.json') if (writer/n).is_file()]
   inputs+=files
   atomic_write(writer/'revision_note.txt',(MARKER+'\n' if files else '')+reason)
   meta={k:v for k,v in old['meta'].items() if k not in {'replaces','revision','auto_repair_round','assisted_repair_round','append_repair_round','auto_repair_strategy','paragraph_repair'}}
   meta.update(revision=1,replaces=old['id'],workflow_release='unattended-20261022-v1',paragraph_repair=bool(files),consumer_rewrite=True)
   identity=publish_ticket(root,'writer',writer,list(dict.fromkeys(inputs+['revision_note.txt'])),
       ['draft.md','article.docx','claim_map.json','knowledge_to_sections.json','writer_done.json'],meta)
   for previous in candidates:
    if previous['state']=='needs_attention':
     atomic_json(root/'queue'/previous['id']/'ticket.json',{**previous,'state':'revision_requested','replaced_by':identity,
       'operator_reason':'Authorized workflow release recheck; old costs and responses retained'})
   published.append({'job':root.name,'category':category,'number':number,'ticket':identity,'paragraph_patch':bool(files)})
assert len(published)==14,published
atomic_json(marker,{'at':time.time(),'release':'unattended-20261022-v1','articles':published,
    'original_unknown_ids':unknowns(),'budget_limits_changed':False,'old_job_article_scopes_preserved':True})
for root in roots:runtime.resume(root)
print(json.dumps(runtime.read(marker),ensure_ascii=False))
