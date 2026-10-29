"""Observe a stale non-arbitrated result at actual repair entry points offline."""
import json,os,sys
from pathlib import Path
import offline_guard
D=Path(__file__).resolve().parent;S=D/'candidate';sys.path[:0]=[str(S/'engine'),str(S)]
os.environ['GEO_OFFLINE_FIXTURES']=str(D/'fixtures')
from tests.test_b1_b2_offline import CacheTests
from geo_source_cards import repair_router,review_quality
from geo_source_cards.article_logic import text_hash
from geo_source_cards.runtime import atomic_json
h=CacheTests();h.setUp()
try:
 for folder in (h.writer,h.review):(folder/'draft.md').write_bytes(h.text.encode('utf8'))
 h.fact['draft_sha256']=text_hash(h.text);review=h.process();count=h.client.calls
 atomic_json(h.review/'result.json',review)
 source=h.root/'research/research_result.json';value=json.loads(source.read_text('utf8'))
 before=value['knowledge_units'][0]['content'];value['knowledge_units'][0]['content']=before+'原始来源更新：规格改为350ml。';atomic_json(source,value)
 try:review_quality.verify_final(review,h.text,h.k,h.p,location=h.writer)
 except ValueError as e:final={'rejected':True,'reason':str(e)}
 else:final={'rejected':False}
 direct=repair_router.route(h.text,h.k,h.p,review,reason='可以考虑自己的购买条件。需核对这个段落。',location=h.writer)
 try:prepared=repair_router.prepare(h.writer,'可以考虑自己的购买条件。需核对这个段落。')
 except ValueError as e:prepared={'raised':True,'reason':str(e)}
 out={'type':'zero_call_source_path_probe','arbitration_present':bool(review.get('arbitration')),'source_content_before':before,
  'source_content_after':value['knowledge_units'][0]['content'],'draft_and_knowledge_and_product_changed':False,
  'final_verification':final,'route_action':direct['action'],'route_issue_origins':[i['origin'] for i in direct['issues']],
  'prepare_action':prepared.get('action'),'prepare_error':prepared.get('reason'),'new_mock_requests':h.client.calls-count,
  'external_api_calls':0,'blocked_network_attempts':len(offline_guard.blocked),'note':'PATCH routing is not final article acceptance; final verifier still rejects. Source gate is incomplete at repair entry.'}
 (D/'source-probe.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(out,ensure_ascii=False))
finally:h.doCleanups()
