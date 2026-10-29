"""Loopback ingest gateway: per-client DeepSeek-only keys, never dashboard access."""
import hashlib,hmac,json,re,threading,urllib.request,urllib.error
from pathlib import Path
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlsplit
ROOT=Path('/opt/monitor/geo-capture/public_ingest')
MAX_BODY=5*1024*1024
SLOTS=threading.BoundedSemaphore(4)
REGISTRY_LOCK=threading.Lock()

def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def authorize(value,clients):
 token=value[7:] if value.startswith('Bearer ') else ''
 if not 24<=len(token)<=256:return None
 digest=hashlib.sha256(token.encode()).hexdigest()
 for c in clients:
  if c.get('enabled') and hmac.compare_digest(digest,c.get('token_sha256','')):return c
 return None

def register(value,header):
 if not isinstance(value,dict) or not re.fullmatch('[a-f0-9]{32}',str(value.get('installation_id',''))):raise ValueError('invalid_device')
 with REGISTRY_LOCK:
  path=ROOT/'clients.json';cfg=read(path)
  supplied=header[7:] if header.startswith('Bearer ') else ''
  if not cfg.get('enrollment_enabled') or not 24<=len(supplied)<=256 or not hmac.compare_digest(hashlib.sha256(supplied.encode()).hexdigest(),cfg.get('enrollment_sha256','')):return None
  identity='desktop-'+value['installation_id']
  token=hmac.new(bytes.fromhex(cfg['derive_secret']),identity.encode(),hashlib.sha256).hexdigest()
  existing=next((c for c in cfg['clients'] if c['id']==identity),None)
  if existing and not existing['enabled']:return {'revoked':True}
  if not existing:
   cfg['clients'].append({'id':identity,'enabled':True,'token_sha256':hashlib.sha256(token.encode()).hexdigest()})
   tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(cfg));tmp.chmod(0o600);tmp.replace(path)
  return {'client_id':identity,'token':token}

def validate(value,client):
 if not isinstance(value,dict) or value.get('model')!='deepseek' or value.get('source_device')!='deepseek-browser-extension':raise ValueError('invalid_model_or_device')
 record=value.get('record');rid=value.get('request_id','')
 if not isinstance(record,dict) or not isinstance(rid,str) or not re.fullmatch('[a-f0-9]{64}',rid):raise ValueError('invalid_envelope')
 client_id=record.get('collector_client_id')
 if client_id and client_id!=client['id']:raise ValueError('client_identity_mismatch')
 raw=json.dumps(record,ensure_ascii=False,sort_keys=True,separators=(',',':'))
 expected=hashlib.sha256(('deepseek\ndeepseek-browser-extension\n'+raw).encode()).hexdigest()
 if not hmac.compare_digest(expected,rid):raise ValueError('request_identity_mismatch')
 body=str(record.get('web_body') or record.get('reply') or record.get('answer') or '').strip()
 prompt=str(record.get('prompt') or record.get('question') or '').strip()
 sources=record.get('sources',[])
 if not prompt or len(prompt)>2000 or len(body)<60 or record.get('status','success')!='success' or record.get('source_capture_complete') is not True or record.get('body_capture_complete') is not True:raise ValueError('incomplete_answer')
 if not isinstance(sources,list) or len(sources)>1000 or len(sources)<int(record.get('expected_source_count',0)):raise ValueError('incomplete_sources')
 for source in sources:
  u=urlsplit(str(source.get('href') or source.get('url') or ''))
  if u.scheme not in ('http','https') or not u.hostname or u.username or u.password:raise ValueError('invalid_source_url')
 return rid,body,sources

class NoRedirect(urllib.request.HTTPRedirectHandler):
 def redirect_request(self,*args,**kwargs):return None

