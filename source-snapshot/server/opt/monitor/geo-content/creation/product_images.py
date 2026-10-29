"""Original product image uploads, associated with a product or pending library."""
import base64,hashlib,io,time,warnings,os,tempfile
from PIL import Image
from . import studio,runtime,knowledge_library

def images():
 return sorted([runtime.read(p) for p in (studio.ROOT/'images').glob('image-*/metadata.json')],key=lambda r:r['uploaded_at'],reverse=True)

def upload(payload):
 pid=payload.get('product_id','');lid=payload.get('library_id','')
 if bool(pid)==bool(lid):raise ValueError('请先选择产品；新增产品请先上传知识库，再上传图片')
 if pid:studio.product(pid)
 else:
  record=knowledge_library.record(lid)
  pid=record.get('product_id','');lid='' if pid else record['library_id']
 name=payload.get('filename','')
 if not isinstance(name,str) or not name:raise ValueError('图片文件名不正确')
 try:body=base64.b64decode(payload.get('content_base64',''),validate=True)
 except Exception:raise ValueError('图片编码不正确')
 if not 0<len(body)<=5*1024*1024:raise ValueError('每张图片须为5MB以内')
 try:
  with warnings.catch_warnings():
   warnings.simplefilter('error',Image.DecompressionBombWarning)
   with Image.open(io.BytesIO(body)) as image:
    fmt=image.format;width,height=image.size
    if fmt not in {'JPEG','PNG','WEBP'} or width*height>25_000_000 or getattr(image,'is_animated',False):raise ValueError('支持静态 JPG、PNG、WebP，最多2500万像素')
    image.verify()
 except ValueError:raise
 except Exception:raise ValueError('图片无法读取，请选择有效的 JPG、PNG 或 WebP 文件')
 digest=hashlib.sha256(body).hexdigest();target=pid or lid
 with runtime.process_lock(studio.ROOT/'image-locks'/(target+'.lock'),blocking=True):
  if lid and knowledge_library.record(lid).get('product_id'):
   return upload(payload) # A concurrent library merge changed the canonical target.
  related={r['library_id'] for r in knowledge_library.records() if pid and r.get('product_id')==pid}
  existing=next((r for r in images() if r.get('sha256')==digest and
      ((pid and r.get('product_id')==pid) or (lid and r.get('library_id')==lid) or r.get('library_id') in related)
      and (studio.ROOT/'images'/r['image_id']/'original').is_file()),None)
  if existing:return {'image_id':existing['image_id'],'image':existing,'reused':True,'message':'该图片已上传，已复用原图。'}
  # Deterministic identity also recovers a crash after writing bytes but before
  # recording the operation receipt. Identical bytes on another product stay separate.
  ident='image-'+hashlib.sha256((target+':'+digest).encode()).hexdigest()[:32]
  folder=studio.ROOT/'images'/ident;folder.mkdir(parents=True,exist_ok=True)
  atomic_bytes(folder/'original',body)
  result={'image_id':ident,'product_id':pid,'library_id':lid,'filename':name.replace('\\','/').rsplit('/',1)[-1][:180],'bytes':len(body),'width':width,'height':height,'mime':{'JPEG':'image/jpeg','PNG':'image/png','WEBP':'image/webp'}[fmt],'sha256':digest,'uploaded_at':time.time()}
  runtime.atomic_json(folder/'metadata.json',result)
  return {'image_id':ident,'image':result,'reused':False,'message':'图片已保存，可立即预览。'}

def atomic_bytes(path,body):
 fd,temp=tempfile.mkstemp(prefix='.image-',dir=path.parent)
 try:
  with os.fdopen(fd,'wb') as f:f.write(body)
  os.chmod(temp,0o600);os.replace(temp,path)
 finally:
  if os.path.exists(temp):os.unlink(temp)

def read(ident,thumbnail=False):
 studio.identity(ident,'image');folder=studio.ROOT/'images'/ident;meta=runtime.read(folder/'metadata.json')
 if not meta:raise ValueError('图片不存在')
 body=(folder/'original').read_bytes()
 if thumbnail:
  with Image.open(io.BytesIO(body)) as image:
   from PIL import ImageOps
   image=ImageOps.exif_transpose(image);image.thumbnail((360,280))
   out=io.BytesIO();image.convert('RGB').save(out,format='JPEG',quality=82)
   return out.getvalue(),'image/jpeg'
 return body,meta['mime']
