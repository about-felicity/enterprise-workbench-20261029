import base64,io,zipfile
from unittest.mock import patch
from .test_studio import StudioTests
from . import knowledge_library as lib,studio,runtime

class LibraryTests(StudioTests):
 def upload(self,**extra):
  buf=io.BytesIO()
  text=extra.pop('_text','测试产品，规格200ml。')
  with zipfile.ZipFile(buf,'w') as z:z.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>'+text+'</w:t></w:r></w:p></w:body></w:document>')
  with patch('creation.knowledge.analyze',side_effect=AssertionError('Upload must not analyze')):
   return lib.upload({'filename':'测试资料.docx','content_base64':base64.b64encode(buf.getvalue()).decode(),'name':'测试产品','notes':'新资料',**extra})
 def publish(self,u,**extra):return lib.publish({**u,'reviewer':'人工验收','product':{'name':'测试产品','brand':'测试品牌','facts':['规格200ml']},**extra})
 def test_upload_is_durable_pending_and_not_selectable(self):
  u=self.upload();r=lib.record(u['library_id']);item=r['uploads'][0]
  self.assertEqual(studio.products(),[]);self.assertEqual(item['status'],'pending');self.assertGreater(item['bytes'],0);self.assertGreater(item['uploaded_at'],0)
  e=runtime.read(studio.ROOT/'imports'/u['import_id']/'extraction.json');self.assertIsNone(e['analysis']);self.assertIn('200ml',e['text'])
 def test_review_publish_and_update_preserve_previous_versions(self):
  u=self.upload();p=self.publish(u);old=studio.product(p['product_id'])
  self.assertEqual(lib.record(u['library_id'])['uploads'][0]['status'],'published')
  newer=self.upload(product_id=p['product_id'],_text='新版测试产品，规格300ml。');self.assertEqual(studio.product(p['product_id']),old)
  with self.assertRaises(ValueError):self.publish(newer,expected_version='outdated')
  result=self.publish(newer,expected_version=p['version']);self.assertEqual(result['product_id'],p['product_id'])
  self.assertEqual(len(studio.products()),1);self.assertEqual(len(lib.record(u['library_id'])['uploads']),2)
  self.assertTrue((studio.ROOT/'versions'/p['product_id']/(p['version']+'.json')).exists())
 def test_latest_upload_only_and_no_duplicate_publish(self):
  u=self.upload();newer=self.upload(library_id=u['library_id'],_text='新版测试产品，规格300ml。')
  with self.assertRaises(ValueError):self.publish(u)
  p=self.publish(newer);self.publish(newer);self.assertEqual(len(studio.products()),1)
  self.assertEqual(lib.record(u['library_id'])['product_id'],p['product_id'])
 def test_manual_edit_detects_stale_version(self):
  p=self.publish(self.upload());body={'product_id':p['product_id'],'expected_version':p['version'],'name':'产品新名称','facts':['规格300ml']}
  changed=lib.edit(body);self.assertNotEqual(changed['version'],p['version'])
  with self.assertRaises(ValueError):lib.edit(body)
 def test_upload_invalid_target_does_not_store_file(self):
  with self.assertRaises(ValueError):self.upload(product_id='product-'+'a'*32)
  self.assertFalse((studio.ROOT/'imports').exists())
 def test_existing_task_keeps_version_after_manual_publication(self):
  p=self.publish(self.upload());body={'product_id':p['product_id'],'questions':['问题甲'],'channels':['baidu_ai'],'capture_time':'01:00','writing_time':'04:00','start_date':'2099-10-17','enabled':False,'rounds':1,'max_per_category':1}
  task=studio.save_plan(body);before=studio.plan(task['plan_id'])
  u=self.upload(product_id=p['product_id'],_text='新版测试产品，规格300ml。');self.publish(u,expected_version=p['version'],product={'name':'新版产品','facts':['规格300ml']})
  self.assertEqual(studio.plan(task['plan_id']),before)
  new=studio.plan(studio.save_plan(body)['plan_id']);self.assertNotEqual(new['product_version'],before['product_version']);self.assertEqual(new['product']['facts'][0]['text'],'规格300ml')
