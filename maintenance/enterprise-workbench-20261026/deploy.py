import subprocess,json,pathlib,shutil,time,urllib.request,hashlib

def run(*a):return subprocess.check_output(a,text=True).strip()
def containers():return {x['Names']:x['ID'] for x in map(json.loads,run('docker','ps','--format','{{json .}}').splitlines()) if x['Names'] not in ['monitor-dashboard','monitor-dashboard-enterprise-preview']}
before=containers()
x=json.loads(run('docker','inspect','monitor-dashboard'))[0]
assert x['HostConfig']['NetworkMode']=='host' and not x['Mounts']
backup=pathlib.Path('/opt/monitor/maintenance/enterprise-workbench-20261026');backup.mkdir(parents=True,exist_ok=True)
config=backup/'container.json';config.write_text(json.dumps(x));config.chmod(0o600)
root=pathlib.Path('/opt/monitor/yuanbao_monitor/dashboard/app')
for name in ['Dashboard.tsx','layout.tsx']:shutil.copy2(root/name,backup/name)
run('docker','tag',x['Image'],'monitor-dashboard:before-enterprise-20261026')
run('docker','stop','monitor-dashboard')
run('docker','rename','monitor-dashboard','monitor-dashboard-before-enterprise-20261026')
try:
 args=['docker','run','-d','--name','monitor-dashboard','--network','host','--restart',x['HostConfig']['RestartPolicy']['Name']]
 for env in x['Config'].get('Env',[]):args+=['-e',env]
 for k,v in (x['Config'].get('Labels') or {}).items():args+=['--label',k+'='+v]
 args+=['monitor-dashboard:enterprise-20261026']+x['Config']['Cmd'];run(*args)
 for i in range(30):
  try:
   with urllib.request.urlopen('http://127.0.0.1:3000/',timeout=5) as r:assert r.status==200
   break
  except Exception:
   if i==29:raise
   time.sleep(1)
 run('/home/user/geo-editorial/venv/bin/python','/tmp/verify-enterprise.py','http://127.0.0.1:3000/')
 files=[]
 for name in ['Dashboard.tsx','layout.tsx']:
  target=root/name;shutil.copyfile('/tmp/enterprise-workbench/'+name,target);target.chmod(0o644)
  files.append({'source':'geo-monitor-deploy/dashboard-integration/app/'+name,'server':str(target),'sha256':hashlib.sha256(target.read_bytes()).hexdigest()})
 assert containers()==before,'Non-frontend containers changed'
 run('docker','tag','monitor-dashboard:enterprise-20261026','monitor-dashboard:local')
 result={'files':files,'other_containers_unchanged':True,'verified_title':'企业工作台'}
 (backup/'release.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False))
except Exception:
 subprocess.run(['docker','rm','-f','monitor-dashboard'],check=False)
 run('docker','rename','monitor-dashboard-before-enterprise-20261026','monitor-dashboard');run('docker','start','monitor-dashboard');raise
run('docker','rm','-f','monitor-dashboard-enterprise-preview')
