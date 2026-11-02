import json,shlex,subprocess
from pathlib import Path
ssh=['ssh','-i','/etc/monitor-vps2-tunnel/id_ed25519','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile=/etc/monitor-vps2-tunnel/known_hosts','root@117.55.234.72']
code=r'''
import ast,json,sys,urllib.request,urllib.error
from pathlib import Path
sys.path.insert(0,'/opt/geo-monitor-auth')
p=Path('/opt/geo-monitor-auth/server.py');tree=ast.parse(p.read_text())
tree.body=[n for n in tree.body if not(isinstance(n,ast.Expr) and isinstance(n.value,ast.Call) and isinstance(n.value.func,ast.Attribute) and n.value.func.attr=='serve_forever')]
ns={'__name__':'confirmation_check'};exec(compile(tree,str(p),'exec'),ns);ns['SESSION_SECONDS']=300
assert 'geo_admin' in ns['users']() and 'superadmin' in ns['users']()
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
url='https://1any.top/geo_monitor/api/performance-entry/confirmation'
def req(cookie='',body=None,headers=None):
 h={'Cookie':cookie,**(headers or {})}
 if body is not None:h['Content-Type']='application/json'
 try:
  with op.open(urllib.request.Request(url+('?month=2026-11' if body is None else ''),headers=h,data=json.dumps(body).encode() if body is not None else None),timeout=45) as r:return r.status,json.load(r)
 except urllib.error.HTTPError as e:return e.code,None
assert req()[0]==401
cookie='REDACTED_CONFIGURE_LOCALLY'+ns['make_token']('geo_admin')
code,v=req(cookie);assert code==200 and v['can_confirm'] and not v['can_reset']
assert v['window']['state']=='upcoming' and v['window']['deadline']=='2026-11-30T18:00:00+08:00'
assert len(v['people'])==5 and all(not p['password_set'] and not p['confirmed_at'] for p in v['people'])
headers={'Origin':'https://1any.top','X-CSRF-Token':v['csrf']}
assert req(cookie,{'action':'reset','name':'佳佳'},headers)[0]==403
assert req(cookie,{'action':'preview','name':'佳佳','month':'2026-11'},headers)[0]==400
assert req(cookie,{'action':'setup','name':'佳佳','password':'REDACTED_CONFIGURE_LOCALLY'},{'Origin':'https://evil.test','X-CSRF-Token':v['csrf']})[0]==403
assert req(cookie,{'action':'setup','name':'佳佳','password':'REDACTED_CONFIGURE_LOCALLY'},{'Origin':'https://1any.top'})[0]==403
admin='geo_monitor_session='+ns['make_token']('superadmin')
code,a=req(admin);assert code==200 and a['can_reset'] and not a['can_confirm']
assert all(not p['password_set'] for p in req(cookie)[1]['people'])
print(json.dumps({'public_geo_admin_access':True,'public_superadmin_reset_permission':True,'anonymous_and_csrf_denied':True,'month_end_deadline_enforced':True,'no_employee_passwords_or_confirmations_created':True}))
'''
r=subprocess.run(ssh+['python3 -c '+shlex.quote(code)],capture_output=True,text=True,timeout=120)
if r.returncode:raise RuntimeError(r.stderr[-1500:])
print(r.stdout)
(Path('/opt/monitor/maintenance/performance-confirmation-20261102')/'public-verification.json').write_text(r.stdout)
