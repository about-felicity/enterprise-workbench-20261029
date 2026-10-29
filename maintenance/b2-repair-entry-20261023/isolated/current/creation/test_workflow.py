import hashlib,json,tempfile,unittest,zipfile
from pathlib import Path
from unittest.mock import patch
from . import knowledge,studio,materials,runtime
from geo_source_cards.runtime import atomic_json
from geo_source_cards.api_budget import BudgetExceeded


class WorkflowTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
  self.ps=[patch.object(studio,'ROOT',self.root/'studio'),patch.object(materials,'ROOT',self.root/'capture'),patch.object(materials,'GEO',self.root/'geo'),patch.object(runtime,'BASE',self.root/'jobs'),patch.object(runtime,'SHARED',self.root/'legacy')]
  for p in self.ps:p.start()
  atomic_json(materials.GEO/'daily_plan.json',{'time':'09:00'})
 def tearDown(self):
  for p in reversed(self.ps):p.stop()
  self.tmp.cleanup()
 def payload(self):
  kb=studio.save_product({'name':'产品甲','brand':'品牌甲','facts':['用户提供的原始事实']})
  return {'name':'产品甲一次任务','product_id':kb['product_id'],'frequency':'once','task_type':'collect_write','questions':['问题甲'],'channels':['baidu_ai'],'capture_time':'01:00','writing_time':'03:00','start_date':'2099-10-20','enabled':True,'rounds':1,'max_per_category':2,'article_budget_cny':0.1,'task_budget_cny':1}
 def test_word_fields_keep_quotes_without_claim_verification(self):
  a=knowledge.analyze('一、产品名称：科熙本二硫化硒清爽去屑止痒洗发水——原文宣传语\n容量200ml/瓶\n京东科熙本旗舰店\n生产企业:原生产企业\n五、适合人群：\n油性头皮\n六、使用方法\n实测99.8%','资料.docx')
  self.assertEqual(a['name'],'科熙本二硫化硒清爽去屑止痒洗发水');self.assertEqual(a['brand'],'科熙本')
  self.assertEqual(a['specification'],'200ml/瓶');self.assertEqual(a['audience'],'油性头皮')
  self.assertIn('实测99.8%',a['claims_to_review']);self.assertIn('尚未独立核验',a['note'])
 def test_repeated_product_title_preferred_to_generic_filename(self):
  a=knowledge.analyze('焕颜计小白罐美白精华霜\n一、焕颜计小白罐美白精华霜：产品资料\n二、产品信息','美白知识库新的.docx')
  self.assertEqual(a['name'],'焕颜计小白罐美白精华霜')
  self.assertIn('文档首行标题',a['field_evidence']['name'])
  self.assertEqual(knowledge.analyze('产品知识库\n资料内容','资料.docx')['name'],'资料')
 def test_product_information_title_and_configurable_task_target(self):
  text='甲品牌抗皱眼霜产品信息：\n甲品牌抗皱眼霜15g/支'
  self.assertEqual(knowledge.analyze(text,'眼霜知识库.docx')['name'],'甲品牌抗皱眼霜')
  v=self.payload();v['article_target']=15
  p=studio.plan(studio.save_plan(v)['plan_id']);self.assertEqual(p['article_target'],15)
  v['plan_id']=p['plan_id'];v['article_target']=7
  self.assertEqual(studio.plan(studio.save_plan(v)['plan_id'])['article_target'],7)
  v['article_target']=101
  self.assertRaises(ValueError,studio.save_plan,v)
 def test_task_pool_preserves_every_question_and_idempotent_single_job(self):
  v=self.payload();v['article_target']=15;v['questions']=['问题甲','问题乙']
  p=studio.plan(studio.save_plan(v)['plan_id'])
  count=[{'id':'baidu_ai','completed':2}]
  from datetime import datetime
  with patch.object(materials,'progress',return_value=count),patch.object(runtime,'action',return_value={'job_id':'creation-1000-aabbccdd'}) as action:
   for _ in range(2):studio.advance(p,'2099-10-20',datetime(2099,10,20,4,tzinfo=studio.ZONE))
   self.assertEqual(action.call_count,1)
   payload=action.call_args[0][1];self.assertEqual(payload['questions'],v['questions']);self.assertEqual(payload['article_target'],15)
 def test_daily_snapshot_preserves_executing_article_target_after_plan_edit(self):
  v=self.payload();v['article_target']=15
  p=studio.plan(studio.save_plan(v)['plan_id']);studio.ensure_day(p,'2099-10-20')
  v.update(plan_id=p['plan_id'],article_target=7);studio.save_plan(v)
  with patch.object(materials,'progress',return_value=[{'id':'baidu_ai','completed':0,'blocked':0}]):
   rows=studio.snapshot([])['daily_tasks']
  day=next(row for row in rows if row['plan_id']==p['plan_id'] and row['date']=='2099-10-20')
  self.assertEqual(day['article_target'],15)
  self.assertEqual(studio.plan(p['plan_id'])['article_target'],7)
 def test_pooled_runtime_collects_all_questions_and_reuses_original_job(self):
  v=self.payload();v.update(article_target=15,questions=['问题甲','问题乙'],channels=['baidu_ai','wenxin_card'])
  p=studio.plan(studio.save_plan(v)['plan_id']);studio.ensure_day(p,'2099-10-20')
  root=studio.capture_root(p['plan_id'])
  for model in p['channels']:
   rows=[{'model':model,'question':q,'task_id':model+q,'body':'完整回答','body_capture_complete':True,'sources':[]} for q in p['questions']]
   runtime.atomic_write(root/'days/2099-10-20'/model/'results.jsonl',''.join(json.dumps(row,ensure_ascii=False)+'\n' for row in rows))
  payload={'material_source':'dedicated','studio_plan_id':p['plan_id'],'date':'2099-10-20','question':'任务问题汇总','questions':p['questions'],'channels':p['channels'],'article_target':15,'max_per_category':1,'product':p['product']}
  with patch.object(runtime,'balance',return_value={'is_available':True}),patch.object(runtime.source_adapter,'observations',side_effect=AssertionError('No main GEO query')):
   result=runtime.create(payload);again=runtime.create(payload)
  self.assertEqual(result['job_id'],again['job_id']);self.assertTrue(again['reused'])
  job=runtime.read(runtime.job_root(result['job_id'])/'job.json')
  self.assertEqual(job['article_target'],15);self.assertEqual(job['material_counts']['private_observations'],4)
  self.assertTrue(runtime.read(runtime.job_root(result['job_id'])/'logic_policy.json')['required'])
 def test_private_browser_identity_isolated_between_products(self):
  from .browser_capture import assignment_id,record
  self.assertNotEqual(assignment_id('/one/product','task'),assignment_id('/other/product','task'))
  with self.assertRaises(ValueError):record({'prompt':'问题甲','status':'success','web_body':'正文','sources':[],'source_capture_complete':False},{'question':'问题甲'})
 def test_oneoff_capture_never_rolls_to_next_day(self):
  p=studio.plan(studio.save_plan(self.payload())['plan_id'])
  self.assertEqual(studio.scheduled_day(p,'2099-10-21'),'2099-10-20')
  self.assertEqual(materials.next_day({'frequency':'once','start_date':'2099-10-20'},'2099-10-21'),'2099-10-20')
 def test_budget_and_task_type_survive_plan_save(self):
  value=self.payload();value['task_type']='capture_only';p=studio.plan(studio.save_plan(value)['plan_id'])
  self.assertEqual(p['task_budget_cny'],1);self.assertEqual(p['task_type'],'capture_only')
  with patch.object(runtime,'action') as action:
   from datetime import datetime
   studio.advance(p,'2099-10-20',datetime(2099,10,20,4,tzinfo=studio.ZONE));action.assert_not_called()
 def test_invalid_budget_never_creates_plan(self):
  v=self.payload();v['task_budget_cny']=float('nan')
  with self.assertRaises(ValueError):studio.save_plan(v)
  self.assertEqual(studio.plans(),[])
 def test_scoped_budget_rejects_before_api_and_releases_reservation(self):
  root=self.root/'one';root.mkdir()
  atomic_json(root/'job.json',{'job_id':'fixture','date':'2026-10-19','studio_plan_id':'p','budget_limits':{'task_budget_cny':0.000001,'article_budget_cny':0.1}})
  b=runtime.SharedBudget(root)
  with self.assertRaises(BudgetExceeded):b.reserve({'messages':[{'role':'user','content':'fixture'}],'max_tokens':10},root/'call',{'date':'2026-10-19','category':'排行类','number':1},'writer')
  self.assertEqual(b.db.execute('select count(*) from costs').fetchone()[0],0);b.db.close()
 def test_separate_jobs_keep_article_caps_but_share_task_budget(self):
  payload={'messages':[{'role':'user','content':'fixture'}],'max_tokens':10};meta={'date':'2026-10-19','category':'排行类','number':1}
  roots=[self.root/'job1',self.root/'job2']
  for i,root in enumerate(roots):
   atomic_json(root/'job.json',{'job_id':str(i),'date':'2026-10-19','studio_plan_id':'same','budget_limits':{'task_budget_cny':0.001,'article_budget_cny':0.0008}})
  first=runtime.SharedBudget(roots[0]);first.reserve(payload,roots[0]/'first',meta,'writer');first.db.close()
  second=runtime.SharedBudget(roots[1])
  with self.assertRaises(BudgetExceeded):second.reserve(payload,roots[1]/'second',meta,'writer')
  self.assertEqual(second.db.execute('select count(*) from costs').fetchone()[0],1);second.db.close()
 def test_exhausted_article_does_not_consume_another_articles_allowance(self):
  from geo_source_cards.api_budget import ArticleBudgetExceeded
  root=self.root/'article-scope'
  atomic_json(root/'job.json',{'job_id':'article-scope','date':'2026-10-19','studio_plan_id':'same','budget_limits':{'task_budget_cny':1,'article_budget_cny':0.0008}})
  payload={'messages':[{'role':'user','content':'fixture'}],'max_tokens':10};meta={'date':'2026-10-19','category':'排行类','number':1}
  b=runtime.SharedBudget(root);b.reserve(payload,root/'first',meta,'writer')
  with self.assertRaises(ArticleBudgetExceeded):b.reserve(payload,root/'retry',meta,'writer')
  b.reserve(payload,root/'second',{**meta,'number':2},'writer')
  self.assertEqual(b.db.execute('select count(*) from costs').fetchone()[0],2);b.db.close()
 def test_package_has_task_date_category_provenance_logs_and_original_word(self):
  root=runtime.SHARED;folder=root/'approved/2026-10-19/排行类/01';folder.mkdir(parents=True)
  (folder/'draft.md').write_text('# 测试文章\n直接面向读者的正文',encoding='utf8');original=b'PK-test-original-word';(folder/'article.docx').write_bytes(original)
  atomic_json(folder/'provenance.json',{'primary_reference':{'primary_url':'https://example.org/original','primary_title':'原文标题'}})
  atomic_json(folder/'category.json',{'source_urls':['https://example.org/original']})
  atomic_json(root/'days/2026-10-19/product.json',{'name':'产品甲','brand':'品牌甲'})
  atomic_json(root/'days/2026-10-19/sources.json',[{'url':'https://example.org/original','article':{'author':'作者甲','site_name':'来源媒体'}}])
  atomic_json(folder/'receipt.json',{'status':'accepted_for_user_review','files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.iterdir()}})
  path=runtime.download('legacy-original','2026-10-19/排行类/01','package')
  with zipfile.ZipFile(path) as z:
   names=z.namelist();self.assertTrue(any('历史创作任务_2026-10-19/排行类/' in n for n in names))
   word=next(n for n in names if n.endswith('.docx'));self.assertEqual(z.read(word),original)
   m=json.loads(z.read(next(n for n in names if n.endswith('文章信息.json'))));self.assertEqual(m['primary_reference']['author'],'作者甲');self.assertIn('未核实',m['primary_reference']['official_account'])
   self.assertTrue(any(n.endswith('执行日志.json') for n in names));self.assertTrue(any(n.endswith('审核与溯源/provenance.json') for n in names))
   self.assertEqual(json.loads(z.read('导出清单.json'))['count'],1)
  # A legacy acceptance receipt cannot bypass the newly required argument gate.
  atomic_json(root/'logic_policy.json',{'required':True})
  self.assertEqual(runtime.articles(root)[0]['quality_status'],'needs_revision')
  for kind in ('word','markdown','package'):
   with self.assertRaises(ValueError):runtime.download('legacy-original','2026-10-19/排行类/01',kind)
  with self.assertRaises(ValueError):runtime.download('legacy-original','','bundle')

 def test_remaining_budget_is_readonly_and_tracks_the_original_article_scope(self):
  root=self.root/'headroom';atomic_json(root/'job.json',{'job_id':'headroom','date':'2026-10-19','studio_plan_id':'p',
    'budget_limits':{'task_budget_cny':1,'article_budget_cny':.1}})
  b=runtime.SharedBudget(root);meta={'date':'2026-10-19','category':'排行类','number':1}
  b.reserve({'messages':[{'role':'user','content':'fixture'}],'max_tokens':100},root/'call',meta,'writer')
  count=b.db.execute('select count(*) from costs').fetchone()[0]
  own=b.remaining(meta,'review');other=b.remaining({**meta,'number':2},'review')
  self.assertLess(own,other);self.assertLessEqual(own,.1)
  self.assertEqual(b.db.execute('select count(*) from costs').fetchone()[0],count);b.db.close()


if __name__=='__main__':unittest.main()
