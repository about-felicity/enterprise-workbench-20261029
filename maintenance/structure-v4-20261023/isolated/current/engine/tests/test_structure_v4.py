"""Saved real V3 responses and local boundary tests. No model verdicts invented."""
import copy,json,os,shutil,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from geo_source_cards import structure_protocol as p,structure_analyzer as a
from geo_source_cards.deepseek_api import APIError
from tests.test_structure_recovery import LocalProtocolClient,response

D=Path(os.environ['GEO_STRUCTURE_FIXTURES']);OLD=D/'real-history';V3=Path(os.environ.get('GEO_V3_CANDIDATE',D.parent/'structure-recovery-20261023'))
read=lambda f:json.loads(Path(f).read_text('utf8'))
class V4Tests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  shutil.copytree(OLD/'article',self.root/'article');self.w=self.root/'article/writer'
  shutil.rmtree(self.w/'structure_calls');(self.w/'article_structure.json').unlink()
  self.data=a.source_input(self.w,read(self.w/'knowledge.json'));self.plan=p.plan(self.data);self.meta={'test':'offline-v4'}
 def migrate(self):return p.import_v3_primaries(self.w,self.w,self.data,self.meta,OLD,V3)
 def analyze(self,c=None):return p.analyze(c or LocalProtocolClient(),self.w,self.w,self.data,self.meta)
 def test_real_saved_first_three_chunks_revalidated_without_api(self):
  imported=self.migrate();self.assertEqual(len(imported),4)
  self.assertTrue(all(v['v3_previously_accepted'] for v in imported[:3]));self.assertFalse(imported[3]['v3_previously_accepted'])
  self.assertEqual(len(imported[3]['normalizations']),1)
  for i in range(3):
   old=read(OLD/f'article/writer/structure_calls/compact-v2/chunk-{i:03d}/primary/response.json')
   new=read(self.w/f'structure_calls/compact-v2/chunk-{i:03d}/primary/accepted.json')['result']
   self.assertEqual(old,new)
 def test_single_anchor_equivalence_only_and_raw_untouched(self):
  c=next(c for c in self.plan['calls'] if c['key']=='chunk-003/primary')
  raw=read(OLD/'article/writer/structure_calls/compact-v2/chunk-003/primary/response.json');before=copy.deepcopy(raw);notes=[]
  out=p.validate_chunk(raw,self.data,c['units'],'compact',notes)
  self.assertEqual(raw,before);self.assertEqual(out['sections'][-1]['anchors'],['O0070'])
  self.assertEqual(notes[0]['raw_anchors'],['O0070','O0070'])
  for anchors in ([],['O0069'],['O0070','O0069'],['O0070']*3,['O9999','O9999']):
   bad=copy.deepcopy(raw);bad['sections'][-1]['anchors']=anchors
   with self.assertRaises(ValueError):p.validate_chunk(bad,self.data,c['units'],'compact')
 def test_multi_anchor_reversal_missing_or_duplicate_rejected(self):
  c=self.plan['calls'][0];v=read(OLD/'article/writer/structure_calls/compact-v2/chunk-000/primary/response.json')
  for anchors in (['O0033','O0003'],['O0003'],['O0003','O0003'],['O0003','O9999']):
   bad=copy.deepcopy(v);bad['sections'][1]['anchors']=anchors
   with self.assertRaises(ValueError):p.validate_chunk(bad,self.data,c['units'],'compact')
 def test_old_invalid_recovery_rejected_and_never_imported(self):
  c=next(c for c in self.plan['calls'] if c['key']=='chunk-003/recover-AS-O0062')
  bad=read(OLD/'article/writer/structure_calls/compact-v2/chunk-003/recover-AS-O0062/response.json')
  with self.assertRaises(ValueError):p.validate_chunk(bad,self.data,c['units'],'minimal')
  self.migrate();self.assertFalse(any(self.w.glob('structure_calls/compact-v2/*/recover-*/accepted.json')))
 def test_recovery_has_separate_schema_and_one_region_only(self):
  c=next(c for c in self.plan['calls'] if c['mode']=='minimal');message=p.prompt(self.data,c['units'],'minimal')
  protocol,source=message.split('\n资料：');sent=json.loads(source)
  self.assertIn('输出合同：',protocol);self.assertEqual(len(sent['units']),1);self.assertNotIn('schema',sent)
  self.assertNotIn('original_text',sent);self.assertNotIn('task_outline',sent);self.assertNotIn('article_title',sent)
  self.assertEqual(sent['units'][0]['blocks'],c['units'][0]['blocks'])
  with self.assertRaises(p.StructureIncomplete):p.prompt(self.data,self.plan['units'][:2],'minimal')
 def test_only_unexecuted_last_chunk_is_simulated_not_regenerated(self):
  self.migrate();client=LocalProtocolClient();out=self.analyze(client)
  self.assertEqual(len(client.calls),1);self.assertIn('chunk-004/primary',client.calls[0][1].replace('\\','/'))
  self.assertEqual(out['status'],'structure_ready_with_checks');self.assertEqual(out['pending_role_checks'],['AS-O0070'])
  self.assertEqual([b for s in out['sections'] for b in s['source_block_ids']],[b['id'] for b in self.data['blocks']])
 def test_needs_check_preserved_and_never_bound_to_a_product(self):
  self.migrate();out=self.analyze();pending=next(s for s in out['sections'] if s['id']=='AS-O0070')
  self.assertEqual(pending['role_status'],'needs_check');self.assertFalse(pending['binding_allowed']);self.assertTrue(pending['role_review']['reason'])
  contract={'sections':[{'id':'SELF','subject':'自有产品','question':'怎样理解','claim_ids':['CL1']},{'id':'OTHER','subject':'其他产品','question':'怎样比较','claim_ids':['CL2']}]}
  bound=a.bind(contract,out);self.assertEqual(bound['sections'][0]['structure_id'],'AS-O0003')
  self.assertEqual([s['claim_ids'] for s in bound['sections']],[['CL1'],['CL2']])
 def test_uncertain_product_reserves_its_slot_without_shifting_identity(self):
  def fault(sent,folder,v):
   for s in v['sections']:
    if s['section_id']=='AS-O0003':s.update(role='unknown',role_status='needs_check')
   return v
  out=self.analyze(LocalProtocolClient(fault));self.assertEqual(out['status'],'structure_ready_with_checks')
  contract={'sections':[{'id':'SELF','subject':'自有','question':'解释','claim_ids':['CL1']},{'id':'OTHER','subject':'其他','question':'解释','claim_ids':['CL2']}]}
  bound=a.bind(contract,out);self.assertIsNone(bound['sections'][0]['structure_id']);self.assertIn('SELF',bound['structure_role_review']['pending_slots'])
  self.assertNotEqual(bound['sections'][1]['structure_id'],'AS-O0003');self.assertEqual(bound['sections'][0]['subject'],'自有')
 def test_input_and_product_or_research_change_invalidate_migration(self):
  for relative in ('article/writer/knowledge.json','article/writer/product.json','article/research/research_result.json'):
   f=self.root/relative;old=f.read_bytes();f.write_bytes(old+b' ')
   with self.assertRaises(p.StructureIncomplete):self.migrate()
   f.write_bytes(old)
 def test_v3_artifact_cannot_be_implicitly_accepted(self):
  old=read(OLD/'article_structure.json')
  with self.assertRaises(ValueError):p.verify(old,self.data)
 def test_completed_v4_cache_current_inputs_only(self):
  self.migrate();out=self.analyze();client=LocalProtocolClient();self.assertEqual(self.analyze(client),out);self.assertEqual(client.calls,[])
  f=self.w/'product.json';f.write_text(f.read_text('utf8')+' ',encoding='utf8')
  with self.assertRaises(p.StructureIncomplete):self.analyze(client)
  self.assertEqual(client.calls,[])
 def test_unknown_request_blocks_migration_without_replay(self):
  tmp=self.root/'legacy';shutil.copytree(OLD,tmp);state=tmp/'article/writer/structure_calls/compact-v2/chunk-003/primary/api_state.json'
  state.write_text(json.dumps({'state':'REQUEST_UNKNOWN'}),encoding='utf8')
  with self.assertRaises(APIError) as error:p.import_v3_primaries(self.w,self.w,self.data,self.meta,tmp,V3)
  self.assertTrue(error.exception.uncertain)
 def test_budget_insufficient_after_reuse_sends_nothing(self):
  self.migrate()
  class Budget:
   def remaining(self,*_):return 0
  c=LocalProtocolClient(budget=Budget())
  with self.assertRaises(APIError):self.analyze(c)
  self.assertEqual(c.calls,[])
 def test_promoting_pending_role_in_artifact_is_rejected(self):
  self.migrate();out=self.analyze();out['status']='structure_ready';out.pop('sha256');out['sha256']=p.digest(out)
  with self.assertRaisesRegex(ValueError,'promoted'):p.verify(out,self.data)
 def test_real_material_compiler_preserves_all_claim_permissions_and_owned_identity(self):
  from geo_source_cards.article_compiler import compile_article
  self.migrate();out=self.analyze();k=read(self.w/'knowledge.json');product=read(self.w/'product.json')
  baseline=compile_article(k,product);bound=a.bind(baseline,out)
  self.assertEqual([(s.get('subject'),s['claim_ids']) for s in baseline['sections']],[(s.get('subject'),s['claim_ids']) for s in bound['sections']])
  own=next(s for s in bound['sections'] if s.get('subject')==product['name']);self.assertEqual(own['structure_id'],'AS-O0003')
  self.assertTrue(all(s.get('structure_id')!='AS-O0070' for s in bound['sections']))
 def test_real_material_full_original_remains_available_for_review(self):
  self.migrate();out=self.analyze();self.assertEqual(a.review_source(out),self.data)
  self.assertEqual(len(a.review_source(out)['blocks']),84)
