import json,tempfile,unittest
from pathlib import Path
from geo_source_cards.article_allocation import allocate

class AllocationTests(unittest.TestCase):
 def test_real_daily_queue_uses_total_and_keeps_primary_sources_distinct(self):
  from geo_source_cards.runtime import atomic_json,atomic_write
  from geo_source_cards.daily_editorial import prepare_day,start_research
  from geo_source_cards.genre_pools import classify
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);sources=[]
   for i in range(6):
    ranking=i<3;marker=chr(0x4e10+i)
    body=('1.甲'+marker+'眼霜\n品牌提供的配方资料列有甘油和透明质酸钠。\n2.乙'+marker+'眼霜\n品牌资料列出产品包装与规格说明。\n' if ranking else '眼周护理的日常知识解释。\n')+marker*500
    sources.append({'url':f'https://www.sohu.com/a/{i}','title':'产品推荐' if ranking else '眼周知识解释','article':{'status':'fetched','title':'产品推荐' if ranking else '眼周知识解释','text':body}})
   product={'name':'测试品牌眼霜','brand':'测试品牌','facts':[{'text':'规格15g','evidence':'测试提供的资料','approved':True}]}
   atomic_json(root/'product.json',product);atomic_json(root/'article_goal.json',{'target':5,'prefer_genres':['排行类','科普类']})
   atomic_write(root/'articles.jsonl',json.dumps({'question':'眼霜','body':'回答','sources':sources},ensure_ascii=False)+'\n')
   prepare_day(root,root/'articles.jsonl',root/'product.json','2026-10-20',max_per_category=5)
   day=root/'days/2026-10-20';atomic_json(day/'taxonomy/result.json',classify(sources,5))
   start_research(root,day)
   result=json.loads((day/'day.json').read_text());self.assertEqual(result['planned_articles'],5)
   blueprints=[json.loads(p.read_text())['reference_design'] for p in day.glob('jobs/*/*/research/research_input.json')]
   self.assertEqual(len({v['primary_url'] for v in blueprints}),5)
   self.assertTrue(all(v['owned_product']['name']=='测试品牌眼霜' for v in blueprints))
 def test_target_balances_pools_and_is_not_fixed_at_fifteen(self):
  pools={'排行类':[(f'r{i}',f'r{i}') for i in range(30)],'科普类':[(f's{i}',f's{i}') for i in range(30)]}
  for target in (1,7,15,20):
   a=allocate(pools,target,['排行类','科普类'])
   self.assertEqual(a['planned'],target);self.assertEqual(a['shortfall'],0)
   self.assertLessEqual(abs(len(a['selected']['排行类'])-len(a['selected']['科普类'])),1)
 def test_duplicate_originals_cannot_pad_count(self):
  a=allocate({'排行类':[('u1','same'),('u2','same'),('u3','other')],'科普类':[('u4','same')]},15,['排行类','科普类'])
  self.assertEqual(a['planned'],2);self.assertEqual(a['shortfall'],13)
 def test_short_pool_redistributes_without_inventing_science(self):
  a=allocate({'排行类':[(f'u{i}',str(i)) for i in range(15)]},15,['排行类','科普类'])
  self.assertEqual(a['planned'],15);self.assertEqual(a['missing_genres'],['科普类'])
  self.assertRaises(ValueError,allocate,{},0,[])
