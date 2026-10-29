import json,os,pwd,shutil,sqlite3,subprocess,sys,time
from pathlib import Path
R=Path('/opt/monitor/geo-content/maintenance/20261016-creation-workflow');B=Path('/opt/monitor/geo-content');P=R/'release.json';S=R/'stage'
image='monitor-dashboard:creation-workflow-20261016'
def run(*args,timeout=90):return subprocess.check_output(args,text=True,timeout=timeout).strip()
def jobs():
 with sqlite3.connect('file:/opt/monitor/geo-capture/panel/control.sqlite?mode=ro',uri=True) as db:names=[r[0] for r in db.execute('select service from jobs where batch in (select current_batch from settings)')]
 names+=['geo-content-worker.service']
 return {n:run('systemctl','show',n,'--property=MainPID,ActiveEnterTimestampMonotonic') for n in names}
mode=sys.argv[1]
if mode=='build':
 assert not P.exists();info={'status':'building','image':image,'old_image':run('docker','inspect','monitor-dashboard','--format','{{.Image}}'),'jobs_before':jobs()}
 P.write_text(json.dumps(info))
 (R/'Dockerfile').write_text('FROM '+info['old_image']+'\nCOPY stage/creation-route.ts /dashboard/app/api/geo-creation/[...path]/route.ts\nCOPY stage/creation-gateway.test.mjs /dashboard/tests/creation-gateway.test.mjs\nWORKDIR /dashboard\nRUN node --experimental-strip-types --test tests/creation-gateway.test.mjs tests/capture-gateway.test.mjs\nRUN npm run build\n')
 subprocess.run(['docker','build','-t',image,str(R)],check=True,timeout=600)
 info['status']='built';P.write_text(json.dumps(info))
elif mode=='publish':
 info=json.loads(P.read_text());assert info['status']=='built' and json.loads((R/'qa-preview.json').read_text())['passed']
 assert not json.loads((B/'materials/health.json').read_text()).get('active_channels'),'Wait for existing private collection to idle'
 backup=R/'backup';backup.mkdir();shutil.copytree(B/'creation',backup/'creation')
 for f in (S/'creation').iterdir():
  if f.suffix in {'.py','.html','.md'}:shutil.copy2(f,B/'creation'/f.name)
 service='''[Unit]
Description=Creation studio daily product tasks and workflow orchestration
After=network-online.target geo-content-api.service
[Service]
Type=simple
WorkingDirectory=/opt/monitor/geo-content
Environment=PYTHONPATH=/opt/monitor/geo-content:/opt/monitor/geo-content/engine
Environment=PYTHONDONTWRITEBYTECODE=1
ExecStart=/home/user/geo-editorial/venv/bin/python -B -m creation.studio
Restart=on-failure
RestartSec=10
TimeoutStopSec=900
KillMode=mixed
MemoryMax=3000M
TasksMax=1024
UMask=0077
[Install]
WantedBy=multi-user.target
'''
 Path('/etc/systemd/system/geo-creation-studio.service').write_text(service)
 run('systemctl','daemon-reload');run('systemctl','enable','--now','geo-creation-studio.service')
 for _ in range(100):
  if (B/'studio/initialized.json').exists():break
  time.sleep(.1)
 assert (B/'studio/initialized.json').exists()
 run('systemctl','restart','geo-creation-materials.service');run('systemctl','restart','geo-content-api.service')
 rollback='monitor-dashboard:before-creation-workflow-20261016';run('docker','tag',info['old_image'],rollback);run('docker','tag',image,'monitor-dashboard:local')
 command=['docker','compose','-p','local-server','-f','/opt/monitor/deploy/local-server/docker-compose.yml','up','-d','--no-deps','--no-build','--force-recreate','dashboard']
 try:run(*command)
 except Exception:
  run('docker','tag',rollback,'monitor-dashboard:local');run(*command);raise
 route=Path('/opt/monitor/yuanbao_monitor/dashboard/app/api/geo-creation/[...path]/route.ts');shutil.copy2(route,backup/'creation-route.ts');shutil.copy2(S/'creation-route.ts',route)
 info.update(status='published',jobs_after=jobs(),rollback=rollback);info['collectors_and_creation_worker_unchanged']=info['jobs_before']==info['jobs_after'];P.write_text(json.dumps(info,indent=2));assert info['collectors_and_creation_worker_unchanged']
 print(json.dumps({'status':info['status'],'collectors_and_creation_worker_unchanged':True}))
