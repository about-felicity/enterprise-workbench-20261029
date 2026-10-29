"""Durable upload inbox; publication requires an explicit reviewed payload."""
import argparse,json,time,uuid,re,unicodedata,base64,hashlib
from pathlib import Path
from . import runtime,studio

def records():
 return sorted([r for p in (studio.ROOT/'library').glob('library-*.json') if not (r:=runtime.read(p)).get('merged_into')],key=lambda r:r['updated_at'],reverse=True)

def record(value,_seen=None):
 studio.identity(value,'library');r=runtime.read(studio.ROOT/'library'/(value+'.json'))
 if not r:raise ValueError('知识库上传记录不存在')
 if r.get('merged_into'):
  seen=set() if _seen is None else _seen
  if value in seen:raise ValueError('知识库关联异常')
  return record(r['merged_into'],seen|{value})
 return r

def summary():
 return records()

def name_key(name):
 return re.sub(r'[\W_]+','',unicodedata.normalize('NFKC',str(name)).casefold())

def upload_snapshot():
 from .product_images import images
 return {'products':studio.products(),'knowledge_library':summary(),'product_images':images()}

def upload(payload):
 pid=payload.get('product_id','');lid=payload.get('library_id','')
 kb=studio.product(pid) if pid else None
 previous=record(lid) if lid else next((r for r in records() if pid and r.get('product_id')==pid),None)
 if previous and pid and previous.get('product_id') not in ('',pid):raise ValueError('上传产品与记录不匹配')
 if previous and previous.get('product_id'):kb=studio.product(previous['product_id'])
 if not isinstance(payload.get('name',''),str):raise ValueError('产品名称须为文字')
 title=payload.get('name','').strip() or (kb or {}).get('product',{}).get('name') or (previous or {}).get('name') or Path(str(payload.get('filename','')).replace('\\','/')).stem
 notes=payload.get('notes','')
 if not title or len(title)>300 or not isinstance(notes,str) or len(notes)>2000:raise ValueError('请填写有效产品名称和备注（最多2000字）')
 if not str(payload.get('filename','')).lower().endswith('.docx'):raise ValueError('请上传.docx文件')
 try:body=base64.b64decode(payload.get('content_base64',''),validate=True)
 except Exception:raise ValueError('Word文件编码不正确')
 if not 0<len(body)<=5*1024*1024:raise ValueError('Word文件应小于5MB')
 file_hash=hashlib.sha256(body).hexdigest()
 # An accidental "new product" selection must not fork an existing library.
 if not previous:
  matches=[r for r in records() if name_key(title) in {name_key(r['name']),*(name_key(a) for a in r.get('aliases',[])),*(name_key(Path(u.get('filename','')).stem) for u in r.get('uploads',[]))}
           or any(u.get('sha256')==file_hash for u in r.get('uploads',[]))]
  if len(matches)>1:raise ValueError('找到多个同名产品，请明确选择要更新的产品')
  if matches:
   previous=matches[0]
   if previous.get('product_id'):kb=studio.product(previous['product_id'])
 if kb:title=kb['product']['name']
 if previous and previous.get('uploads'):
  latest=previous['uploads'][-1]
  if latest.get('sha256')==file_hash:
   return {'library_id':previous['library_id'],'import_id':latest['import_id'],'reused':True,'message':'此文件已是该产品最新知识库，无需重复上传。'}
 extraction=studio.import_word(payload,analyze_now=False)
 now=extraction['at'];r=previous or {'library_id':'library-'+uuid.uuid4().hex,'product_id':(kb or {}).get('product_id',''),'name':title,'created_at':now,'uploads':[]}
 if not previous and kb and kb.get('word_source',{}).get('import_id'):
  source=kb['word_source'];r['created_at']=source.get('at',kb['updated_at'])
  r['uploads'].append({k:source.get(k) for k in ('import_id','filename','sha256','bytes','paragraphs')})
  r['uploads'][-1].update(uploaded_at=source.get('at'),revision=1,status='published',product_version=kb['version'],notes='此前已有的知识库原文件')
 item={k:extraction[k] for k in ('import_id','filename','sha256','bytes','paragraphs')}
 item.update(uploaded_at=now,revision=len(r['uploads'])+1,status='pending',notes=notes)
 r['uploads'].append(item);r.update(updated_at=now,name=title)
 runtime.atomic_json(studio.ROOT/'library'/(r['library_id']+'.json'),r)
 return {'library_id':r['library_id'],'import_id':item['import_id'],'message':'上传已保存，等待人工分析。请告知助手分析这份资料；分析完成后即可选择该产品创建任务。'}

def publish(payload):
 r=record(payload.get('library_id',''));uid=studio.identity(payload.get('import_id',''),'upload')
 if not r['uploads'] or r['uploads'][-1]['import_id']!=uid:raise ValueError('这不是最新上传版本，请分析最新资料后发布')
 item=r['uploads'][-1]
 if item['status']=='published':return {'product_id':r['product_id'],'version':item['product_version'],'message':'该版本已经分析发布'}
 reviewer=payload.get('reviewer','').strip()
 if not reviewer or len(reviewer)>200:raise ValueError('请记录分析人')
 pid=r.get('product_id','');old=studio.product(pid) if pid else None
 fields=payload.get('product',{})
 if not isinstance(fields,dict):raise ValueError('请提供人工分析后的产品资料')
 # Recover publication interrupted after the product was written, without creating a duplicate.
 recovered=next((k for k in studio.products() if k.get('word_source',{}).get('import_id')==uid),None)
 if old and not recovered and payload.get('expected_version')!=old['version']:raise ValueError('产品已被更新，请重新核对最新版本')
 if recovered:result={'product_id':recovered['product_id'],'version':recovered['version']}
 else:result=studio.save_product({**{k:v for k,v in fields.items() if k in {'name','brand','audience','facts','fact_details'}},**({'product_id':pid} if pid else {}),'import_id':uid})
 item.update(status='published',analyzed_at=time.time(),reviewer=reviewer,product_version=result['version'])
 r.update(product_id=result['product_id'],name=studio.product(result['product_id'])['product']['name'],updated_at=time.time())
 runtime.atomic_json(studio.ROOT/'library'/(r['library_id']+'.json'),r)
 return {**result,'message':'人工分析结果已发布，产品可以用于新任务。已有任务保留原知识库版本。'}

def edit(payload):
 old=studio.product(payload.get('product_id',''))
 if payload.get('expected_version')!=old['version']:raise ValueError('产品已被更新，请重新打开最新资料再编辑')
 result=studio.save_product(payload)
 runtime.atomic_json(studio.ROOT/'manual_edits'/old['product_id']/(str(time.time_ns())+'.json'),{'at':time.time(),'previous_version':old['version'],'version':result['version'],'source':'用户在知识库管理中手动编辑'})
 return result

def main():
 parser=argparse.ArgumentParser(description='人工知识库分析工作入口；不会自动调用模型')
 parser.add_argument('command',choices=['list','read','publish']);parser.add_argument('--library-id');parser.add_argument('--file');args=parser.parse_args()
 if args.command=='list':result=summary()
 elif args.command=='read':
  r=record(args.library_id);u=r['uploads'][-1];result={'record':r,'extraction':runtime.read(studio.ROOT/'imports'/u['import_id']/'extraction.json'),'current_product':studio.product(r['product_id']) if r.get('product_id') else None}
 else:result=runtime.action('kb_publish',json.loads(Path(args.file).read_text('utf-8-sig')),uuid.uuid4().hex)
 print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
