import subprocess,json,urllib.request
from pathlib import Path
for name in ['monitor-dashboard']:
 d=json.loads(subprocess.check_output(['docker','inspect',name]))[0]
 print(json.dumps({'container':name,'image_id':d['Image'],'image_ref':d['Config']['Image'],'command':d['Config']['Cmd'],'mounts':[{'source':m['Source'],'dest':m['Destination']} for m in d['Mounts']]}))
print(subprocess.run(['docker','compose','-p','local-server','-f','/opt/monitor/deploy/local-server/docker-compose.yml','config','--images'],capture_output=True,text=True).stdout)
for endpoint in ['http://127.0.0.1:8804/api/uploads','http://127.0.0.1:3000/api/geo-creation/uploads','http://127.0.0.1:3000/']:
 try:
  with urllib.request.urlopen(endpoint,timeout=8) as r:print(endpoint,r.status,r.read(150).decode('utf-8','replace'))
 except Exception as e:print(endpoint,str(e))
print(subprocess.run(['docker','run','--rm','--network','none','--entrypoint','sh','monitor-dashboard:upload-reliability-20261028','-c',"grep -n 'uploads' '/dashboard/app/api/geo-creation/[...path]/route.ts'; cat /dashboard/package.json | head -18"],capture_output=True,text=True).stdout)
