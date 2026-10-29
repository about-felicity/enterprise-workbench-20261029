import json,tempfile,unittest
from pathlib import Path
from geo_source_cards.genre_pools import classify,classify_source
from geo_source_cards.reference_design import design,validate_structure
from geo_source_cards.article_allocation import allocate,validate_quotas
from geo_source_cards.article_logic import WRITING_RULES

def source(title='两款洗发水横向测评',url='https://www.sohu.com/a/review'):
 return {'url':url,'article':{'status':'fetched','title':title,'text':'比较维度是成分资料与包装。\n1.甲牌洗发水\n品牌提供的配方资料明确列有甘油和透明质酸钠。规格为200ml，包装是泵头瓶。\n2.乙牌洗发水\n品牌提供的配方资料明确列有氯化钠和丙二醇。规格为300ml，包装采用翻盖。'}}

class ReviewGenreTests(unittest.TestCase):
 def test_review_is_opt_in_and_does_not_reclassify_legacy_jobs(self):
  item=source();self.assertEqual(classify_source(item)['genre'],'排行类')
  r=classify_source(item,True);self.assertEqual((r['genre'],r['status']),('测评类','ready'))
  result=classify([item,source('两款洗发水推荐','b')],include_review=True)
  self.assertEqual(result['version'],'three-genre-v1')
  self.assertEqual({r['label'] for r in result['categories']},{'排行类','测评类'})
 def test_review_keyword_cannot_certify_missing_roster(self):
  item={'url':'a','article':{'title':'洗发水实测测评','text':'这款产品一定有效，立即点击购买。'}}
  self.assertEqual(classify_source(item,True)['status'],'needs_review')
 def test_test_headline_needs_comparison_structure_to_enter_review_pool(self):
  item=source('两款洗发水实测')
  self.assertEqual(classify_source(item,True)['genre'],'测评类')
  item['article']['text']=item['article']['text'].replace('比较维度是成分资料与包装。','日常产品资料介绍。')
  self.assertEqual(classify_source(item,True)['genre'],'排行类')
  self.assertEqual(classify_source(source('两款洗发水实测'))['genre'],'排行类')
 def test_seven_plus_seven_does_not_fill_missing_reviews_with_rankings(self):
  pools={'排行类':[(str(i),str(i)) for i in range(20)],'测评类':[('v'+str(i),'v'+str(i)) for i in range(4)]}
  a=allocate(pools,14,['排行类','测评类'],{'排行类':7,'测评类':7})
  self.assertEqual((len(a['selected']['排行类']),len(a['selected']['测评类']),a['shortfall']),(7,4,3))
  self.assertRaises(ValueError,validate_quotas,{'排行类':7,'测评类':6},14)
 def test_blueprint_keeps_real_review_and_comparison_role(self):
  b=design([source()],'测评类');self.assertEqual(b['genre'],'review')
  self.assertEqual(b['version'],'three-genre-v1');self.assertEqual(len(b['products']),2)
  self.assertEqual(b['product_insertion'],'FIRST_COMPARISON')
 def test_research_binding_retains_review_roles_before_writer_is_queued(self):
  from geo_source_cards.genre_outline import bind
  from geo_source_cards.product_identity import bind as bind_product
  b=bind_product(design([source()],'测评类'),{'name':'丙牌洗发水'})
  answer={'units':[{'id':'KU01','kind':'source_claim','text':'甲牌洗发水规格为200ml。','evidence':['R1_1']},{'id':'KU02','kind':'source_claim','text':'乙牌洗发水规格为300ml。','evidence':['R2_1']},{'id':'KU03','kind':'opinion','text':'根据组成与包装比较。','evidence':['R0_1']}], 'sections':[{'id':'S1','topic':'选购前需知'},{'id':'S2','topic':'总结'}]}
  result=bind(answer,b)
  self.assertEqual(result['sections'][0]['topic'],'统一比较维度与资料边界')
  self.assertEqual(result['sections'][1]['topic'],'丙牌洗发水')
  self.assertEqual(validate_structure('\n'.join('## '+s['topic'] for s in result['sections']),b,include_length=False),[])
 def test_renamed_ranking_without_dimensions_or_with_fake_test_is_rejected(self):
  b=design([source()],'测评类');b['owned_product']={'name':'丙牌洗发水','brand':'丙牌'}
  text='# 三款资料测评\n\n## 1.丙牌洗发水\n\n介绍。\n\n## 2.甲牌洗发水\n\n介绍。\n\n## 3.乙牌洗发水\n\n我们本次实测评分98分。\n\n## 总结\n\n结尾。'
  errors=validate_structure(text,b,include_length=False)
  self.assertTrue(any('统一比较维度' in e for e in errors));self.assertTrue(any('编造作者实测' in e for e in errors))
 def test_new_and_rewrite_writer_routes_receive_shared_logic_rules(self):
  from geo_source_cards.api_prompts import build_prompt
  from geo_source_cards.runtime import atomic_json
  for rewrite in (False,True):
   with self.subTest(rewrite=rewrite),tempfile.TemporaryDirectory() as d:
    from .test_article_compiler import case
    p=Path(d);k,product=case(genre='review',title='三款产品资料测评')
    atomic_json(p/'knowledge.json',k);atomic_json(p/'product.json',product)
    prompt=build_prompt({'stage':'writer','meta':{'consumer_rewrite':rewrite}},p)
    self.assertIn(WRITING_RULES,prompt)
    self.assertIn('不得把其他品类的示例和术语带入当前产品',prompt)
    self.assertNotIn('显色',WRITING_RULES)
    data=json.loads(prompt.rsplit('\n资料：',1)[1]);self.assertEqual(data['compilation']['genre'],'review')
    self.assertEqual([s['id'] for s in data['compilation']['sections']],['S1','S2','S3','S4'])
 def test_local_taxonomy_input_and_queue_preserve_requested_review_quota(self):
  from geo_source_cards.daily_editorial import prepare_day,start_research
  from geo_source_cards.runtime import atomic_json,atomic_write
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);items=[source('两款洗发水横向测评'),source('两款洗发水推荐','https://www.sohu.com/a/rank')]
   # Different repeated tokens prevent these two fixture originals deduplicating.
   for i,s in enumerate(items):s['article']['text']+='\n'+chr(0x4e11+i)*600
   atomic_json(p/'product.json',{'name':'丙牌洗发水','facts':[]})
   atomic_json(p/'article_goal.json',{'target':2,'genre_targets':{'排行类':1,'测评类':1}})
   atomic_write(p/'articles.jsonl',json.dumps({'question':'洗发水','sources':items},ensure_ascii=False)+'\n')
   prepare_day(p,p/'articles.jsonl',p/'product.json','2026-10-21',max_per_category=7)
   day=p/'days/2026-10-21';self.assertTrue(json.loads((day/'taxonomy/input.json').read_text())['include_review'])
   atomic_json(day/'taxonomy/result.json',classify(items,7,include_review=True));start_research(p,day)
   blueprints=[json.loads(f.read_text())['reference_design'] for f in day.glob('jobs/*/*/research/research_input.json')]
   self.assertEqual({b['genre'] for b in blueprints},{'ranking','review'})
