"""Independently audit the existing fourteen mask drafts without rewriting."""
import sys,time,json,shutil,hashlib,argparse
from pathlib import Path
sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation import runtime
from creation.client import CreationClient
from creation.quality_repair import writer_for
from geo_source_cards.deepseek_api import APIError
from geo_source_cards.runtime import atomic_json,process_lock
from geo_source_cards.article_logic import enforce
ROOT=runtime.BASE/'runs/creation-1792556219-bbc55e13'
M=Path('/opt/monitor/geo-capture/maintenance/20261021-article-logic');A=runtime.BASE/'logic-review/20261021-mask'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

parser=argparse.ArgumentParser();parser.add_argument('--reconcile-cached',action='store_true');args=parser.parse_args()
with process_lock(A/'audit.lock',blocking=False):
 report=runtime.read(M/'audit.json') or {'started_at':time.time(),'articles':[]}
 report.pop('finished_at',None)
 completed={r['id'] for r in report['articles'] if r.get('state') in {'passed','needs_revision','unknown_request'} or r.get('state')=='known_response_error' and not args.reconcile_cached}
 for folder in sorted((ROOT/'approved').glob('*/*/*')):
  if not (folder/'receipt.json').is_file():continue
  identity=str(folder.relative_to(ROOT/'approved'))
  if identity in completed:continue
  day,category,number=folder.relative_to(ROOT/'approved').parts;meta={'date':day,'category':category,'number':int(number)}
  writer=writer_for(ROOT,day,category,int(number));digest=sha(folder/'draft.md')
  if sha(writer/'draft.md')!=digest:
   matches=[p.parent for p in (ROOT/'days'/day).glob('**/writer/draft.md') if sha(p)==digest]
   assert len(matches)==1,'Need exact matching frozen writer '+identity
   writer=matches[0]
  side=A/category/number;location=side/'input';location.mkdir(parents=True,exist_ok=True)
  if args.reconcile_cached and not (side/'call/response.json').is_file():continue
  atomic_json(side/'job.json',runtime.read(ROOT/'job.json'))
  for name in ('product.json','knowledge.json'):shutil.copy2(writer/name,location/name)
  shutil.copy2(folder/'draft.md',location/'draft.md')
  budget=runtime.SharedBudget(side);client=CreationClient(runtime.KEY,budget=budget)
  row={'id':identity,'title':(folder/'draft.md').read_text().splitlines()[0],'draft_sha256':digest,'writer':str(writer),'audit_root':str(side)}
  try:
   cert=client.review_logic(location,side/'call',meta)
   try:enforce(cert,(location/'draft.md').read_text(),runtime.read(location/'product.json'));row['state']='passed'
   except ValueError as error:row.update(state='needs_revision',reason=str(error))
   with process_lock(ROOT/'coordinator.lock',blocking=True):
    assert sha(folder/'draft.md')==digest,'Article changed during logic audit'
    atomic_json(folder/'logic_review.json',cert);shutil.copy2(location/'product.json',folder/'logic_product.json')
    receipt=runtime.read(folder/'receipt.json')
    receipt['files'].update({name:sha(folder/name) for name in ('logic_review.json','logic_product.json')})
    atomic_json(folder/'receipt.json',receipt)
   row['issues']=cert['review'].get('issues',[])+cert.get('local_issues',[])
  except APIError as error:row.update(state='unknown_request' if error.uncertain else 'known_response_error',reason=error.code)
  except (ValueError,KeyError,TypeError) as error:row.update(state='known_response_error',reason=str(error))
  finally:budget.db.close()
  previous=next((r for r in report['articles'] if r['id']==identity),None)
  if previous:report.setdefault('previous_audits',[]).append(previous)
  report['articles']=[r for r in report['articles'] if r['id']!=identity]+[row];report['updated_at']=time.time();atomic_json(M/'audit.json',report)
  print(json.dumps(row,ensure_ascii=False),flush=True)
  if row['state']=='unknown_request':report['stopped_on_unknown']=True;break
 report['finished_at']=time.time();atomic_json(M/'audit.json',report)
