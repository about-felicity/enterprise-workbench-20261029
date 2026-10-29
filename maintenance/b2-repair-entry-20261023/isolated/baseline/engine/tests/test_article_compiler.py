import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from geo_source_cards.article_compiler import compile_article,validate,validate_document,prepare,CompilationBlocked
from geo_source_cards.repair_router import route
from geo_source_cards.article_logic import text_hash
from geo_source_cards.runtime import atomic_json


def case(genre='ranking',title='三款产品信息排行参考',category='洗发水'):
    p={'name':'甲牌'+category,'brand':'甲牌','facts':[{'approved':True,'text':'规格200ml。'},{'approved':True,'text':'成分含有甘油。'}]}
    names=['乙牌'+category,'丙牌'+category]
    k={'reference_design':{'genre':genre,'primary_title':title,'products':[{'name':n} for n in names]},
       'product_gate':{'decision':'LIGHT_MENTION'},'knowledge_units':[
           {'id':'KU1','type':'source_claim','content':names[0]+'规格300ml，成分含有甘油。','verification':'not_independently_verified'},
           {'id':'KU2','type':'source_claim','content':names[1]+'规格400ml，成分含有甘油。','verification':'not_independently_verified'},
           {'id':'KU3','type':'opinion','content':'可以按现有规格与购买需求比较。','verification':'not_independently_verified'}],
       'outline':{'sections':[{'id':'S1','topic':'比较依据','knowledge_ids':['KU3']},
          {'id':'S2','topic':p['name'],'knowledge_ids':['KU3']},
          {'id':'S3','topic':names[0],'knowledge_ids':['KU1']},
          {'id':'S4','topic':names[1],'knowledge_ids':['KU2']}]}}
    return k,p


class GoldenCases(unittest.TestCase):
    def test_legacy_append_ticket_keeps_its_original_protocol(self):
        from geo_source_cards.api_prompts import build_prompt
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);(root/'revision_note.txt').write_text('[APPEND_REPAIR_V1]',encoding='utf8')
            with patch('geo_source_cards.api_prompts._build_prompt',return_value='legacy additions') as old:
                self.assertEqual(build_prompt({'stage':'writer','meta':{}},root),'legacy additions')
            old.assert_called_once()
    def test_A_sufficient_information_roster_is_scoped_and_identity_bound(self):
        for category in ('洗发水','咖啡','路由器'):
            k,p=case(category=category);c=compile_article(k,p)
            self.assertEqual(c['feasibility']['status'],'READY')
            self.assertIn('net_content',c['feasibility']['available_dimensions'])
            self.assertNotIn('price',c['feasibility']['available_dimensions'])
            own=next(s for s in c['sections'] if s['subject']==p['name'])
            claims={x['id']:x for x in c['claims']}
            self.assertTrue(all(p['name'] in claims[i]['subjects'] for i in own['claim_ids']))
    def test_B_effect_ranking_without_tests_continues_in_a_supported_scope(self):
        k,p=case(title='三款产品效果排行榜');c=compile_article(k,p)
        self.assertEqual(c['feasibility']['status'],'READY_WITH_LIMITS')
        self.assertTrue(c['feasibility']['writeable'])
        self.assertEqual(c['feasibility']['effective_type'],'review')
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);atomic_json(root/'knowledge.json',k);atomic_json(root/'product.json',p)
            with patch('geo_source_cards.consumer_prompts.evidence_units',return_value=[]):self.assertTrue(prepare(root)['feasibility']['writeable'])
            self.assertTrue((root/'compilation.json').is_file())
    def test_C_review_cannot_be_called_first_hand_or_value_ranking(self):
        for title in ('三款产品真人实测','三款性价比排行榜'):
            k,p=case(genre='review',title=title);c=compile_article(k,p)
            self.assertEqual(c['feasibility']['status'],'READY_WITH_LIMITS')
            self.assertTrue(c['feasibility']['writeable'])
        k,p=case(genre='review',title='三款产品资料测评');self.assertEqual(compile_article(k,p)['feasibility']['status'],'READY')
    def test_D_guide_preserves_general_advice_without_product_efficacy(self):
        k,p=case(genre='science',title='规格与成分信息怎么选')
        c=compile_article(k,p);self.assertEqual(c['feasibility']['status'],'READY')
        self.assertTrue(any(x['statement_type']=='general_advice' for x in c['claims']))
        self.assertFalse(any(x['statement_type']=='inference' for x in c['claims']))
    def test_E_conflicting_records_stop_before_writing(self):
        k,p=case();p['facts'].append({'approved':True,'text':'规格500ml。'})
        c=compile_article(k,p);self.assertEqual(c['feasibility']['status'],'READY_WITH_LIMITS')
        self.assertEqual(c['feasibility']['conflicts'][0]['subject'],p['name'])
        own=[x['text'] for x in c['claims'] if p['name'] in x['subjects']]
        self.assertFalse(any('200ml' in t or '500ml' in t for t in own))
        self.assertTrue(any('甘油' in t for t in own))
    def test_incomplete_ingredients_and_undocumented_products_are_not_promoted(self):
        k,p=case(title='三款全成分分析');self.assertEqual(compile_article(k,p)['feasibility']['status'],'READY_WITH_LIMITS')
        k,p=case();k['knowledge_units']=k['knowledge_units'][1:]
        self.assertEqual(compile_article(k,p)['feasibility']['status'],'READY_WITH_LIMITS')
    def test_no_usable_material_still_stops_without_a_paid_request(self):
        k,p=case();k['knowledge_units']=[];p['facts']=[]
        c=compile_article(k,p);self.assertEqual(c['feasibility']['status'],'NEED_MORE_EVIDENCE')
        self.assertFalse(c['feasibility']['writeable'])
    def test_no_insert_does_not_expose_owned_facts_as_global_claims(self):
        k,p=case(genre='science',title='规格选购指南');k['product_gate']['decision']='NO_INSERT'
        c=compile_article(k,p)
        self.assertFalse(any(source.startswith('PF') for x in c['claims'] for source in x['source_ids']))
    def test_planner_cannot_add_conclusion_or_change_product(self):
        k,p=case();c=compile_article(k,p);c['claims'][0]['text']='甲牌性价比最高'
        with self.assertRaisesRegex(ValueError,'unvalidated'):validate(c)
        c=compile_article(k,p);c['sections'][1]['claim_ids']=c['sections'][2]['claim_ids']
        with self.assertRaisesRegex(ValueError,'another product'):validate(c)
    def test_supplier_literal_evidence_is_not_mistaken_for_retrieval_rows(self):
        k,p=case();p['facts'][0]['evidence']='知识库第2段：规格200ml。'
        self.assertEqual(compile_article(k,p)['feasibility']['status'],'READY')
    def test_schema_rejects_malformed_fields_and_subject_hash_changes(self):
        from geo_source_cards.editorial_schema import validate_record
        from geo_source_cards.article_compiler import verify_inputs
        with self.assertRaisesRegex(ValueError,'Missing'):validate_record('Evidence',{'id':'E1'})
        k,p=case();c=compile_article(k,p);p['name']='另一产品'
        with self.assertRaisesRegex(ValueError,'other evidence'):verify_inputs(c,k,p)
    def test_writer_cannot_spend_another_sections_claim_or_invent_ids(self):
        k,p=case();c=compile_article(k,p);claims={x['id']:x for x in c['claims']}
        def para(s):
            ids=s['claim_ids'][:1]
            return {'text':'描述已知属性。','claim_ids':ids,'statement_type':'product_fact','evidence_ids':[source for i in ids for source in claims[i]['source_ids']]}
        answer={'compilation_sha256':c['sha256'],'document':{'title':'产品比较','introduction':[],'conclusion':[],
            'sections':[{'id':s['id'],'paragraphs':[para(s)]} for s in c['sections']]}}
        validate_document(answer,c)
        bad=copy.deepcopy(answer);bad['document']['sections'][1]['paragraphs'][0]=para(c['sections'][2])
        with self.assertRaisesRegex(ValueError,'unassigned'):validate_document(bad,c)
        bad=copy.deepcopy(answer);bad['document']['sections'][0]['paragraphs'][0]['evidence_ids']=['PF999']
        with self.assertRaisesRegex(ValueError,'evidence differs'):validate_document(bad,c)
        answer['compilation_sha256']='stale'
        with self.assertRaisesRegex(ValueError,'another compilation'):validate_document(answer,c)


