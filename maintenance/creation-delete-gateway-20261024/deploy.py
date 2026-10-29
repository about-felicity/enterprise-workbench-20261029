import hashlib,json,os,shutil,subprocess,sys,time,urllib.request
from pathlib import Path
R=Path('/tmp/creation-delete-gateway-20261024');B=Path('/opt/monitor/geo-content/maintenance/creation-delete-gateway-20261024');S=R/'stage'
P=B/'release.json';IMAGE='monitor-dashboard:delete-fix-20261024';PREVIEW='monitor-dashboard-delete-preview'
def run(*args):return subprocess.check_output(args,text=True,timeout=90).strip()
def save(info):P.write_text(json.dumps(info,indent=2))
def ready(port):
 for _ in range(40):
  try:
   with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/geo-creation/panel',timeout=3) as r:
    if r.status==200:return
  except Exception:time.sleep(1)
 raise RuntimeError('Dashboard failed health check')
mode=sys.argv[1]
if mode=='build':
 B.mkdir(parents=True,exist_ok=True);assert not P.exists()
 info={'original_image':run('docker','inspect','monitor-dashboard','--format','{{.Image}}'),'status':'building'}
 save(info);run('docker','tag',info['original_image'],'monitor-dashboard:before-delete-fix-20261024')
 (R/'Dockerfile').write_text('FROM monitor-dashboard:before-delete-fix-20261024\nCOPY stage/route.ts /dashboard/app/api/geo-creation/[...path]/route.ts\nCOPY stage/creation-gateway.test.mjs /dashboard/tests/creation-gateway.test.mjs\nWORKDIR /dashboard\nRUN node --experimental-strip-types --test tests/creation-gateway.test.mjs tests/capture-gateway.test.mjs\nRUN npm run build\n')
 subprocess.run(['docker','build','-t',IMAGE,str(R)],check=True,timeout=600)
 run('docker','run','-d','--name',PREVIEW,'--network','host',IMAGE,'npm','run','start','--','-H','127.0.0.1','-p','3001');ready(3001)
 info['status']='preview';save(info)
elif mode=='publish':
 info=json.loads(P.read_text());assert info['status']=='preview'
 assert json.loads((R/'qa-3001.json').read_text())['success']
 assert run('docker','inspect','monitor-dashboard','--format','{{.Image}}')==info['original_image']
 mapping={'panel.html':'/opt/monitor/geo-content/creation/panel.html','route.ts':'/opt/monitor/yuanbao_monitor/dashboard/app/api/geo-creation/[...path]/route.ts','creation-gateway.test.mjs':'/opt/monitor/yuanbao_monitor/dashboard/tests/creation-gateway.test.mjs'}
 backup=B/'before';backup.mkdir(exist_ok=True)
 for source,target in mapping.items():shutil.copy2(target,backup/source)
 assert hashlib.sha256(Path(mapping['panel.html']).read_bytes()).hexdigest()=='4b42baacd622bf22ecc5d7d3212bf9b8520a9eacaf5dd28f057ed6cb7b8b5065'
 command=['docker','compose','-p','local-server','-f','/opt/monitor/deploy/local-server/docker-compose.yml','up','-d','--no-deps','--no-build','--force-recreate','dashboard']
 try:
  for source,target in mapping.items():
   dest=Path(target);temp=dest.with_name(dest.name+'.installing');shutil.copy2(S/source,temp);os.replace(temp,dest)
  run('docker','tag',IMAGE,'monitor-dashboard:local');run(*command);ready(3000)
 except Exception:
  for source,target in mapping.items():shutil.copy2(backup/source,target)
  run('docker','tag',info['original_image'],'monitor-dashboard:local');run(*command);raise
 info.update(status='published',files=[{'source_name':s,'server':t,'sha256':hashlib.sha256(Path(t).read_bytes()).hexdigest()} for s,t in mapping.items()]);save(info)
 run('docker','rm','-f',PREVIEW)
print(json.dumps(json.loads(P.read_text())))
