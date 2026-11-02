import json,shlex,subprocess
from pathlib import Path
ssh=['ssh','-i','/etc/monitor-vps2-tunnel/id_ed25519','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','UserKnownHostsFile=/etc/monitor-vps2-tunnel/known_hosts','root@117.55.234.72']
code=r'''
import ast,json,sys,time,urllib.request,urllib.error,uuid
from pathlib import Path
sys.path.insert(0,'/opt/geo-monitor-auth')
path=Path('/opt/geo-monitor-auth/server.py');tree=ast.parse(path.read_text())
def listener(node):return isinstance(node,ast.Expr) and isinstance(node.value,ast.Call) and isinstance(node.value.func,ast.Attribute) and node.value.func.attr=='serve_forever'
assert sum(listener(node) for node in tree.body)==1
tree.body=[node for node in tree.body if not listener(node)]
namespace={'__name__':'geo_access_verification'};exec(compile(tree,str(path),'exec'),namespace);namespace['SESSION_SECONDS']=600
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
base='https://1any.top/geo_monitor'
def request(path,user=None,data=None,extra=None):
 headers={'Cache-Control':'no-cache'}
 if user:headers['Cookie']='geo_monitor_session='+namespace['make_token'](user)
 headers.update(extra or {})
 if data is not None:headers['Content-Type']='application/json';data=json.dumps(data).encode()
 try:
  with op.open(urllib.request.Request(base+path,headers=headers,data=data),timeout=60) as r:return r.status,r.read(),dict(r.headers)
 except urllib.error.HTTPError as e:return e.code,e.read(),dict(e.headers)
reader=next(u for u in namespace['users']() if u!='superadmin')
assert request('/api/performance-entry/access')[0]==401
status,body,headers=request('/api/performance-entry/access',reader);assert status==200,(status,body[:150]);assert json.loads(body)['can_edit'] is False
assert request('/api/performance-entry/data?month=2026-10&date=2026-10-31',reader)[0]==403
# Keep the exact admin session for CSRF binding across the next calls.
token=namespace['make_token']('superadmin');cookie={'Cookie':'REDACTED_CONFIGURE_LOCALLY'+token}
status,body,headers=request('/api/performance-entry/access',extra=cookie);assert status==200,(status,body[:150])
access=json.loads(body);assert access['can_edit'] is True and access['user']=='superadmin'
status,body,_=request('/api/performance-entry/data?month=2026-10&date=2026-10-30',extra=cookie);assert status==200,(status,body[:150])
data=json.loads(body);assert len(data['rows'])==15
row=data['rows'][0];cell=row['fields']['traffic']
save={'month':'2026-10','operation_id':uuid.uuid4().hex,'changes':[{'product':row['product'],'field':'traffic','date':'2026-10-30','value':cell['value'],'expected_revision':cell['revision']}]}
assert request('/api/performance-entry/save',reader,save,{'Origin':'https://1any.top','X-CSRF-Token':access['csrf']})[0]==403
assert request('/api/performance-entry/save',data=save,extra={**cookie,'Origin':'https://1any.top'})[0]==403
assert request('/api/performance-entry/save',data=save,extra={**cookie,'Origin':'https://evil.test','X-CSRF-Token':access['csrf']})[0]==403
status,body,_=request('/api/performance-entry/save',data=save,extra={**cookie,'Origin':'https://1any.top','X-CSRF-Token':access['csrf']})
assert status==200,(status,body[:150]);assert json.loads(body)['updated_cells']==0,'Verification must not alter historical data'
status,body,_=request('/api/performance?month=2026-10&refresh='+str(time.time_ns()),'superadmin');assert status==200
assert len(json.loads(body)['people'])==5
# Admin response must never bleed into a reader request, even on the identical URL.
assert json.loads(request('/api/performance-entry/access',reader)[1])['can_edit'] is False
report={'anonymous_denied':True,'reader_write_denied':True,'admin_access':True,'csrf_and_origin_enforced':True,'admin_save_noop':True,'historical_data_unchanged':True,'rows':15,'people':5,'identity_cache_isolation':True}
print(json.dumps(report))
'''
result=subprocess.run(ssh+['python3 -c '+shlex.quote(code)],capture_output=True,text=True,timeout=180)
if result.returncode:raise RuntimeError(result.stderr[-2000:])
report=json.loads(result.stdout)
(Path('/opt/monitor/maintenance/performance-entry-20261031')/'public-verification.json').write_text(json.dumps(report,indent=2))
print('PUBLIC_CHECK',json.dumps(report))
