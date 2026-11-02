import shlex,subprocess
code=r'''
import ast,gzip,json,sys,time,urllib.request
from pathlib import Path
sys.path.insert(0,'/opt/geo-monitor-auth');path=Path('/opt/geo-monitor-auth/server.py');tree=ast.parse(path.read_text())
tree.body=[n for n in tree.body if not(isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Attribute) and n.value.func.attr=='serve_forever')]
ns={'__name__':'probe'};exec(compile(tree,str(path),'exec'),ns);ns['SESSION_SECONDS']=300;token=ns['make_token']('superadmin')
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
for suffix in ['', '&refresh='+str(time.time_ns())]:
 start=time.monotonic();req=urllib.request.Request('https://1any.top/geo_monitor/api/performance?month=2026-10'+suffix,headers={'Cookie':'REDACTED_CONFIGURE_LOCALLY'+token,'Accept-Encoding':'gzip'})
 with op.open(req,timeout=70) as r:
  ttfb=time.monotonic()-start;body=r.read();encoding=r.headers.get('Content-Encoding','');status=r.status;cache=r.headers.get('X-Monitor-Cache')
 if encoding=='gzip':data=json.loads(gzip.decompress(body))
 else:data=json.loads(body)
 print(json.dumps({'status':status,'ttfb':round(ttfb,3),'total':round(time.monotonic()-start,3),'bytes':len(body),'encoding':encoding,'people':len(data['people']),'cache':cache}),flush=True)
'''
ssh=['ssh','-i','/etc/monitor-vps2-tunnel/id_ed25519','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile=/etc/monitor-vps2-tunnel/known_hosts','root@117.55.234.72']
r=subprocess.run(ssh+['python3 -c '+shlex.quote(code)],capture_output=True,text=True,timeout=170)
print(r.stdout)
if r.returncode:raise RuntimeError(r.stderr[-1200:])
