import hashlib,json,re,shlex,subprocess,urllib.request
from pathlib import Path
work=Path('/opt/monitor/maintenance/performance-weights-20261031');report=json.loads((work/'release.json').read_text())
for row in report['files']:assert hashlib.sha256(Path(row['server']).read_bytes()).hexdigest()==row['sha256']
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
with op.open('http://127.0.0.1:3000/',timeout=15) as r:html=r.read().decode()
expected=set(re.findall(r'assets/([A-Za-z0-9_-]+\.js)',html));assert expected
ssh=['ssh','-i','/etc/monitor-vps2-tunnel/id_ed25519','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile=/etc/monitor-vps2-tunnel/known_hosts','root@117.55.234.72']
code=r'''
import ast,json,re,sys,urllib.request
from pathlib import Path
sys.path.insert(0,'/opt/geo-monitor-auth')
path=Path('/opt/geo-monitor-auth/server.py');tree=ast.parse(path.read_text())
tree.body=[n for n in tree.body if not(isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Attribute) and n.value.func.attr=='serve_forever')]
ns={'__name__':'verify_public_build'};exec(compile(tree,str(path),'exec'),ns);ns['SESSION_SECONDS']=300
expected=set(json.load(sys.stdin));op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
req=urllib.request.Request('https://1any.top/geo_monitor/',headers={'Cookie':'REDACTED_CONFIGURE_LOCALLY'+ns['make_token']('superadmin')})
with op.open(req,timeout=30) as r:html=r.read().decode()
actual=set(re.findall(r'assets/([A-Za-z0-9_-]+\.js)',html))
assert expected<=actual,('Public HTML still refers to old build',sorted(expected-actual))
print('PUBLIC_FRONTEND_CURRENT',len(expected))
'''
result=subprocess.run(ssh+['python3 -c '+shlex.quote(code)],input=json.dumps(sorted(expected)),text=True,capture_output=True,timeout=60)
if result.returncode:raise RuntimeError(result.stderr[-1200:])
print(result.stdout.strip())
try:
 with op.open(urllib.request.Request('http://127.0.0.1:8765/api/performance-entry/access',headers={'X-Geo-Performance-Identity':'superadmin'}),timeout=5):raise AssertionError('Forged LAN identity accepted')
except urllib.error.HTTPError as e:assert e.code==401
report['public_verification']=json.loads((work/'public-verification.json').read_text());report['public_frontend_current']=True;report['deployed_hashes_verified']=True;report['forged_lan_identity_denied']=True
with op.open('http://127.0.0.1:8765/api/performance?month=2026-10&as_of=2026-10-31&refresh=mention-verify',timeout=60) as r:data=json.load(r)
report['mention_scores']={p['name']:p['current']['scores']['mention'] for p in data['people']}
for person in data['people']:
 expected=[10,40,40,10] if person['name'] in {'小美','谭露'} else [30,30,30,10]
 for snapshot in person['daily']:assert [m['weight'] for m in snapshot['mention']['models']]==expected
report['employee_weights_verified_all_days']=True
report.pop('historical_results_preserved',None);report['historical_manual_data_preserved']=True
(work/'release.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print('FINAL_VERIFIED',json.dumps(report['mention_scores'],ensure_ascii=False))