class Handler(BaseHTTPRequestHandler):
 protocol_version='HTTP/1.1'
 def log_message(self,*args):pass
 def reply(self,status,value):
  raw=json.dumps(value,ensure_ascii=False).encode();self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store');self.send_header('Connection','close');self.end_headers();self.wfile.write(raw);self.close_connection=True
 def do_GET(self):
  if self.path=='/api/v1/health':return self.reply(200,{'ok':True,'service':'deepseek-public-ingest'})
  self.reply(404,{'ok':False,'error':'not_found'})
 def do_POST(self):
  if self.path=='/api/v1/register':
   if self.headers.get('Origin'):return self.reply(403,{'ok':False,'error':'browser_origin_not_supported'})
   try:
    n=int(self.headers.get('Content-Length','0'))
    if not 0<n<=16000:return self.reply(413,{'ok':False,'error':'invalid_size'})
    self.connection.settimeout(10);value=json.loads(self.rfile.read(n));result=register(value,self.headers.get('Authorization',''))
    if not result:return self.reply(401,{'ok':False,'error':'unauthorized'})
    if result.get('revoked'):return self.reply(403,{'ok':False,'error':'device_revoked'})
    return self.reply(200,{'ok':True,**result})
   except (ValueError,TypeError):return self.reply(400,{'ok':False,'error':'invalid_device'})
   except Exception:return self.reply(503,{'ok':False,'error':'registration_unavailable'})
  if self.path not in ['/api/v1/models/deepseek/results','/api/v1/models/deepseek/validate']:return self.reply(404,{'ok':False,'error':'not_found'})
  try:client=authorize(self.headers.get('Authorization',''),read(ROOT/'clients.json')['clients'])
  except Exception:return self.reply(503,{'ok':False,'error':'auth_unavailable'})
  if not client:return self.reply(401,{'ok':False,'error':'unauthorized'})
  if self.headers.get('Origin'):return self.reply(403,{'ok':False,'error':'browser_origin_not_supported'})
  if not SLOTS.acquire(blocking=False):return self.reply(429,{'ok':False,'error':'busy_retry_later'})
  try:
   if self.headers.get('Content-Type','').split(';')[0]!='application/json':return self.reply(415,{'ok':False,'error':'json_required'})
   n=int(self.headers.get('Content-Length','0'))
   if not 0<n<=MAX_BODY:return self.reply(413,{'ok':False,'error':'body_too_large'})
   self.connection.settimeout(15);value=json.loads(self.rfile.read(n));rid,body,sources=validate(value,client)
   if self.path.endswith('/validate'):return self.reply(200,{'ok':True,'request_id':rid,'status':'validated','client_id':client['id']})
   upstream=read('/opt/monitor/runtime/lan_result_receiver.json')
   req=urllib.request.Request('http://127.0.0.1:'+str(int(upstream['port']))+'/api/v1/models/deepseek/results',data=json.dumps(value,ensure_ascii=False).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+upstream['token']})
   opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),NoRedirect())
   with opener.open(req,timeout=12) as response:result=json.load(response)
   if not result.get('ok') or result.get('request_id')!=rid or result.get('status') not in ('queued','processed'):raise RuntimeError('upstream_unconfirmed')
   if result['status']=='processed':
    receipt=read(Path('/opt/monitor/runtime/lan_result_receiver/deepseek/done')/(rid+'.json'));a=receipt.get('analysis',{})
    if receipt.get('request_id')!=rid or not receipt.get('stored_run_id') or a.get('quarantined') is True or a.get('answer_length')!=len(body) or a.get('source_count')!=len(sources) or a.get('source_capture_complete') is not True:return self.reply(422,{'ok':False,'error':'receipt_needs_review','request_id':rid})
   self.reply(200 if result['status']=='processed' else 202,{'ok':True,'request_id':rid,'status':result['status'],'client_id':client['id']})
  except (ValueError,TypeError,KeyError,json.JSONDecodeError):self.reply(400,{'ok':False,'error':'invalid_capture'})
  except Exception:self.reply(503,{'ok':False,'error':'upstream_unavailable_retry_same_request'})
  finally:SLOTS.release()

if __name__=='__main__':ThreadingHTTPServer(('127.0.0.1',8811),Handler).serve_forever()
