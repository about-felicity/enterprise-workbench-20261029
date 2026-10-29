import sys,json,time
from pathlib import Path
D=Path('/opt/monitor/geo-capture/maintenance/20261022-article-quality');sys.path[:0]=['/opt/monitor/geo-content','/opt/monitor/geo-content/engine']
from creation.runtime import read
from geo_source_cards.article_compiler import compile_article,validate_document
from geo_source_cards.consumer_prompts import evidence_units
from geo_source_cards.quality_checks import findings,semantic_candidates
root=Path('/opt/monitor/geo-content/runtime/runs/creation-1792575159-0a8f9221');out=[]
for t in (root/'queue').glob('*/ticket.json'):
 j=read(t)
 if j.get('meta',{}).get('compiler_pilot_release')!='practical-v1':continue
 run=root/'api/runs'/j.get('execution',{}).get('run_id','missing')
 if j['stage']=='writer' and j['meta']['category']=='排行类':
  answer=read(run/'call/response.json');location=root/j['location'];contract=compile_article(read(location/'knowledge.json'),read(location/'product.json'),evidence_units(location))
  try:validate_document(answer,contract,complete=True)
  except ValueError as error:out.append({'sample':'original ranking01 response','result':'rejected_as_incomplete','reason':str(error),'sections':len(answer.get('document',{}).get('sections',[]))})
  else:raise AssertionError('Empty real response was accepted')
 if j['stage']=='review' and j['meta']['category']=='测评类':
  text=(run/'draft.md').read_text();out.append({'sample':'original review02 final text','deterministic_issues':findings(text,read(run/'knowledge.json'),read(run/'product.json')),'semantic_candidates':semantic_candidates(text),'semantic_arbitration':'not_run_budget_insufficient','no_truth_certificate_issued':True})
result={'at':time.time(),'real_saved_response_local_replay_only':True,'new_api_calls':0,'samples':out};(D/'saved-sample-replay.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False))
