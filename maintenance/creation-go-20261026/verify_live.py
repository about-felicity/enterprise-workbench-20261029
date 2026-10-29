import json,subprocess,tempfile,pwd,os,sys
sys.path.insert(0,'/opt/monitor/geo-content')
from creation.go_transport import GoSession
r=GoSession('/opt/monitor/geo-content/runtime/model.sock').get('https://api.deepseek.com/user/balance')
assert r.status_code==200 and isinstance(r.json().get('is_available'),bool)
with tempfile.TemporaryDirectory(prefix='creation-go-probe-') as folder:
 owner=pwd.getpwnam('user');os.chown(folder,owner.pw_uid,owner.pw_gid)
 subprocess.run(['/usr/sbin/runuser','-u','user','--','/opt/monitor/geo-content/bin/creation-runner','capture','/opt/monitor/geo-content/search-pool/slots',folder+'/resource.lock','--','/bin/true'],check=True,timeout=10)
print(json.dumps({'native_balance_transport':True,'capture_permissions_and_release':True,'paid_requests':0}))
