import hashlib,json,tempfile,unittest
from pathlib import Path
from geo_source_cards.runtime import atomic_json,atomic_write
from geo_source_cards.known_response import load

class KnownResponseTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  self.source=self.root/'api/runs'/('a'*24);self.run=self.root/'api/runs'/('b'*24)
  meta={'date':'2026-10-21','category':'测评','number':1}
  self.old={'stage':'writer','execution':{'run_id':'a'*24},'meta':meta,'inputs':{'knowledge.json':hashlib.sha256(b'{}').hexdigest()},'outputs':['draft.md']}
  self.job={'stage':'writer','meta':meta}
  atomic_json(self.root/'queue'/('c'*24)/'ticket.json',self.old)
  atomic_json(self.source/'call/api_state.json',{'state':'RESPONDED'})
  atomic_json(self.source/'call/response.json',{'edits':[]})
  atomic_write(self.run/'knowledge.json','{}')
  atomic_json(self.run/'known_response.json',{'source_run':'a'*24,'source_ticket':'c'*24,
      'response_sha256':hashlib.sha256((self.source/'call/response.json').read_bytes()).hexdigest()})
 def test_complete_known_result_reprocesses_without_any_client(self):
  self.assertEqual(load(self.root,self.job,self.run),{'edits':[]})
 def test_completed_review_rebuilds_sentence_mapping_without_new_request(self):
  from unittest.mock import patch
  self.old['stage']='review';atomic_json(self.root/'queue'/('c'*24)/'ticket.json',self.old)
  with patch('geo_source_cards.api_prompts.build_prompt') as build:
   self.assertEqual(load(self.root,{'stage':'review','meta':self.job['meta']},self.run),{'edits':[]})
  build.assert_called_once_with({'stage':'review','meta':self.job['meta']},self.run)
 def test_unknown_logic_cannot_be_attached_to_completed_fact_review(self):
  from unittest.mock import patch
  self.old['stage']='review';atomic_json(self.root/'queue'/('c'*24)/'ticket.json',self.old)
  proof=json.loads((self.run/'known_response.json').read_text('utf8'));proof['logic_source_run']='d'*24
  atomic_json(self.run/'known_response.json',proof)
  atomic_json(self.root/'api/runs'/('d'*24)/'logic-call/api_state.json',{'state':'REQUEST_UNKNOWN'})
  with patch('geo_source_cards.api_prompts.build_prompt'),self.assertRaisesRegex(ValueError,'not a completed'):
   load(self.root,{'stage':'review','meta':self.job['meta']},self.run)
 def test_logic_reuse_requires_exact_messages_and_revalidates_certificate(self):
  from unittest.mock import patch
  from geo_source_cards.deepseek_api import request_payload
  self.old['stage']='review';atomic_json(self.root/'queue'/('c'*24)/'ticket.json',self.old)
  logic=self.root/'api/runs'/('d'*24)/'logic-call'
  atomic_json(logic/'api_state.json',{'state':'RESPONDED'});atomic_json(logic/'response.json',{'verdict':'pass'})
  proof=json.loads((self.run/'known_response.json').read_text('utf8'))
  proof.update(logic_source_run='d'*24,logic_response_sha256=hashlib.sha256((logic/'response.json').read_bytes()).hexdigest())
  atomic_json(self.run/'known_response.json',proof);atomic_write(self.run/'draft.md','text');atomic_json(self.run/'product.json',{})
  atomic_json(logic/'request.json',request_payload('other text',2000))
  with patch('geo_source_cards.api_prompts.build_prompt'),patch('geo_source_cards.article_logic.build_input',return_value={'bound':'current'}),patch('geo_source_cards.article_logic.prompt',return_value='exact text'),patch('geo_source_cards.article_logic.certificate',return_value={'status':'passed'}) as cert,patch('geo_source_cards.article_logic.deterministic_issues',return_value=[]):
   with self.assertRaisesRegex(ValueError,'input changed'):load(self.root,{'stage':'review','meta':self.job['meta']},self.run)
   cert.assert_not_called()
   atomic_json(logic/'request.json',request_payload('exact text',2000))
   answer=load(self.root,{'stage':'review','meta':self.job['meta']},self.run)
   self.assertEqual(answer['logic_review'],{'status':'passed'})
   cert.assert_called_once_with({'verdict':'pass'},{'bound':'current'},[])
 def test_unknown_different_article_or_changed_input_never_replays(self):
  atomic_json(self.source/'call/api_state.json',{'state':'REQUEST_UNKNOWN'})
  with self.assertRaises(ValueError):load(self.root,self.job,self.run)
  atomic_json(self.source/'call/api_state.json',{'state':'RESPONDED'})
  with self.assertRaises(ValueError):load(self.root,{'stage':'writer','meta':{**self.job['meta'],'number':2}},self.run)
  atomic_write(self.run/'knowledge.json','{"changed":true}')
  with self.assertRaises(ValueError):load(self.root,self.job,self.run)
