import hashlib,json,shutil,subprocess,time,urllib.request
from pathlib import Path
def run(*args):return subprocess.check_output(args,text=True).strip()
D=Path('/opt/monitor/maintenance/panel-cleanup-20261027');D.mkdir(parents=True,exist_ok=True)
source=Path('/opt/monitor/yuanbao_monitor/dashboard/app')
stage=Path('/tmp/panel-cleanup-20261027')
names=['Dashboard.tsx','PerformanceBoard.tsx','globals.css','WorkbenchLogo.tsx']
for name in names:
 if (source/name).exists():
  expected=stage/'before'/name
  assert expected.exists() and expected.read_bytes()==(source/name).read_bytes(), 'Source changed: '+name
  shutil.copy2(source/name,D/name)
x=json.loads(run('docker','inspect','monitor-dashboard'))[0]
assert not x['Mounts'] and x['HostConfig']['NetworkMode']=='host'
(D/'container.json').write_text(json.dumps(x));(D/'container.json').chmod(0o600)
(stage/'Dockerfile').write_text('FROM '+x['Image']+'\nCOPY app/ /dashboard/app/\nWORKDIR /dashboard\nRUN npm run build\n')
subprocess.run(['docker','build','-t','monitor-dashboard:clean-20261027',str(stage)],check=True)
def launch(name,port):
 args=['docker','run','-d','--name',name,'--network','host','--restart',x['HostConfig']['RestartPolicy']['Name']]
 for env in x['Config'].get('Env',[]):
  if not env.startswith('PORT='):args+=['-e',env]
 args+=['-e','PORT='+str(port)]
 for k,v in (x['Config'].get('Labels') or {}).items():args+=['--label',k+'='+v]
 cmd=[str(port) if arg=='3000' else arg for arg in x['Config']['Cmd']]
 return run(*args,'monitor-dashboard:clean-20261027',*cmd)
def ready(port):
 for _ in range(40):
  try:
   with urllib.request.urlopen('http://127.0.0.1:'+str(port)+'/',timeout=3) as response:html=response.read().decode()
   assert '企业工作台' in html
   assert 'workbench-logo' in html
   assert '企业概率监控' not in html and 'MODEL INTELLIGENCE' not in html
   return html
  except Exception:time.sleep(1)
 raise RuntimeError('Frontend health check failed')
launch('monitor-dashboard-clean-preview',3003);ready(3003)
run('docker','stop','monitor-dashboard');run('docker','rename','monitor-dashboard','monitor-dashboard-before-clean-20261027')
try:
 launch('monitor-dashboard',3000);ready(3000)
except Exception:
 subprocess.run(['docker','rm','-f','monitor-dashboard'])
 run('docker','rename','monitor-dashboard-before-clean-20261027','monitor-dashboard');run('docker','start','monitor-dashboard');raise
files=[]
for name in names:
 shutil.copy2(stage/'app'/name,source/name)
 files.append({'source':'geo-monitor-deploy/dashboard-integration/app/'+name,'server':str(source/name),'sha256':hashlib.sha256((source/name).read_bytes()).hexdigest()})
run('docker','tag','monitor-dashboard:clean-20261027','monitor-dashboard:local')
run('docker','rm','-f','monitor-dashboard-clean-preview')
(D/'release.json').write_text(json.dumps({'files':files},indent=2))
print('Frontend deployed and HTTP checks passed')