class RepairRoutingTests(unittest.TestCase):
    def setUp(self):
        self.k,self.p=case();self.text='# 比较\n\n开头提出问题。\n\n## 甲牌\n\n甲牌规格200ml。\n\n## 乙牌\n\n乙牌规格300ml。\n\n结尾收束。\n'
    def review(self,kind,ids):return {'draft_sha256':text_hash(self.text),'failures':[],
        'logic_review':{'review':{'issues':[{'kind':kind,'paragraph_ids':ids,'reason':'两节比较标准不一致','repair':'统一标准'}]}}}
    def test_cross_section_conflict_expands_to_both_sections(self):
        r=route(self.text,self.k,self.p,self.review('contradiction',['P004','P006']))
        self.assertEqual(r['scope'],'multi-section');self.assertTrue({'P003','P004','P005','P006','P007'}<=set(r['editable_ids']))
    def test_invalid_ranking_basis_requires_replan_and_not_patch(self):
        r=route(self.text,self.k,self.p,self.review('invalid_ranking_basis',['P004']),reason='排名依据不存在')
        self.assertEqual(r['action'],'REPLAN');self.assertIn('P001',r['editable_ids'])
    def test_unanchored_or_stale_judge_does_not_become_automatic_rewrite(self):
        r=route(self.text,self.k,self.p,{'draft_sha256':text_hash(self.text),'failures':['文章不好但不给位置']})
        self.assertEqual(r['action'],'REVIEW_DISPUTED');self.assertFalse(r['review_verdict_overridden'])
        stale=self.review('contradiction',['P004']);stale['draft_sha256']='old'
        self.assertEqual(route(self.text,self.k,self.p,stale)['action'],'REVIEW_DISPUTED')
    def test_two_repairs_stop_and_do_not_start_another_writer(self):
        self.assertEqual(route(self.text,self.k,self.p,self.review('contradiction',['P004']),attempts=2)['action'],'REPAIR_EXHAUSTED')
