import hashlib,json,tempfile,threading,unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.request import urlopen
from urllib.error import HTTPError
from .service import Handler

class DownloadTests(unittest.TestCase):
 def setUp(self):
  self.server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
  self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
  self.url='http://127.0.0.1:'+str(self.server.server_port)+'/api/download?job=all-approved&kind=bundle'
 def tearDown(self):
  self.server.shutdown();self.server.server_close();self.thread.join()
 def test_snapshot_header_hash_and_length_match_delivered_binary(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'archive.zip';payload=b'PK\x03\x04\xff\x00\x81';p.write_bytes(payload)
   with patch('creation.runtime.download',return_value=p),patch.object(Path,'read_bytes',side_effect=[payload,b'changed']) as read:
    with urlopen(self.url) as r:
     self.assertEqual(r.read(),payload);self.assertEqual(r.headers['X-Content-SHA256'],hashlib.sha256(payload).hexdigest());self.assertEqual(int(r.headers['X-Download-Bytes']),len(payload))
   self.assertEqual(read.call_count,1)
 def test_export_errors_are_json_without_attachment(self):
  with patch('creation.runtime.download',side_effect=ValueError('当前筛选没有可下载的成稿')):
   with self.assertRaises(HTTPError) as result:urlopen(self.url)
   r=result.exception;self.assertEqual(r.code,400);self.assertNotIn('Content-Disposition',r.headers);self.assertIn('没有可下载',json.loads(r.read())['message'])
