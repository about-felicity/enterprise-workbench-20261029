import base64,io,threading,uuid,unittest,zipfile
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from PIL import Image
from .test_studio import StudioTests
from . import runtime,studio,product_images,knowledge_library as library

class UploadReliabilityTests(unittest.TestCase):
 setUp=StudioTests.setUp
 tearDown=StudioTests.tearDown
 def image(self,pid,color='red'):
  b=io.BytesIO();Image.new('RGB',(600,400),color).save(b,'PNG')
  return {'product_id':pid,'filename':'test.png','content_base64':base64.b64encode(b.getvalue()).decode()}
 def product(self,name='Upload product'):
  return studio.save_product({'name':name,'facts':['original fact']})['product_id']
 def word(self,name='Upload product',content='original fact'):
  b=io.BytesIO()
  with zipfile.ZipFile(b,'w') as z:z.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>'+content+'</w:t></w:r></w:p></w:body></w:document>')
  return {'name':name,'filename':'knowledge.docx','content_base64':base64.b64encode(b.getvalue()).decode()}
 def test_parallel_same_image_creates_one_file_and_receipts(self):
  payload=self.image(self.product())
  with ThreadPoolExecutor(max_workers=8) as pool:
   results=list(pool.map(lambda _:runtime.action('product_image_upload',payload,uuid.uuid4().hex),range(16)))
  self.assertEqual(len({r['image_id'] for r in results}),1)
  self.assertEqual(len(product_images.images()),1)
 def test_parallel_distinct_images_and_products(self):
  a,b=self.product('one'),self.product('two')
  payloads=[self.image(pid,color) for pid in (a,b) for color in ('red','blue','green','yellow')]
  with ThreadPoolExecutor(max_workers=8) as pool:results=list(pool.map(lambda p:runtime.action('product_image_upload',p,uuid.uuid4().hex),payloads))
  self.assertEqual(len({r['image_id'] for r in results}),8)
 def test_upload_does_not_wait_for_global_job_lock(self):
  payload=self.image(self.product())
  with runtime.process_lock(runtime.BASE/'actions.lock',blocking=True):
   with ThreadPoolExecutor(max_workers=1) as pool:
    result=pool.submit(runtime.action,'product_image_upload',payload,uuid.uuid4().hex).result(timeout=4)
  self.assertTrue(result['image_id'])
 def test_lost_receipt_reuses_saved_image_and_same_key_rejects_new_body(self):
  payload=self.image(self.product());key=uuid.uuid4().hex
  first=product_images.upload(payload) # simulate interruption before operations receipt
  replay=runtime.action('product_image_upload',payload,key)
  self.assertEqual(first['image_id'],replay['image_id']);self.assertTrue(replay['reused'])
  with self.assertRaises(ValueError):runtime.action('product_image_upload',{**payload,'filename':'changed.png'},key)
 def test_thumbnail_does_not_change_original(self):
  payload=self.image(self.product());r=product_images.upload(payload)
  original,_=product_images.read(r['image_id']);thumb,mime=product_images.read(r['image_id'],True)
  self.assertEqual(original,base64.b64decode(payload['content_base64']));self.assertEqual(mime,'image/jpeg')
  with Image.open(io.BytesIO(thumb)) as image:self.assertLessEqual(image.width,360)
 def test_new_upload_matching_product_name_updates_one_library(self):
  first=runtime.action('kb_upload',self.word(),uuid.uuid4().hex)
  second=runtime.action('kb_upload',self.word(content='new fact'),uuid.uuid4().hex)
  self.assertEqual(first['library_id'],second['library_id']);self.assertEqual(len(library.records()),1)
  self.assertEqual(len(library.record(first['library_id'])['uploads']),2)
 def test_same_word_retries_do_not_append_revisions(self):
  payload=self.word()
  with ThreadPoolExecutor(max_workers=6) as pool:results=list(pool.map(lambda _:runtime.action('kb_upload',payload,uuid.uuid4().hex),range(10)))
  self.assertEqual(len({r['library_id'] for r in results}),1)
  self.assertEqual(len(library.records()[0]['uploads']),1)
 def test_archived_library_routes_images_to_canonical_product(self):
  pid=self.product();lid='library-'+uuid.uuid4().hex;old='library-'+uuid.uuid4().hex
  runtime.atomic_json(studio.ROOT/'library'/(lid+'.json'),{'library_id':lid,'product_id':pid,'name':'product','updated_at':1,'uploads':[]})
  runtime.atomic_json(studio.ROOT/'library'/(old+'.json'),{'library_id':old,'merged_into':lid,'updated_at':1})
  p=self.image(pid);p.pop('product_id');p['library_id']=old
  image=product_images.upload(p)['image'];self.assertEqual(image['product_id'],pid);self.assertFalse(image['library_id']);self.assertEqual(len(library.records()),1)
 def test_light_snapshot_never_scans_articles(self):
  with patch.object(runtime,'status',side_effect=AssertionError('heavy status')):
   self.assertEqual(library.upload_snapshot()['products'],[])
 def test_http_multiple_sessions_upload_while_global_lock_is_held(self):
  import urllib.request,http.cookiejar,json
  from http.server import ThreadingHTTPServer
  from .service import Handler
  pid=self.product();server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
  thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
  base='http://127.0.0.1:'+str(server.server_port)
  def client(color):
   op=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
   state=json.load(op.open(base+'/api/uploads',timeout=5))
   req=urllib.request.Request(base+'/api/control/product_image_upload',data=json.dumps(self.image(pid,color)).encode(),headers={'Content-Type':'application/json','Origin':'http://127.0.0.1:8804','X-CSRF-Token':state['csrf'],'X-Action-Id':uuid.uuid4().hex})
   result=json.load(op.open(req,timeout=8));self.assertTrue(result['ok']);return result['result']['image_id']
  try:
   with runtime.process_lock(runtime.BASE/'actions.lock',blocking=True):
    with ThreadPoolExecutor(max_workers=6) as pool:results=list(pool.map(client,['red','green','blue','yellow','purple','orange']))
   self.assertEqual(len(set(results)),6)
  finally:server.shutdown();server.server_close();thread.join()
