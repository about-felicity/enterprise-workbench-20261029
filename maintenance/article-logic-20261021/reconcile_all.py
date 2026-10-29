"""Validate already delivered audit JSON locally; absolutely no API calls."""
import sys,json,hashlib,time,shutil
from pathlib import Path
from collections import Counter
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
from geo_source_cards.article_logic import build_input,certificate,deterministic_issues,enforce
from geo_source_cards.runtime import atomic_json,process_lock
M=Path('/opt/monitor/geo-capture/maintenance/20261021-all-logic');A=runtime.BASE/'logic-review/20261021-all'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
inventory=runtime.read(M/'inventory.json');items={r['key']:r for r in inventory['approved_versions']+inventory['non_current_drafts']};results=[]
for row in runtime.read(M/'audit.json').get('articles',[]):
 side=A/row['key'];response=runtime.read(side/'call/response.json')
 if not response:results.append(row);continue
 item=items[row['key']];result={**row};location=side/'input'
 try:
  data=build_input(location);text=(location/'draft.md').read_text('utf-8-sig');product=runtime.read(location/'product.json')
  original_response=response
  # Some delivered reviews also enumerated body paragraphs. Keep every original
  # byte; project only actual section headings, without changing any judgment.
  headings={p['id'] for p in data['paragraphs'][1:] if p['kind']=='heading'}
  if isinstance(response.get('sequence'),list):
   response={**response,'sequence':[s for s in response['sequence'] if s.get('id') in headings]}
   if len(response['sequence'])!=len(original_response['sequence']):atomic_json(side/'section-sequence-projection.json',{'reason':'Keep all actual heading rows; extra body analysis remains in the raw response','original_rows':len(original_response['sequence']),'retained_heading_rows':len(response['sequence']),'judgments_unchanged':True,'new_paid_requests':0})
  cert=certificate(response,data,deterministic_issues(text,product));atomic_json(side/'locally-validated-certificate.json',cert)
  try:enforce(cert,text,product);result['state']='passed';result.pop('reason',None)
  except ValueError as error:result.update(state='needs_revision',reason=str(error)[:500])
  result.update(issues=cert['review']['issues']+cert.get('local_issues',[]),sequence=cert['review']['sequence'],main_question=cert['review']['main_question'],cached_validation_only=True)
  if item.get('folder'):
   root=Path(item['root']);folder=Path(item['folder'])
   with process_lock(root/'coordinator.lock',blocking=True):
    assert sha(folder/'draft.md')==item['draft_sha256'],'Current draft changed'
    backup=side/'previous-delivery-review';backup.mkdir(exist_ok=True)
    for name in ('receipt.json','logic_review.json','logic_product.json'):
     if (folder/name).exists() and not (backup/name).exists():shutil.copy2(folder/name,backup/name)
    atomic_json(folder/'logic_review.json',cert);shutil.copy2(location/'product.json',folder/'logic_product.json')
    receipt=runtime.read(folder/'receipt.json');receipt.setdefault('files',{}).update({name:sha(folder/name) for name in ('logic_review.json','logic_product.json')});atomic_json(folder/'receipt.json',receipt)
 except (ValueError,KeyError,TypeError,AssertionError) as error:result.update(state='input_or_review_incomplete',reason=str(error)[:600])
 results.append(result)
value={'at':time.time(),'articles':results,'states':dict(Counter(r['state'] for r in results)),'new_api_requests':0,'requested_total':len(items),'audit_finished':bool(runtime.read(M/'audit.json').get('finished_at'))}
atomic_json(M/'validated-audit.json',value)
ready=[];held=[]
for root in inventory['roots']:
 for article in runtime.articles(Path(root)):
  (ready if article['quality_status']=='ready' else held).append({'root':root,**{k:article[k] for k in ('id','title','quality_status')}})
atomic_json(M/'delivery-state.json',{'at':time.time(),'ready':ready,'held':held})
print(json.dumps({'states':value['states'],'validated_records':len(results),'requested_total':len(items),'ready_current_deliveries':len(ready),'held_current_deliveries':len(held),'new_api_requests':0},ensure_ascii=False))
