"""Loopback-only creation API; same-origin gateway supplies public authentication."""
import argparse
import base64
import gzip
import hashlib
import json
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import secrets
import threading
import time
import logging
from urllib.parse import parse_qs,urlsplit,quote
from . import runtime,source_adapter
from .article_export import article_filename
from .status_cache import StatusCache,LibraryCache

sessions={};lock=threading.Lock()
task_status_cache=LibraryCache(ttl=3,max_stale=7,wait_timeout=35)
output_cache=LibraryCache(ttl=30,wait_timeout=40)
panel_cache=StatusCache(ttl=10,wait_timeout=40)
knowledge_cache=StatusCache(ttl=5)

def build_tasks():
    return runtime.status(task_list=True)

def build_outputs():
    return runtime.output_status()

def prime_lists():
    try:
        task_status_cache.get(build_tasks)
        output_cache.get(build_outputs)
    except Exception:
        logging.exception('Creation list warmup failed')

class PackedView:
    def __init__(self):
        self.lock = threading.Lock()
        self.snapshot = None

    def response(self, snapshot, version):
        with self.lock:
            if snapshot is not self.snapshot:
                raw = json.dumps({k:v for k,v in snapshot.items() if k!='at'},ensure_ascii=False,separators=(',',':')).encode()
                self.version = hashlib.sha256(raw).hexdigest()
                self.packed = base64.b64encode(gzip.compress(raw,compresslevel=3)).decode('ascii')
                self.snapshot = snapshot
            result = {'version':self.version, 'at':snapshot['at']}
            if version != self.version:
                result['packed'] = self.packed
            return result

packed_outputs = PackedView()
packed_tasks = PackedView()

def packed_knowledge():
    from .knowledge_library import upload_snapshot
    raw=json.dumps(upload_snapshot(),ensure_ascii=False,separators=(',',':')).encode()
    return hashlib.sha256(raw).hexdigest(),base64.b64encode(gzip.compress(raw,compresslevel=3)).decode('ascii')
