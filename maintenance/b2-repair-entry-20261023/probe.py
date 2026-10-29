"""Actual frozen/new router code with saved real research, Mock review only."""
import hashlib,importlib.util,json,os,shutil,sys
from pathlib import Path
import offline_guard
D=Path(__file__).resolve().parent;S=D/'isolated/current';sys.path[:0]=[str(S/'engine'),str(S)]
os.environ['GEO_OFFLINE_FIXTURES']=str(D/'fixtures')
from tests import test_b1_b2_offline as fixtures
from geo_source_cards import repair_router as new,review_quality as q,structure_analyzer as a
from geo_source_cards.article_compiler import compile_article
from geo_source_cards.consumer_prompts import evidence_units
from geo_source_cards.article_logic import text_hash
from geo_source_cards.runtime import atomic_json
spec=importlib.util.spec_from_file_location('geo_source_cards._repair_router_baseline',D/'baseline-source/geo_source_cards/repair_router.py')
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
h=fixtures.CacheTests();h.setUp();reason='可以考虑自己的购买条件。需核对这个段落。'
try:
 _,h.k,h.p=fixtures.saved('ranking01')
 for p in (D/'real-fixtures/research').glob('*.json'):shutil.copyfile(p,h.root/'research'/p.name)
 for folder in (h.writer,h.review):
  atomic_json(folder/'knowledge.json',h.k);atomic_json(folder/'product.json',h.p);(folder/'draft.md').write_bytes(h.text.encode('utf8'))
 compiled=a.bind(compile_article(h.k,h.p,evidence_units(h.writer)),fixtures.saved('ranking01')[0])
 for folder in (h.writer,h.review):atomic_json(folder/'writer_done.json',{'compilation':compiled})
 h.fact['draft_sha256']=text_hash(h.text);review=h.process();assert not review.get('arbitration')
 atomic_json(h.review/'result.json',review);before_review=(h.review/'result.json').read_bytes();calls=h.client.calls
 positive={'route':new.route(h.text,h.k,h.p,review,reason,location=h.writer)['action'],'prepare':new.prepare(h.writer,reason)['action']}
 prior_patch=(h.writer/'repair_route.json').read_bytes()
 source=h.root/'research/research_result.json';data=json.loads(source.read_text('utf8'));before_source=hashlib.sha256(source.read_bytes()).hexdigest()
 data['knowledge_units'][0]['content']+='（仅供离线测试：来源版本已更新，须重新核对。）';atomic_json(source,data)
 out={'type':'zero_call_saved_real_research_probe','research_fixture':'saved ranking01 research_input/research_result + knowledge/product',
  'synthetic_method_text_and_mock_judge':True,'real_model_quality_acceptance':False,'arbitration_present':False,'unchanged_valid_patch':positive,
  'source_sha_before':before_source,'source_sha_after':hashlib.sha256(source.read_bytes()).hexdigest(),'routes':{}}
 for label,module in [('frozen_v1',old),('candidate_v2',new)]:
  row={}
  for entry in ('route','prepare'):
   try:
    result=module.route(h.text,h.k,h.p,review,reason,location=h.writer) if entry=='route' else module.prepare(h.writer,reason)
   except ValueError as e:row[entry]={'rejected':True,'status':getattr(e,'status',None),'reason':str(e)}
   else:row[entry]={'rejected':False,'action':result['action']}
  out['routes'][label]=row
 try:q.verify_final(review,h.text,h.k,h.p,location=h.writer)
 except ValueError as e:out['old_final_rejected']=str(e)
 else:raise AssertionError('Old final review was reused')
 out.update(old_review_bytes_unchanged=(h.review/'result.json').read_bytes()==before_review,
  old_patch_bytes_unchanged=(h.writer/'repair_route.json').read_bytes()==prior_patch,
  new_mock_requests=h.client.calls-calls,real_api_calls=0,balance_calls=0,external_business_service_calls=0,blocked_network_attempts=len(offline_guard.blocked))
 assert all(v.get('action')=='PATCH' for v in out['routes']['frozen_v1'].values())
 assert all(v.get('status')=='needs_reaudit' for v in out['routes']['candidate_v2'].values())
 assert out['old_review_bytes_unchanged'] and out['old_patch_bytes_unchanged'] and out['new_mock_requests']==0
 (D/('probe-'+sys.platform+'.json')).write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(out,ensure_ascii=False))
finally:h.doCleanups()
