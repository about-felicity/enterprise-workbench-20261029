import shlex,subprocess,json,time,urllib.request
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
for month in ['2026-10','2026-11']:
 for attempt in range(2):
  t=time.monotonic()
  with op.open('http://127.0.0.1:8765/api/performance?month='+month,timeout=90) as r:
   body=r.read();print('LAN',month,attempt,round(time.monotonic()-t,3),len(body),r.headers.get('X-Monitor-Cache'),flush=True)
code=r'''
import ast,json,sys,time,urllib.request,gzip
from pathlib import Path
sys.path.insert(0,'/opt/geo-monitor-auth');p=Path('/opt/geo-monitor-auth/server.py');tree=ast.parse(p.read_text())
tree.body=[n for n in tree.body if not(isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Attribute) and n.value.func.attr=='serve_forever')]
ns={'__name__':'speed_probe'};exec(compile(tree,str(p),'exec'),ns);ns['SESSION_SECONDS']=300
op=urllib.request.build_opener(urllib.request.ProxyHandler({}));cookie='REDACTED_CONFIGURE_LOCALLY'+ns['make_token']('superadmin')
for path in ['/','/api/performance?month=2026-10','/api/performance?month=2026-11','/api/performance-entry/access','/api/performance-entry/data?month=2026-10&date=2026-10-30','/api/performance-entry/confirmation?month=2026-11']:
 t=time.monotonic()
 with op.open(urllib.request.Request('https://1any.top/geo_monitor'+path,headers={'Cookie':cookie,'Accept-Encoding':'gzip'}),timeout=90) as r:
  first=time.monotonic()-t;body=r.read();print('PUBLIC',json.dumps({'path':path,'ttfb':round(first,3),'total':round(time.monotonic()-t,3),'bytes':len(body),'encoding':r.headers.get('Content-Encoding'),'cache':r.headers.get('X-Monitor-Cache')}),flush=True)
'''
ssh=['ssh','-i','/etc/monitor-vps2-tunnel/id_ed25519','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile=/etc/monitor-vps2-tunnel/known_hosts','root@117.55.234.72']
r=subprocess.run(ssh+['python3 -c '+shlex.quote(code)],text=True,capture_output=True,timeout=240);print(r.stdout,flush=True)
if r.returncode:raise RuntimeError(r.stderr[-1500:])
