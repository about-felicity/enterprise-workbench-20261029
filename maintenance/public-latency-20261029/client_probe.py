import subprocess,shlex,json
code=r'''
import ast,json,urllib.request,http.cookiejar,time,gzip,re,concurrent.futures
from pathlib import Path
p=Path('/opt/geo-monitor-auth/server.py');tree=ast.parse(p.read_text())
def listener(n):return isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Attribute) and n.value.func.attr=='serve_forever'
assert sum(listener(n) for n in tree.body)==1
tree.body=[n for n in tree.body if not listener(n)];ns={'__name__':'latency_verification'};exec(compile(tree,str(p),'exec'),ns);ns['SESSION_SECONDS']=300;token=ns['make_token'](next(iter(ns['users']())))
def get(path):
 start=time.monotonic();op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
 req=urllib.request.Request('https://1any.top'+path,headers={'Cookie':'REDACTED_CONFIGURE_LOCALLY'+token,'Accept-Encoding':'gzip'})
 try:
  with op.open(req,timeout=35) as r:
   first=time.monotonic()-start;raw=r.read();body=gzip.decompress(raw) if r.headers.get('Content-Encoding')=='gzip' else raw
   result={'path':path,'http':r.status,'first':round(first,3),'total':round(time.monotonic()-start,3),'bytes':len(raw),'encoding':r.headers.get('Content-Encoding')}
   if path=='/geo_monitor/':result['assets']=re.findall(r'(?:src|href)=["\x27]([^"\x27]+\.(?:js|css)(?:\?[^"\x27]*)?)["\x27]',body.decode('utf8','replace'))[:5]
   return result
 except Exception as e:return {'path':path,'error':str(e),'seconds':round(time.monotonic()-start,3)}
with concurrent.futures.ThreadPoolExecutor(3) as pool:rows=list(pool.map(get,['/geo_monitor/','/geo_monitor/api/control/status','/geo_monitor/api/geo-creation/uploads']))
assets=rows[0].get('assets',[])
with concurrent.futures.ThreadPoolExecutor(3) as pool:rows+=list(pool.map(get,[x for x in assets if x.startswith('/')]))
print(json.dumps({'authenticated':rows}))
'''
args=['ssh','-i','/etc/monitor-vps2-tunnel/id_ed25519','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile=/etc/monitor-vps2-tunnel/known_hosts','-o','ConnectTimeout=10','root@117.55.234.72','python3 -c '+shlex.quote(code)]
token_code=code[:code.index('def get(path):')]+'\nprint(token)'
args[-1]='python3 -c '+shlex.quote(token_code)
r=subprocess.run(args,capture_output=True,text=True,timeout=30)
assert r.returncode==0
scope={'token':r.stdout.strip()}
exec('import json,urllib.request,time,gzip,re,concurrent.futures\n'+code[code.index('def get(path):'):],scope)
from pathlib import Path
Path('/tmp/public-latency-client.json').write_text(json.dumps({'authenticated_from_lan':scope['rows']}))
