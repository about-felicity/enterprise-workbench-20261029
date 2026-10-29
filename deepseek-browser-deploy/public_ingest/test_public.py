import hashlib,importlib.util,json,tempfile,unittest,sys
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('gateway',ROOT/'gateway.py');g=importlib.util.module_from_spec(s);s.loader.exec_module(g)
sys.path.insert(0,str(ROOT.parent/'public_client'))
from remote_sync import RemoteSync
class Tests(unittest.TestCase):
 def test_scoped_auth_and_envelope(self):
  token='x'*32;c={'id':'desktop-a','enabled':True,'token_sha256':hashlib.sha256(token.encode()).hexdigest()}
  self.assertEqual(g.authorize('Bearer '+token,[c]),c);self.assertIsNone(g.authorize('Bearer '+('y'*32),[c]));self.assertIsNone(g.authorize('Bearer '+token,[{**c,'enabled':False}]))
  record={'collector_client_id':c['id'],'prompt':'问题','reply':'完整正文'*30,'body_capture_complete':True,'source_capture_complete':True,'sources':[]}
  rid=hashlib.sha256(('deepseek\ndeepseek-browser-extension\n'+json.dumps(record,ensure_ascii=False,sort_keys=True,separators=(',',':'))).encode()).hexdigest()
  env={'model':'deepseek','source_device':'deepseek-browser-extension','record':record,'request_id':rid}
  self.assertEqual(g.validate(env,c)[0],rid)
  for bad in [{**env,'model':'yuanbao'},{**env,'request_id':'0'*64},{**env,'source_device':'other'}]:
   with self.assertRaises(ValueError):g.validate(bad,c)
  with self.assertRaises(ValueError):g.validate(env,{**c,'id':'desktop-b'})
 def test_enroll_idempotent_revocation(self):
  with tempfile.TemporaryDirectory() as tmp,patch.object(g,'ROOT',Path(tmp)):
   token='e'*32;p=Path(tmp)/'clients.json';p.write_text(json.dumps({'enrollment_enabled':True,'enrollment_sha256':hashlib.sha256(token.encode()).hexdigest(),'derive_secret':'d'*64,'clients':[]}))
   a=g.register({'installation_id':'a'*32},'Bearer '+token);b=g.register({'installation_id':'b'*32},'Bearer '+token)
   self.assertNotEqual(a['token'],b['token']);self.assertEqual(a,g.register({'installation_id':'a'*32},'Bearer '+token))
   cfg=json.loads(p.read_text());cfg['clients'][0]['enabled']=False;p.write_text(json.dumps(cfg))
   self.assertTrue(g.register({'installation_id':'a'*32},'Bearer '+token)['revoked']);self.assertIsNone(g.register({'installation_id':'c'*32},'Bearer '+('f'*32)))
 def test_tls_and_offline_queue(self):
  self.assertEqual(RemoteSync._urls({'receiver_url':'http://example.com'}),[])
  self.assertEqual(RemoteSync._urls({'receiver_url':'https://user:password@example.com'}),[])
  self.assertEqual(RemoteSync._urls({'receiver_url':'https://1any.top/geo_monitor/collector/deepseek'}),['https://1any.top/geo_monitor/collector/deepseek'])
  with tempfile.TemporaryDirectory() as tmp:
   sync=RemoteSync(Path(tmp),lambda e:e);cfg={'enabled':True,'receiver_url':'https://1any.top/geo_monitor/collector/deepseek','client_id':'desktop-test','token':''}
   with patch.object(sync,'_config',return_value=cfg):
    sync.enqueue({'prompt':'offline','reply':'正文','result_id':'one'});self.assertEqual(len(list(sync.outbox.glob('*.json'))),1)
    saved=json.loads(next(sync.outbox.glob('*.json')).read_text());self.assertEqual(saved['record']['collector_client_id'],'desktop-test')
if __name__=='__main__':unittest.main()
