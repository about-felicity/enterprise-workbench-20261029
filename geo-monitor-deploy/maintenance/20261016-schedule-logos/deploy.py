import json,shutil,subprocess,sys,time,urllib.request
from pathlib import Path
B=Path('/opt/monitor/geo-capture');R=B/'maintenance/20261016-schedule-logos';S=R/'stage';P=R/'release.json'
IMAGE='monitor-dashboard:schedule-logos-20261016';PREVIEW='monitor-dashboard-schedule-logos-preview'
NAMES=['schedule_control.py','control_panel.py','daily_dispatch.py','daily_tasks.py','fleet_status.py','panel.html']
def run(*args,timeout=60):return subprocess.check_output(args,text=True,timeout=timeout).strip()
def save(v):P.write_text(json.dumps(v,ensure_ascii=False,indent=2))
def ready(port):
 for _ in range(30):
  try:
   with urllib.request.urlopen(f'http://127.0.0.1:{port}/api/geo-capture/panel',timeout=15) as response:assert len(json.load(response)['models'])==6
   return
  except Exception:time.sleep(.5)
 raise RuntimeError('Dashboard not ready')
mode=sys.argv[1]
if mode=='prepare':
 assert not P.exists(),'Inspect previous release'
 sys.path.insert(0,str(B));from control_panel import Controller
 c=Controller()
 with c.connect() as db:
  settings=[dict(r) for r in db.execute('select model,revision,current_batch from settings')]
  services=[r[0] for r in db.execute('select service from jobs where batch in (select current_batch from settings)')]
 info={'status':'prepared','settings_before':settings,'jobs_before':{s:run('systemctl','show',s,'--property=MainPID,ActiveEnterTimestampMonotonic') for s in services},'original_image':run('docker','inspect','monitor-dashboard','--format','{{.Image}}'),'schedule_before':json.loads((B/'daily_plan.json').read_text())}
 backup=R/'backup';backup.mkdir()
 for name in NAMES:
  if (B/name).exists():shutil.copy2(B/name,backup/name)
  temp=B/(name+'.schedule-new');shutil.copy2(S/name,temp);temp.chmod(0o644);temp.replace(B/name)
 run('systemctl','restart','geo-monitor-status.service');run('systemctl','restart','geo-daily-control.service')
 save(info)
elif mode=='build':
 info=json.loads(P.read_text());assert info['status']=='prepared'
 rollback='monitor-dashboard:before-schedule-logos-20261016';run('docker','tag',info['original_image'],rollback)
 info['rollback']=rollback;save(info)
 (R/'Dockerfile').write_text(f'FROM {rollback}\nCOPY stage/capture-route.ts /dashboard/app/api/geo-capture/[...path]/route.ts\nCOPY stage/capture-gateway.test.mjs /dashboard/tests/capture-gateway.test.mjs\nWORKDIR /dashboard\nRUN node --experimental-strip-types --test tests/capture-gateway.test.mjs tests/creation-gateway.test.mjs\nRUN npm run build\n')
 subprocess.run(['docker','build','-t',IMAGE,str(R)],check=True,timeout=600)
 run('docker','run','-d','--name',PREVIEW,'--network','host',IMAGE,'npm','run','start','--','-H','0.0.0.0','-p','3001')
 ready(3001);info['status']='preview';save(info)
elif mode=='publish':
 info=json.loads(P.read_text());assert info['status']=='preview'
 assert json.loads((R/'qa-preview.json').read_text())['passed']
 assert run('docker','inspect','monitor-dashboard','--format','{{.Image}}')==info['original_image']
 command=['docker','compose','-p','local-server','-f','/opt/monitor/deploy/local-server/docker-compose.yml','up','-d','--no-deps','--no-build','--force-recreate','dashboard']
 run('docker','tag',IMAGE,'monitor-dashboard:local')
 try:run(*command);ready(3000)
 except Exception:
  run('docker','tag',info['rollback'],'monitor-dashboard:local');run(*command);raise
 target=Path('/opt/monitor/yuanbao_monitor/dashboard/app/api/geo-capture/[...path]/route.ts');shutil.copy2(target,R/'backup/capture-route.ts');shutil.copy2(S/'capture-route.ts',target)
 info['jobs_after']={s:run('systemctl','show',s,'--property=MainPID,ActiveEnterTimestampMonotonic') for s in info['jobs_before']}
 info['collectors_unchanged']=info['jobs_after']==info['jobs_before'];info['status']='published';save(info)
print(json.dumps({'mode':mode,'status':json.loads(P.read_text())['status']}))
