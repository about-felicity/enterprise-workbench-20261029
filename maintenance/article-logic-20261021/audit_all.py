"""Bounded all-draft review; exact inputs, original caps, no writer or replay."""
import sys,time,json,shutil,hashlib,threading,concurrent.futures
from pathlib import Path
from collections import Counter
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
from creation.client import CreationClient
from geo_source_cards.article_logic import enforce,VERSION
from geo_source_cards.deepseek_api import APIError
from geo_source_cards.runtime import atomic_json,process_lock
from geo_source_cards.pipeline_control import PipelinePaused
M=Path('/opt/monitor/geo-capture/maintenance/20261021-all-logic');A=runtime.BASE/'logic-review/20261021-all'
LOCK=threading.Lock();STOP=threading.Event();report=runtime.read(M/'audit.json') or {'started_at':time.time(),'articles':[]}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(row):
 with LOCK:
  report['articles']=[x for x in report['articles'] if x['key']!=row['key']]+[row]
  report['updated_at']=time.time();report['states']=dict(Counter(r['state'] for r in report['articles']));atomic_json(M/'audit.json',report)
 print(json.dumps({k:v for k,v in row.items() if k not in ('issues',)},ensure_ascii=False),flush=True)
 return row
def audit(item):
 old=next((r for r in report['articles'] if r['key']==item['key']),None)
 if old:return old
 row={k:item[k] for k in ('key','root','title','draft_sha256')};row['current_delivery']=bool(item.get('folder'));row['id']=item.get('id',item.get('path'));row['state']='not_started'
 control=runtime.read(A/item['key']/'control.json')
 if control.get('reason')=='audit_contract_maintenance':atomic_json(A/item['key']/'control.json',{'paused':False,'revision':control.get('revision',0)+1,'reason':'audit_contract_maintenance_finished','resumed_epoch':time.time()})
 if STOP.is_set():row['state']='not_started_after_unknown';return save(row)
 budget=None;side=A/item['key'];side.mkdir(parents=True,exist_ok=True);location=side/'input';location.mkdir(exist_ok=True)
 try:
  assert item['product_path'] and item['knowledge_path'],'Frozen product or knowledge is missing'
  source=Path(item['folder'])/'draft.md' if item.get('folder') else Path(item['path']);assert sha(source)==item['draft_sha256'],'Draft changed since inventory'
  root=Path(item['root']);job=runtime.read(root/'job.json') or {'job_id':root.name,'date':item['date']};atomic_json(side/'job.json',job)
  for name,path in [('draft.md',source),('product.json',Path(item['product_path'])),('knowledge.json',Path(item['knowledge_path']))]:shutil.copy2(path,location/name)
  assert item.get('category') and isinstance(item.get('number'),int),'Article metadata is missing'
  meta={k:item[k] for k in ('date','category','number')};budget=runtime.SharedBudget(side);client=CreationClient(runtime.KEY,budget=budget)
  cert=client.review_logic(location,side/'call',meta)
  try:enforce(cert,(location/'draft.md').read_text('utf-8-sig'),runtime.read(location/'product.json'));row['state']='passed'
  except ValueError as error:row.update(state='needs_revision',reason=str(error)[:500])
  row['issues']=cert['review'].get('issues',[])+cert.get('local_issues',[]);row['main_question']=cert['review']['main_question'];row['sequence']=cert['review']['sequence']
  if item.get('folder'):
   folder=Path(item['folder'])
   with process_lock(root/'coordinator.lock',blocking=True):
    assert sha(folder/'draft.md')==item['draft_sha256'],'Approved draft changed during review'
    backup=side/'previous-delivery-review';backup.mkdir(exist_ok=True)
    for name in ('receipt.json','logic_review.json','logic_product.json'):
     if (folder/name).exists() and not (backup/name).exists():shutil.copy2(folder/name,backup/name)
    atomic_json(folder/'logic_review.json',cert);shutil.copy2(location/'product.json',folder/'logic_product.json')
    receipt=runtime.read(folder/'receipt.json');receipt.setdefault('files',{}).update({name:sha(folder/name) for name in ('logic_review.json','logic_product.json')});atomic_json(folder/'receipt.json',receipt)
 except PipelinePaused as error:row.update(state='maintenance_hold',reason=str(error))
 except APIError as error:
  row.update(state='unknown_request' if error.uncertain else 'budget_blocked' if error.code=='budget_exceeded' else 'known_response_error',reason=error.code)
  if error.uncertain:STOP.set()
 except (ValueError,KeyError,TypeError,AssertionError) as error:row.update(state='input_or_review_incomplete',reason=str(error)[:600])
 finally:
  if budget:budget.db.close()
 row['finished_at']=time.time();return save(row)
with process_lock(A/'audit.lock',blocking=False):
 inventory=runtime.read(M/'inventory.json');current=inventory['approved_versions'];drafts=inventory['non_current_drafts']
 # Previously available deliveries get the stronger audit first; no old pass is reused.
 current.sort(key=lambda x:(runtime.read(Path(x['folder'])/'logic_review.json').get('status')!='passed',x['date'],x['key']))
 controls={str(Path(r)/'control.json'):sha(Path(r)/'control.json') for r in inventory['roots'] if (Path(r)/'control.json').exists()}
 atomic_json(M/'controls-before.json',controls)
 with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(audit,current+drafts))
 report['finished_at']=time.time();report['all_requested_versions']=len(current)+len(drafts);report['original_controls_unchanged']=all(sha(Path(p))==h for p,h in controls.items());atomic_json(M/'audit.json',report)
 print(json.dumps({'states':report['states'],'original_controls_unchanged':report['original_controls_unchanged'],'all_requested_versions':report['all_requested_versions']},ensure_ascii=False),flush=True)
