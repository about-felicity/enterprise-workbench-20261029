import base64,hashlib,hmac,json,os,sys,tempfile,time,unittest,uuid
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'geo-monitor-deploy/server-source'))
from monitor_core import performance_store as s,performance_identity as auth

class EntryTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.env=patch.dict(os.environ,MONITOR_PERFORMANCE_DB=str(Path(self.tmp.name)/'test.sqlite'),MONITOR_PERFORMANCE_AUTH_KEY=str(Path(self.tmp.name)/'key'));self.env.start()
  Path(os.environ['MONITOR_PERFORMANCE_AUTH_KEY']).write_bytes(b'test-key'*4)
  self.product=s.template()['products'][0]['product']
 def tearDown(self):self.env.stop();self.tmp.cleanup()
 def payload(self,value=0,revision=0,field='traffic',day='2026-10-31'):
  return {'month':'2026-10','operation_id':uuid.uuid4().hex,'changes':[{'product':self.product,'field':field,'date':day,'value':value,'expected_revision':revision}]}
 def test_history_and_zero_clear_idempotency(self):
  original=s.month_config('2026-10')['products'][0]['traffic'].copy()
  p=self.payload();r=s.save(p,'superadmin');self.assertEqual(r['updated_cells'],1);self.assertEqual(s.save(p,'superadmin'),r)
  self.assertEqual(s.month_config('2026-10')['products'][0]['traffic']['2026-10-31'],0)
  s.save(self.payload(None,1),'superadmin');after=s.month_config('2026-10')['products'][0]['traffic'];self.assertIsNone(after.pop('2026-10-31'));self.assertEqual(after,original)
  self.assertEqual(len(s.editor_data('2026-10','2026-10-31')['history']),2)
 def test_conflict_atomic_and_cents(self):
  s.save(self.payload(3),'superadmin');p=self.payload(99,1);p['changes'] += self.payload(7,0,'expenses')['changes'];p['changes'][-1]['expected_revision']=4
  with self.assertRaises(s.ConflictError):s.save(p,'superadmin')
  self.assertEqual(s.month_config('2026-10')['products'][0]['traffic']['2026-10-31'],3)
  s.save(self.payload(100.25,0,'expenses'),'superadmin');self.assertEqual(s.month_config('2026-10')['products'][0]['cumulative_expenses']['2026-10-31'],100.25)
 def test_validation_and_reader(self):
  with self.assertRaises(PermissionError):s.save(self.payload(),'reader')
  for value in [-1,.1,float('nan'),True]:
   with self.assertRaises(ValueError):s.save(self.payload(value),'superadmin')
  with self.assertRaises(ValueError):s.save(self.payload(3,field='mention'),'superadmin')
  p=self.payload();p['changes'][0]['product']=s.template()['excluded_products'][0]
  with self.assertRaises(ValueError):s.save(p,'superadmin')
 def proof(self,user='superadmin',expires=None):
  cookie='test-session';payload={'u':user,'e':expires or int(time.time())+60,'s':hashlib.sha256(cookie.encode()).hexdigest()}
  data=base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=');signature=base64.urlsafe_b64encode(hmac.new(auth.key(),b'performance-v1:'+data.encode(),hashlib.sha256).digest()).decode().rstrip('=')
  headers={'Cookie':'REDACTED_CONFIGURE_LOCALLY'+cookie,'X-Geo-Performance-Identity':data+'.'+signature,'Origin':'https://1any.top','Sec-Fetch-Site':'same-origin'};headers['X-CSRF-Token']=auth.csrf(headers);return headers
 def test_identity_and_write_boundary(self):
  headers=self.proof();self.assertEqual(auth.authorize_write(headers),'superadmin')
  for altered in [dict(headers,Cookie='REDACTED_CONFIGURE_LOCALLY'),dict(headers,Origin='https://evil.test'),dict(headers,**{'X-CSRF-Token':''}),self.proof('reader'),self.proof(expires=int(time.time())-5),{'X-Geo-Performance-Identity':'superadmin'}]:
   with self.assertRaises(PermissionError):auth.authorize_write(altered)

if __name__=='__main__':unittest.main()
