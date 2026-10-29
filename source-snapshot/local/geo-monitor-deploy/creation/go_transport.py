"""Compatibility adapter for the native Go Unix-socket model transport."""
import http.client,json,socket
import requests

class UnixConnection(http.client.HTTPConnection):
    def __init__(self,path,timeout):
        super().__init__('localhost',timeout=timeout);self.path=path
    def connect(self):
        self.sock=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout);self.sock.connect(self.path)

class GoSession:
    def __init__(self,path):self.path=path
    def send(self,method,url,**kwargs):
        routes={('GET','https://api.deepseek.com/user/balance'):'/balance',
                ('POST','https://api.deepseek.com/chat/completions'):'/completions'}
        path=routes.get((method,url))
        if not path:raise requests.RequestException('Unsupported native transport route')
        # Never fall back to a second transport after an uncertain paid send.
        conn=UnixConnection(self.path,340 if method=='POST' else 30)
        try:
            body=json.dumps(kwargs['json'],ensure_ascii=False).encode('utf8') if method=='POST' else None
            conn.request(method,path,body=body,headers={'Content-Type':'application/json'})
            value=conn.getresponse();response=requests.Response()
            response.status_code=value.status;response._content=value.read(16*1024*1024+1)
            if len(response._content)>16*1024*1024:raise requests.RequestException('Native response too large')
            response.encoding='utf8';return response
        except (OSError,http.client.HTTPException) as error:
            raise requests.RequestException('Native model transport unavailable') from error
        finally:conn.close()
    def get(self,url,**kwargs):return self.send('GET',url,**kwargs)
    def post(self,url,**kwargs):return self.send('POST',url,**kwargs)
    def close(self):pass
