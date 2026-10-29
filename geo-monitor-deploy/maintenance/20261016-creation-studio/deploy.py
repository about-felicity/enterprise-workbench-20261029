import json,os,pwd,shutil,sqlite3,subprocess,sys,time
from datetime import datetime,timedelta
from pathlib import Path
from zoneinfo import ZoneInfo
B=Path('/opt/monitor/geo-content');R=B/'maintenance/20261016-creation-studio';S=R/'stage';P=R/'release.json';G=Path('/opt/monitor/geo-capture')
IMAGE='monitor-dashboard:creation-studio-20261016';PREVIEW='monitor-dashboard-creation-studio-preview'
def run(*a,timeout=60):return subprocess.check_output(a,text=True,timeout=timeout).strip()
def save(v):P.write_text(json.dumps(v,ensure_ascii=False,indent=2))
def jobs():
 with sqlite3.connect(G/'panel/control.sqlite') as db:services=[r[0] for r in db.execute('select service from jobs where batch in (select current_batch from settings)')]
 return {s:run('systemctl','show',s,'--property=MainPID,ActiveEnterTimestampMonotonic') for s in services}
mode=sys.argv[1]
if mode=='prepare':
 assert not P.exists(),'Inspect release before repeating'
 sys.path.insert(0,str(B));from creation import runtime
 assert all(j['control'].get('paused') or j['day'].get('status')=='complete' for j in runtime.status()['jobs']),'Wait for API work to reach idle'
 backup=R/'backup';backup.mkdir();shutil.copytree(B/'creation',backup/'creation')
 shutil.copy2(G/'capture_bridge.py',backup/'capture_bridge.py');shutil.copy2(G/'venv/lib/python3.10/site-packages/geo_source_cards/cli.py',backup/'cli.py')
 info={'status':'prepared','jobs_before':jobs(),'original_image':run('docker','inspect','monitor-dashboard','--format','{{.Image}}'),'at':time.time()}
 for file in (S/'creation').iterdir():
  if file.suffix not in {'.py','.html','.md'}:continue
  shutil.copy2(file,B/'creation'/file.name)
 shutil.copy2(S/'capture_bridge.py',G/'capture_bridge.py');shutil.copy2(S/'cli.py',G/'venv/lib/python3.10/site-packages/geo_source_cards/cli.py')
 owner=pwd.getpwnam('user');root=B/'materials';root.mkdir(mode=0o700);os.chown(root,owner.pw_uid,owner.pw_gid)
 questions=[q.strip() for q in Path('/home/user/geo-editorial/runtime-api/questions.txt').read_text('utf-8-sig').splitlines() if q.strip()]
 assert len(questions)==16 and len(set(questions))==16
 cfg={'enabled':True,'paused':False,'time':'01:00','timezone':'Asia/Shanghai','start_date':(datetime.now(ZoneInfo('Asia/Shanghai')).date()+timedelta(days=1)).isoformat(),'questions':questions,'rounds':1,'deepseek_interval':600,'search_interval':60}
 (root/'settings.json').write_text(json.dumps(cfg,ensure_ascii=False,indent=2));(root/'settings.json').chmod(0o600)
 lock=G/'deepseek_account.lock';lock.touch(exist_ok=True);lock.chmod(0o600);os.chown(lock,owner.pw_uid,owner.pw_gid)
 service='''[Unit]
Description=Creation-only private materials, idle GEO account windows
After=network-online.target docker.service
[Service]
Type=simple
WorkingDirectory=/opt/monitor/geo-content
Environment=PYTHONPATH=/opt/monitor/geo-content:/opt/monitor/geo-content/engine
Environment=PYTHONDONTWRITEBYTECODE=1
ExecStart=/home/user/geo-editorial/venv/bin/python -B -m creation.materials
Restart=on-failure
RestartSec=10
MemoryMax=2200M
TasksMax=512
TimeoutStopSec=180
KillMode=mixed
UMask=0077
[Install]
WantedBy=multi-user.target
'''
 Path('/etc/systemd/system/geo-creation-materials.service').write_text(service)
 run('systemctl','daemon-reload');run('systemctl','restart','geo-content-api.service');run('systemctl','restart','geo-content-worker.service');run('systemctl','enable','--now','geo-creation-materials.service')
 info['material_config']=cfg;save(info)
elif mode=='build':
 info=json.loads(P.read_text());assert info['status']=='prepared'
 rollback='monitor-dashboard:before-creation-studio-20261016';run('docker','tag',info['original_image'],rollback);info['rollback']=rollback;save(info)
 (R/'Dockerfile').write_text(f'FROM {rollback}\nCOPY stage/creation-route.ts /dashboard/app/api/geo-creation/[...path]/route.ts\nCOPY stage/creation-gateway.test.mjs /dashboard/tests/creation-gateway.test.mjs\nCOPY stage/CreationControl.tsx /dashboard/app/CreationControl.tsx\nCOPY stage/Dashboard.tsx /dashboard/app/Dashboard.tsx\nWORKDIR /dashboard\nRUN node --experimental-strip-types --test tests/creation-gateway.test.mjs tests/capture-gateway.test.mjs\nRUN npm run build\n')
 subprocess.run(['docker','build','-t',IMAGE,str(R)],check=True,timeout=600)
 run('docker','run','-d','--name',PREVIEW,'--network','host',IMAGE,'npm','run','start','--','-H','0.0.0.0','-p','3001')
 info['status']='preview';save(info)
elif mode=='publish':
 info=json.loads(P.read_text());assert info['status']=='preview';assert json.loads((R/'qa-preview.json').read_text())['passed']
 assert run('docker','inspect','monitor-dashboard','--format','{{.Image}}')==info['original_image']
 command=['docker','compose','-p','local-server','-f','/opt/monitor/deploy/local-server/docker-compose.yml','up','-d','--no-deps','--no-build','--force-recreate','dashboard']
 run('docker','tag',IMAGE,'monitor-dashboard:local')
 try:run(*command)
 except Exception:
  run('docker','tag',info['rollback'],'monitor-dashboard:local');run(*command);raise
 app=Path('/opt/monitor/yuanbao_monitor/dashboard/app')
 for source,target in [('creation-route.ts','api/geo-creation/[...path]/route.ts'),('CreationControl.tsx','CreationControl.tsx'),('Dashboard.tsx','Dashboard.tsx')]:
  shutil.copy2(app/target,R/'backup'/source);shutil.copy2(S/source,app/target)
 info['jobs_after']=jobs();info['collectors_unchanged']=info['jobs_before']==info['jobs_after'];info['status']='published';save(info)
print(json.dumps({'mode':mode,'status':json.loads(P.read_text())['status']}))
