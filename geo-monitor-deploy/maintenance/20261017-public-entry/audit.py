import hashlib,json,re,sys,urllib.request
from pathlib import Path
sys.path.insert(0,'/tmp')
from vps_geo_access import browser_cookie,vps_python
token=browser_cookie()
def get(url,auth=False):
 req=urllib.request.Request(url,headers={'Cookie':'REDACTED_CONFIGURE_LOCALLY'+token} if auth else {})
 with urllib.request.urlopen(req,timeout=25) as r:body=r.read();return {'status':r.status,'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest(),'assets':re.findall(r'(?:src|href)="([^"]+\.(?:js|css)[^"]*)"',body.decode(errors='replace')),'headers':{k:v for k,v in r.headers.items() if k.lower() in {'cache-control','x-geo-cache','x-geo-fallback','x-cache','etag','last-modified'}}}
result={'lan':get('http://127.0.0.1:3000/'),'public':get('https://1any.top/geo_monitor/',True)}
result['vps']=json.loads(vps_python('''import json,re,urllib.request
from pathlib import Path
text=Path('/etc/nginx/nginx.conf').read_text();start=text.find('location ^~ /geo_monitor/ {')
with urllib.request.urlopen('http://127.0.0.1:13000/',timeout=15) as r:html=r.read().decode()
print(json.dumps({'root_location':text[start:start+3300],'tunnel_assets':re.findall(r'(?:src|href)="([^\\"]+\\.js[^\\"]*)"',html)}))
'''))
print(json.dumps(result,ensure_ascii=False,indent=2))
