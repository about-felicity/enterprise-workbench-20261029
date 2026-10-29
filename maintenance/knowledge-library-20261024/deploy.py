import hashlib,json,os,shutil,subprocess,sys,time,urllib.request
from pathlib import Path
D=Path('/tmp/knowledge-library-20261024');B=Path('/opt/monitor/geo-content/maintenance/knowledge-library-20261024');L=Path('/opt/monitor/geo-content');P=B/'release.json'
IMAGE='monitor-dashboard:knowledge-library-20261024';PREVIEW='monitor-dashboard-knowledge-preview'
files=['panel.html','studio.py','runtime.py','service.py','knowledge_library.py','library.js','wizard.js','test_knowledge_library.py']
def run(*args):return subprocess.check_output(args,text=True,timeout=90).strip()
def ready(port):
 for _ in range(40):
  try:
   with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/geo-creation/panel',timeout=3) as r:
    if r.status==200:return
  except Exception:time.sleep(1)
 raise RuntimeError('Health check failed')
mode=sys.argv[1]
if mode=='build':
 B.mkdir(parents=True,exist_ok=True);assert not P.exists()
 info={'original_image':run('docker','inspect','monitor-dashboard','--format','{{.Image}}'),'baseline':{f:hashlib.sha256((L/'creation'/f).read_bytes()).hexdigest() if (L/'creation'/f).exists() else None for f in files},'status':'building'};P.write_text(json.dumps(info))
 run('docker','tag',info['original_image'],'monitor-dashboard:before-knowledge-library-20261024')
 (D/'Dockerfile').write_text('FROM monitor-dashboard:before-knowledge-library-20261024\nCOPY route.ts /dashboard/app/api/geo-creation/[...path]/route.ts\nCOPY creation-gateway.test.mjs /dashboard/tests/creation-gateway.test.mjs\nWORKDIR /dashboard\nRUN node --experimental-strip-types --test tests/creation-gateway.test.mjs tests/capture-gateway.test.mjs\nRUN npm run build\n')
 subprocess.run(['docker','build','-t',IMAGE,str(D)],check=True,timeout=600)
 run('docker','run','-d','--name',PREVIEW,'--network','host',IMAGE,'npm','run','start','--','-H','127.0.0.1','-p','3001');ready(3001)
 info['status']='preview';P.write_text(json.dumps(info))
elif mode=='publish':
 info=json.loads(P.read_text());assert info['status']=='preview';assert json.loads((D/'qa.json').read_text())['success'];assert (D/'tests.log').read_text().rstrip().endswith('OK')
 assert run('docker','inspect','monitor-dashboard','--format','{{.Image}}')==info['original_image']
 for f,sha in info['baseline'].items():assert (hashlib.sha256((L/'creation'/f).read_bytes()).hexdigest() if (L/'creation'/f).exists() else None)==sha,f
 backup=B/'before';backup.mkdir(exist_ok=True)
 for f in files:
  if (L/'creation'/f).exists():shutil.copy2(L/'creation'/f,backup/f)
 info['workers_before']={s:run('systemctl','show',s,'-p','MainPID','-p','ActiveEnterTimestampMonotonic') for s in ['geo-content-worker','geo-creation-studio']}
 command=['docker','compose','-p','local-server','-f','/opt/monitor/deploy/local-server/docker-compose.yml','up','-d','--no-deps','--no-build','--force-recreate','dashboard']
 try:
  run('systemctl','stop','geo-content-api')
  for f in files:
   dest=L/'creation'/f;temp=dest.with_name(f+'.installing');shutil.copy2(D/'candidate/creation'/f,temp);os.replace(temp,dest)
  run('systemctl','start','geo-content-api');run('docker','tag',IMAGE,'monitor-dashboard:local');run(*command);ready(3000)
 except Exception:
  for f in files:
   if (backup/f).exists():shutil.copy2(backup/f,L/'creation'/f)
  run('systemctl','restart','geo-content-api');run('docker','tag',info['original_image'],'monitor-dashboard:local');run(*command);raise
 mapping={str(D/'candidate/creation'/f):str(L/'creation'/f) for f in files}
 for name,target in [('route.ts','app/api/geo-creation/[...path]/route.ts'),('creation-gateway.test.mjs','tests/creation-gateway.test.mjs')]:
  dest=Path('/opt/monitor/yuanbao_monitor/dashboard')/target;shutil.copy2(dest,backup/name);shutil.copy2(D/name,dest);mapping[str(D/name)]=str(dest)
 info['workers_after']={s:run('systemctl','show',s,'-p','MainPID','-p','ActiveEnterTimestampMonotonic') for s in info['workers_before']};assert info['workers_before']==info['workers_after']
 info.update(status='published',files=[{'server':v,'sha256':hashlib.sha256(Path(v).read_bytes()).hexdigest()} for v in mapping.values()]);P.write_text(json.dumps(info,indent=2))
 run('docker','rm','-f',PREVIEW)
print(json.dumps(json.loads(P.read_text())))