class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def send(self,value,status=200,content_type='application/json; charset=utf-8',cookie=None,extra=None):
        body=value if isinstance(value,bytes) else json.dumps(value,ensure_ascii=False,separators=(',',':')).encode()
        self.send_response(status);self.send_header('Content-Type',content_type)
        self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff')
        if cookie:self.send_header('Set-Cookie','geo_creation='+cookie+'; HttpOnly; SameSite=Strict; Path=/; Max-Age=21600')
        for key,val in (extra or {}).items():self.send_header(key,val)
        self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
    def session(self,create=False):
        cookies=SimpleCookie(self.headers.get('Cookie',''));token=cookies.get('geo_creation')
        token=token.value if token else ''
        now=time.time()
        with lock:
            for key in list(sessions):
                if sessions[key]['expires']<now:del sessions[key]
            if token not in sessions:
                if not create:return None,None
                token=secrets.token_hex(32);sessions[token]={'csrf':secrets.token_hex(32),'expires':now+21600}
            return token,sessions[token]
    def do_GET(self):
        path=urlsplit(self.path).path
        try:
            if path=='/':
                html=Path(__file__).with_name('panel.html').read_bytes()
                token,session=self.session(True)
                try:
                    # The first page may show a timestamped recent result. Live polling
                    # retains its short freshness limit, including after any mutation.
                    with task_status_cache.condition:
                        previous=task_status_cache.value
                    if previous and 0 <= time.time()-previous['at'] < 3600:
                        snapshot=previous
                    else:
                        snapshot=task_status_cache.get(build_tasks)
                    payload=json.dumps({**snapshot,'csrf':session['csrf']},ensure_ascii=False,separators=(',',':')).encode()
                    html=html.replace(b'__TASK_BOOTSTRAP__',base64.b64encode(gzip.compress(payload,compresslevel=1)),1)
                except Exception:
                    logging.exception('Task bootstrap unavailable')
                    html=html.replace(b'__TASK_BOOTSTRAP__',b'',1)
                return self.send(html,content_type='text/html; charset=utf-8',cookie=token)
            if path=='/api/panel':
                token,session=self.session(True)
                return self.send({**panel_cache.get(runtime.status),'csrf':session['csrf']},cookie=token)
            if path=='/api/uploads':
                from .knowledge_library import upload_snapshot
                token,session=self.session(True)
                return self.send({'ok':True,'studio':upload_snapshot(),'csrf':session['csrf'],'at':time.time()},cookie=token)
            if path=='/api/status':
                token,session=self.session(True)
                return self.send({**task_status_cache.get(build_tasks),'csrf':session['csrf']},cookie=token)
            if path=='/api/catalog':
                from . import materials
                try:geo=source_adapter.catalog()
                except Exception:geo={'dates':[],'questions':[],'channels':[]}
                return self.send({**geo,'geo':geo,'dedicated':materials.catalog(),'product':runtime.read(runtime.SHARED/'product.json')})
            if path=='/api/product_image':
                if not self.session()[1]:return self.send({'ok':False,'message':'请刷新页面后查看图片'},403)
                from .product_images import read
                query=parse_qs(urlsplit(self.path).query)
                body,mime=read(query.get('id',[''])[0],thumbnail=query.get('thumbnail',[''])[0]=='1')
                return self.send(body,content_type=mime)
            if path=='/api/download':
                query=parse_qs(urlsplit(self.path).query)
                get=lambda k:query.get(k,[''])[0]
                if get('kind')=='scene-image':
                    from .pexels_images import image_path
                    return self.send(image_path(get('id')).read_bytes(),content_type='image/png')
                if get('kind')=='pexels-search':
                    from .pexels_images import search
                    return self.send(search(get('query')))
                if get('kind')=='knowledge-list':
                    token,session=self.session(True)
                    version,packed=knowledge_cache.get(packed_knowledge)
                    result={'csrf':session['csrf'],'version':version}
                    if get('version')!=version:result['packed']=packed
                    return self.send(result,cookie=token)
                if get('kind')=='knowledge':
                    from . import studio
                    from .knowledge_library import record
                    owner=get('owner')
                    if owner.startswith('library-'):
                        versions=record(owner).get('uploads',[])
                    else:
                        versions=[studio.product(owner).get('word_source') or {}]
                    uid=studio.identity(get('version'),'upload')
                    source=next((v for v in versions if v.get('import_id')==uid),None)
                    if not source:raise ValueError('该知识库没有此版本')
                    file=studio.ROOT/'imports'/uid/'source.docx'
                    if not file.is_file():raise ValueError('该版本原文件不存在')
                    body=file.read_bytes()
                    if hashlib.sha256(body).hexdigest()!=source.get('sha256'):raise ValueError('原文件校验失败')
                    name=Path(source['filename'].replace('\\','/')).name
                    return self.send(body,content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document',extra={'Content-Disposition':"attachment; filename=\"knowledge.docx\"; filename*=UTF-8''"+quote(name,safe=''),'X-Content-SHA256':source['sha256']})
                if get('kind') in {'library','task-list'}:
                    token,session=self.session(True)
                    if get('kind')=='task-list':
                        snapshot=task_status_cache.get(build_tasks,max_stale=117)
                        response=packed_tasks.response(snapshot,get('version'))
                    else:
                        snapshot=output_cache.get(build_outputs)
                        response=packed_outputs.response(snapshot,get('version')) if get('packed')=='1' else snapshot
                    return self.send({**response,'csrf':session['csrf']},cookie=token)
                references=query.get('references',['1'])
                if references not in (['1'],['0']):raise ValueError('参考链接选项不正确')
                filters={k:get(k) for k in ('date','product','source','search','plan') if get(k)}
                file,title=runtime.download_with_title(get('job'),get('article'),get('kind'),filters,include_references=references==['1'])
                mime='application/json; charset=utf-8' if file.suffix=='.json' else 'application/zip' if file.suffix=='.zip' else 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' if file.suffix=='.docx' else 'text/markdown; charset=utf-8'
                body=file.read_bytes()
                # Hash and deliver the exact same snapshot even during concurrent exports.
                disposition=f'attachment; filename="creation-articles{file.suffix}"'
                if title:
                    disposition+="; filename*=UTF-8''"+quote(article_filename(title,file.suffix),safe='')
                return self.send(body,content_type=mime,extra={'Content-Disposition':disposition,'X-Content-SHA256':hashlib.sha256(body).hexdigest(),'X-Download-Bytes':str(len(body))})
            self.send({'ok':False,'message':'接口不存在'},404)
        except (ValueError,KeyError) as error:self.send({'ok':False,'message':str(error)},400)
        except Exception as error:self.send({'ok':False,'message':'服务检查失败：'+type(error).__name__},503)
    def do_POST(self):
        started=time.monotonic()
        self.connection.settimeout(90)
        _,session=self.session()
        if self.headers.get('Origin')!='http://127.0.0.1:8804' or not session or not secrets.compare_digest(self.headers.get('X-CSRF-Token',''),session['csrf']):
            return self.send({'ok':False,'message':'请求校验失败，请刷新面板'},403)
        try:
            length=int(self.headers.get('Content-Length','0'))
            limit=7_100_000 if urlsplit(self.path).path in {'/api/control/kb_import','/api/control/kb_upload','/api/control/product_image_upload'} else 1_100_000
            if not 0<length<=limit:raise ValueError('请求长度不正确')
            if self.headers.get('Content-Type','').split(';')[0]!='application/json':raise ValueError('需要JSON请求')
            payload=json.loads(self.rfile.read(length))
            if not isinstance(payload,dict):raise ValueError('请求须为对象')
            action=urlsplit(self.path).path.removeprefix('/api/control/')
            try:
                result=runtime.action(action,payload,self.headers.get('X-Action-Id',''))
            finally:
                # Even a failed action may have saved part of its durable state.
                task_status_cache.invalidate()
                output_cache.invalidate()
                panel_cache.invalidate()
                if action.startswith('kb_') or action=='product_image_upload':knowledge_cache.invalidate()
            if action in {'product_image_upload','kb_upload'}:
                logging.warning('upload_completed action=%s bytes=%s elapsed=%.3f reused=%s',action,length,time.monotonic()-started,result.get('reused',False))
            self.send({'ok':True,'result':result})
        except (BrokenPipeError,ConnectionResetError):return
        except (ValueError,KeyError,TypeError) as error:
            logging.warning('upload_or_control_rejected path=%s type=%s elapsed=%.3f',urlsplit(self.path).path,type(error).__name__,time.monotonic()-started)
            self.send({'ok':False,'message':str(error)},400)
        except Exception as error:
            logging.exception('upload_or_control_failed path=%s elapsed=%.3f',urlsplit(self.path).path,time.monotonic()-started)
            self.send({'ok':False,'message':'操作失败，保留现场：'+type(error).__name__},503)

if __name__=='__main__':
    runtime.BASE.mkdir(parents=True,exist_ok=True)
    class CreationServer(ThreadingHTTPServer):
        request_queue_size=64
    server=CreationServer(('127.0.0.1',8804),Handler)
    threading.Thread(target=prime_lists,daemon=True).start()
    server.serve_forever()
