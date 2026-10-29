import base64,io,tempfile,unittest,zipfile
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo
from . import studio,materials,runtime

class StudioTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();root=Path(self.tmp.name)
  self.patches=[patch.object(studio,'ROOT',root/'studio'),patch.object(materials,'ROOT',root/'capture'),patch.object(materials,'GEO',root/'geo'),patch.object(runtime,'BASE',root/'jobs'),patch.object(runtime,'SHARED',root/'legacy')]
  for p in self.patches:p.start()
  runtime.atomic_json(materials.GEO/'daily_plan.json',{'time':'05:00'})
 def tearDown(self):
  for p in reversed(self.patches):p.stop()
  self.tmp.cleanup()
 def kb(self):return studio.save_product({'name':'用户产品','brand':'用户品牌','facts':['原始事实']})
 def plan(self):
  kb=self.kb();return studio.save_plan({'product_id':kb['product_id'],'questions':['问题甲','问题乙'],'channels':['deepseek','baidu_ai'],'capture_time':'01:00','writing_time':'04:00','start_date':'2099-10-17','enabled':True,'rounds':1,'max_per_category':1})
 def test_word_import_preserves_original_bytes_and_table_paragraphs(self):
  buf=io.BytesIO()
  with zipfile.ZipFile(buf,'w') as z:z.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>产品知识</w:t></w:r></w:p><w:tbl><w:tr><w:tc><w:p><w:r><w:t>规格200ml</w:t></w:r></w:p></w:tc></w:tr></w:tbl></w:body></w:document>')
  result=studio.import_word({'filename':'资料.docx','content_base64':base64.b64encode(buf.getvalue()).decode()})
  self.assertEqual(result['text'],'产品知识\n规格200ml')
  self.assertEqual((studio.ROOT/'imports'/result['import_id']/'source.docx').read_bytes(),buf.getvalue())
  kb=studio.save_product({'name':'产品','facts':result['text'].splitlines(),'import_id':result['import_id']})
  self.assertFalse(studio.product(kb['product_id'])['product']['facts'][0]['independently_verified'])
 def test_invalid_word_and_invalid_plan_do_not_enable_tasks(self):
  with self.assertRaises(ValueError):studio.import_word({'filename':'bad.doc','content_base64':'AA=='})
  with self.assertRaises(ValueError):studio.import_word({'filename':'bad.docx','content_base64':'AA=='})
  kb=self.kb()
  with self.assertRaises(ValueError):studio.save_plan({'product_id':kb['product_id'],'questions':['重复','重复']})
  self.assertEqual(studio.plans(),[])
 def test_plan_product_is_versioned_and_geo_settings_untouched(self):
  original=(materials.GEO/'daily_plan.json').read_bytes();pid=self.plan()['plan_id'];p=studio.plan(pid)
  studio.save_product({'product_id':p['product_id'],'name':'修改后的产品','facts':['新事实']})
  self.assertEqual(studio.plan(pid)['product']['name'],'用户产品')
  self.assertEqual((materials.GEO/'daily_plan.json').read_bytes(),original)
  self.assertNotEqual(studio.capture_root(pid),materials.ROOT)
 def test_capture_and_time_gates_then_each_question_enqueues_once(self):
  p=studio.plan(self.plan()['plan_id']);now=datetime(2099,10,17,3,tzinfo=ZoneInfo('Asia/Shanghai'))
  progress=[{'id':'deepseek','completed':2},{'id':'baidu_ai','completed':1}]
  with patch.object(materials,'progress',return_value=progress),patch.object(runtime,'action') as enqueue:
   studio.advance(p,'2099-10-17',now.replace(hour=5));enqueue.assert_not_called()
  progress[1]['completed']=2
  with patch.object(materials,'progress',return_value=progress),patch.object(runtime,'action',side_effect=[{'job_id':'one'},{'job_id':'two'}]) as enqueue:
   studio.advance(p,'2099-10-17',now);enqueue.assert_not_called()
   studio.advance(p,'2099-10-17',now.replace(hour=4));self.assertEqual(enqueue.call_count,2)
   studio.advance(p,'2099-10-17',now.replace(hour=6));self.assertEqual(enqueue.call_count,2)
   self.assertTrue(all(c.args[1]['studio_plan_id']==p['plan_id'] for c in enqueue.call_args_list))
 def test_enqueue_error_is_durable_and_not_retried_without_operator(self):
  p=studio.plan(self.plan()['plan_id']);progress=[{'id':m,'completed':2} for m in p['channels']]
  with patch.object(materials,'progress',return_value=progress),patch.object(runtime,'action',side_effect=ValueError('余额不可用')) as enqueue:
   studio.advance(p,'2099-10-17',datetime(2099,10,17,4,tzinfo=ZoneInfo('Asia/Shanghai')))
   studio.advance(p,'2099-10-17',datetime(2099,10,17,5,tzinfo=ZoneInfo('Asia/Shanghai')))
   self.assertEqual(enqueue.call_count,1)
  self.assertIn('余额不可用',runtime.read(studio.day_path(p['plan_id'],'2099-10-17'))['error'])
 def test_initialize_keeps_capture_schedule_and_does_not_enable_paid_writing(self):
  runtime.atomic_json(runtime.SHARED/'product.json',{'name':'旧产品','facts':[]});runtime.atomic_json(materials.ROOT/'settings.json',{'enabled':True,'time':'01:00','start_date':'2099-10-17','questions':['原问题']})
  before=(materials.ROOT/'settings.json').read_bytes();studio.initialize();studio.initialize()
  self.assertEqual(len(studio.plans()),1);self.assertFalse(studio.plans()[0]['enabled'])
  self.assertEqual((materials.ROOT/'settings.json').read_bytes(),before)

 def test_pause_arriving_between_questions_is_preserved_and_prevents_enqueue(self):
  p=studio.plan(self.plan()['plan_id']);progress=[{'id':m,'completed':2} for m in p['channels']]
  def first(*args):
   path=studio.day_path(p['plan_id'],'2099-10-17');task=runtime.read(path);task['paused']=True;runtime.atomic_json(path,task)
   return {'job_id':'one'}
  with patch.object(materials,'progress',return_value=progress),patch.object(runtime,'action',side_effect=first) as enqueue:
   studio.advance(p,'2099-10-17',datetime(2099,10,17,4,tzinfo=ZoneInfo('Asia/Shanghai')))
   self.assertEqual(enqueue.call_count,1)
  self.assertTrue(runtime.read(studio.day_path(p['plan_id'],'2099-10-17'))['paused'])

 def test_cross_midnight_capture_keeps_unfinished_original_batch(self):
  runtime.atomic_json(materials.ROOT/'days/2099-10-16/config.json',{'questions':['甲'],'channels':['deepseek'],'rounds':1})
  with patch.object(materials,'progress',return_value=[{'id':'deepseek','completed':0}]):
   self.assertEqual(materials.next_day({},'2099-10-17'),'2099-10-16')
   self.assertEqual(materials.next_day({'paused_day':'2099-10-16'},'2099-10-17'),'2099-10-17')

 def test_daily_product_and_questions_follow_capture_snapshot_after_plan_edit(self):
  p=studio.plan(self.plan()['plan_id']);cfg={'questions':p['questions'],'channels':p['channels'],'rounds':1,'studio_plan':p}
  runtime.atomic_json(studio.capture_root(p['plan_id'])/'days/2099-10-17/config.json',cfg)
  changed={**p,'questions':['后改的问题'],'product':{'name':'后改的产品'}}
  task=studio.ensure_day(changed,'2099-10-17')
  self.assertEqual(task['plan']['questions'],p['questions']);self.assertEqual(task['plan']['product']['name'],'用户产品')

if __name__=='__main__':unittest.main()
