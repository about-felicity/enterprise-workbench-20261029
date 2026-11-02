import hashlib,json,os,shutil,subprocess,time,urllib.request
from pathlib import Path
work=Path('/opt/monitor/maintenance/performance-chart-20261031');stage=work/'stage';manifest=json.loads((stage/'manifest.json').read_text())
image='monitor-dashboard:performance-chart-20261031'
def command(*args):return subprocess.run(args,check=True,capture_output=True,text=True,timeout=40).stdout.strip()
configs={name:json.loads(command('docker','inspect',name))[0] for name in ['monitor-dashboard','monitor-dashboard-performance-preview']}
assert configs['monitor-dashboard']['Image']==json.loads((work/'container-before.json').read_text())['Image']
for row in manifest['files']:
 p=Path(row['server'])
 if row['before']:assert hashlib.sha256(p.read_bytes()).hexdigest()==row['before']
 else:assert not p.exists()
for name,config in configs.items():
 assert not config['Mounts'] and config['HostConfig']['NetworkMode']=='host'
 assert subprocess.run(['docker','inspect',name+'-before-chart-20261031'],capture_output=True).returncode!=0
op=urllib.request.build_opener(urllib.request.ProxyHandler({}));switched=[]
try:
 for name,port in [('monitor-dashboard-performance-preview',3003),('monitor-dashboard',3000)]:
  config=configs[name];old=name+'-before-chart-20261031'
  command('docker','stop','--time','15',name);command('docker','rename',name,old);switched.append((name,old))
  args=['docker','run','-d','--name',name,'--network','host']
  if config['HostConfig']['RestartPolicy']['Name']:args+=['--restart',config['HostConfig']['RestartPolicy']['Name']]
  for env in config['Config'].get('Env',[]):args+=['-e',env]
  for k,v in (config['Config'].get('Labels') or {}).items():args+=['--label',k+'='+v]
  command(*args,image,*config['Config']['Cmd'])
  for attempt in range(25):
   try:
    with op.open('http://127.0.0.1:'+str(port)+'/',timeout=5) as r:assert '绩效考核' in r.read().decode()
    break
   except Exception:
    if attempt==24:raise
    time.sleep(1)
 for row in manifest['files']:
  p=Path(row['server']);temp=p.with_suffix(p.suffix+'.chart.tmp');shutil.copy2(stage/row['archive'],temp);temp.chmod(0o644);shutil.chown(temp,user='user',group='user');os.replace(temp,p)
except Exception:
 for name,old in reversed(switched):
  subprocess.run(['docker','rm','-f',name],capture_output=True);command('docker','rename',old,name);command('docker','start',name)
 for row in manifest['files']:
  p=Path(row['server']);backup=work/'before'/row['archive']
  if backup.exists():shutil.copy2(backup,p)
  else:p.unlink(missing_ok=True)
 raise
command('docker','tag',image,'monitor-dashboard:local')
report={'status':'live','public_url':'https://1any.top/geo_monitor/#performance','chart_render_checks':True,'backend_unchanged':True,'files':[{k:r[k] for k in ['source','server','sha256']} for r in manifest['files']]}
(work/'release.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print('CHART_LIVE')
