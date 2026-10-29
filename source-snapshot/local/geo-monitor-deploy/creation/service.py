"""Loopback-only creation API; same-origin gateway supplies public authentication."""
import argparse
import hashlib
import json
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import secrets
import threading
import time
import logging
from urllib.parse import parse_qs,urlsplit
from . import runtime,source_adapter

sessions={};lock=threading.Lock()
class Handler(BaseHTTPRequestHandler):
    def log_message(self,*args):pass
    def send(self,value,status=200,content_type='application/json; charset=utf-8',cookie=None,extra=None):
        body=value if isinstance(value,bytes) else json.dumps(value,ensure_ascii=False).encode()
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
            if path=='/':return self.send(Path(__file__).with_name('panel.html').read_bytes(),content_type='text/html; charset=utf-8')
            if path=='/api/panel':
                token,session=self.session(True)
                return self.send({**runtime.status(),'csrf':session['csrf']},cookie=token)
            if path=='/api/uploads':
                from .knowledge_library import upload_snapshot
                token,session=self.session(True)
                return self.send({'ok':True,'studio':upload_snapshot(),'csrf':session['csrf'],'at':time.time()},cookie=token)
            if path=='/api/status':return self.send(runtime.status())
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
                file=runtime.download(get('job'),get('article'),get('kind'),{k:get(k) for k in ('date','product','source','search','plan') if get(k)})
                mime='application/zip' if file.suffix=='.zip' else 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' if file.suffix=='.docx' else 'text/markdown; charset=utf-8'
                body=file.read_bytes()
                # Hash and deliver the exact same snapshot even during concurrent exports.
                return self.send(body,content_type=mime,extra={'Content-Disposition':'attachment; filename="creation-articles'+file.suffix+'"','X-Content-SHA256':hashlib.sha256(body).hexdigest(),'X-Download-Bytes':str(len(body))})
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
            result=runtime.action(action,payload,self.headers.get('X-Action-Id',''))
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
    ThreadingHTTPServer(('127.0.0.1',8804),Handler).serve_forever()
