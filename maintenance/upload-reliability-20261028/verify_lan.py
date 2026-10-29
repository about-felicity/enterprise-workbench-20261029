"""Real LAN/public HTTP uploads with disposable fixtures; never creates writing jobs."""
import sys,os,json,io,zipfile,base64,uuid,hashlib,time,urllib.request,http.cookiejar,subprocess,shlex,shutil,gzip
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
sys.path.insert(0,'/home/user/geo-editorial/venv/lib/python3.10/site-packages')
from PIL import Image
root=Path('/opt/monitor/geo-content/studio');report=Path('/opt/monitor/geo-content/maintenance/upload-reliability-20261028')
read=lambda p:json.loads(p.read_text())
original_ids={p.parent.name for p in (root/'images').glob('image-*/metadata.json')}
def vps(code):
 args=['ssh','-i','/etc/monitor-vps2-tunnel/id_ed25519','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile=/etc/monitor-vps2-tunnel/known_hosts','-o','ConnectTimeout=10','root@117.55.234.72','python3 -c '+shlex.quote(code)]
 r=subprocess.run(args,capture_output=True,text=True,timeout=35)
 if r.returncode:raise RuntimeError('Test session unavailable')
 return r.stdout.strip()
token=vps("""import ast
from pathlib import Path
p=Path('/opt/geo-monitor-auth/server.py');tree=ast.parse(p.read_text())
def listener(n):return isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Attribute) and n.value.func.attr=='serve_forever'
assert sum(listener(n) for n in tree.body)==1
tree.body=[n for n in tree.body if not listener(n)];ns={'__name__':'upload_verification'};exec(compile(tree,str(p),'exec'),ns);ns['SESSION_SECONDS']=600
print(ns['make_token'](next(iter(ns['users']()))))""")
class Client:
 def __init__(self,public=False):
  self.base='https://1any.top/geo_monitor/api/geo-creation/' if public else 'http://127.0.0.1:3000/api/geo-creation/'
  self.origin='https://1any.top' if public else 'http://127.0.0.1:3000'
  jar=http.cookiejar.CookieJar()
  if public:jar.set_cookie(http.cookiejar.Cookie(0,'geo_monitor_session',token,None,False,'1any.top',False,False,'/geo_monitor/',True,True,None,True,None,None,{},False))
  self.op=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPCookieProcessor(jar))
  begin=time.monotonic()
  with self.op.open(urllib.request.Request(self.base+'uploads',headers={'Accept-Encoding':'gzip'}),timeout=90) as response:
   raw=response.read();state=json.loads(gzip.decompress(raw) if response.headers.get('Content-Encoding')=='gzip' else raw)
  self.csrf=state['csrf'];self.state_seconds=round(time.monotonic()-begin,3)
 def post(self,name,payload,key=None):
  body=json.dumps(payload).encode();req=urllib.request.Request(self.base+'control/'+name,data=body,headers={'Content-Type':'application/json','Origin':self.origin,'X-CSRF-Token':self.csrf,'X-Action-Id':key or uuid.uuid4().hex})
  begin=time.monotonic()
  with self.op.open(req,timeout=300) as response:
   result=json.load(response);assert result['ok'];return result['result'],round(time.monotonic()-begin,3)

result={};library=None
try:
 lan=Client();public=Client();result['lightweight_seconds']={'lan':lan.state_seconds,'public':public.state_seconds}
 buf=io.BytesIO()
 with zipfile.ZipFile(buf,'w') as z:z.writestr('word/document.xml','<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Temporary upload verification only.</w:t></w:r></w:p></w:body></w:document>')
 library,_=lan.post('kb_upload',{'name':'临时上传验收-'+uuid.uuid4().hex,'filename':'upload-verification.docx','content_base64':base64.b64encode(buf.getvalue()).decode()})
 def image_body(size):
  b=io.BytesIO();Image.frombytes('RGB',(size,size),os.urandom(size*size*3)).save(b,'PNG');return b.getvalue()
 large=image_body(1000);assert len(large)>2*1024*1024
 payload={'library_id':library['library_id'],'filename':'public-large-verification.png','content_base64':base64.b64encode(large).decode()}
 uploaded,seconds=public.post('product_image_upload',payload);result['lan_large']={'bytes':len(large),'seconds':seconds,'ok':True};print(json.dumps({'lan_large':result['lan_large']}),flush=True)
 duplicate,_=public.post('product_image_upload',payload);assert duplicate['image_id']==uploaded['image_id'] and duplicate['reused'];result['duplicate_safe']=True
 with public.op.open(public.base+'product_image?id='+uploaded['image_id'],timeout=30) as response:assert hashlib.sha256(response.read()).digest()==hashlib.sha256(large).digest()
 result['original_download_sha_match']=True
 def parallel(n):
  client=Client();raw=image_body(25+n)
  r,t=client.post('product_image_upload',{'library_id':library['library_id'],'filename':'parallel-'+str(n)+'.png','content_base64':base64.b64encode(raw).decode()})
  return {'id':r['image_id'],'seconds':t}
 with ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(parallel,range(4)))
 assert len({r['id'] for r in rows})==4;result['lan_four_sessions']=rows
 result['ok']=True
finally:
 if library:
  lid=library['library_id'];assert lid.startswith('library-')
  archive=report/'qa-artifacts';archive.mkdir(exist_ok=True)
  for p in (root/'images').glob('image-*/metadata.json'):
   if read(p).get('library_id')==lid:
    assert p.parent.name not in original_ids;shutil.move(str(p.parent),str(archive/p.parent.name))
  p=root/'library'/(lid+'.json');r=read(p);assert r['name'].startswith('临时上传验收-')
  for upload in r['uploads']:
   p2=root/'imports'/upload['import_id'];assert p2.parent==root/'imports';shutil.move(str(p2),str(archive/p2.name))
  shutil.move(str(p),str(archive/p.name))
  assert original_ids=={p.parent.name for p in (root/'images').glob('image-*/metadata.json')}
  result['temporary_data_removed']=True
 (report/'lan-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
 print(json.dumps(result,ensure_ascii=False))
