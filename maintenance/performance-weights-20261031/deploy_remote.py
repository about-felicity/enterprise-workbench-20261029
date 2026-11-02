import hashlib,json,os,shutil,subprocess,time,urllib.request
from pathlib import Path
work=Path('/opt/monitor/maintenance/performance-weights-20261031');stage=work/'stage';manifest=json.loads((stage/'manifest.json').read_text())
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def command(*args):return subprocess.run(args,check=True,capture_output=True,text=True,timeout=40).stdout.strip()
def get(url,timeout=50):
 with op.open(url,timeout=timeout) as r:return r.read()
before=json.loads(get('http://127.0.0.1:8765/api/performance?month=2026-10&as_of=2026-10-31'))
(work/'performance-before.json').write_text(json.dumps(before,ensure_ascii=False))
configs={name:json.loads(command('docker','inspect',name))[0] for name in ['monitor-dashboard','monitor-dashboard-performance-preview']}
for row in manifest['files']:
 path=Path(row['server'])
 if row['before']:assert hashlib.sha256(path.read_bytes()).hexdigest()==row['before'],'Production source changed '+str(path)
 else:assert not path.exists(),'Unexpected existing file '+str(path)
 assert hashlib.sha256((stage/row['archive']).read_bytes()).hexdigest()==row['sha256']
for name,config in configs.items():
 assert not config['Mounts'] and config['HostConfig']['NetworkMode']=='host'
 assert subprocess.run(['docker','inspect',name+'-before-weights-20261031'],capture_output=True).returncode!=0
switched=[]
try:
 for row in manifest['files']:
  if not row['archive'].startswith('backend/'):continue
  dest=Path(row['server']);tmp=dest.with_suffix(dest.suffix+'.entry.tmp');shutil.copy2(stage/row['archive'],tmp);tmp.chmod(0o644);shutil.chown(tmp,user='user',group='user');os.replace(tmp,dest)
 command('docker','restart','monitor-dashboard-api')
 for attempt in range(30):
  try:
   after=json.loads(get('http://127.0.0.1:8765/api/performance?month=2026-10&as_of=2026-10-31',60));break
  except Exception:
   if attempt==29:raise
   time.sleep(1)
 for old,new in zip(before['people'],after['people']):
  assert old['name']==new['name']
  for field in ['traffic','budget']:
   assert old['current'][field]==new['current'][field],('Historical result changed',old['name'],field)
 for name,port in [('monitor-dashboard-performance-preview',3003),('monitor-dashboard',3000)]:
  config=configs[name];old=name+'-before-weights-20261031'
  command('docker','stop','--time','15',name);command('docker','rename',name,old);switched.append((name,old))
  args=['docker','run','-d','--name',name,'--network','host']
  if config['HostConfig']['RestartPolicy']['Name']:args+=['--restart',config['HostConfig']['RestartPolicy']['Name']]
  for env in config['Config'].get('Env',[]):args+=['-e',env]
  for k,v in (config['Config'].get('Labels') or {}).items():args+=['--label',k+'='+v]
  command(*args,'monitor-dashboard:performance-weights-20261031',*config['Config']['Cmd'])
  for attempt in range(25):
   try:
    assert '绩效考核' in get('http://127.0.0.1:'+str(port)+'/',10).decode();break
   except Exception:
    if attempt==24:raise
    time.sleep(1)
 for row in manifest['files']:
  if not row['archive'].startswith('app/'):continue
  dest=Path(row['server']);tmp=dest.with_suffix(dest.suffix+'.entry.tmp');shutil.copy2(stage/row['archive'],tmp);tmp.chmod(0o644);shutil.chown(tmp,user='user',group='user');os.replace(tmp,dest)
except Exception:
 for name,old in reversed(switched):
  subprocess.run(['docker','rm','-f',name],capture_output=True);command('docker','rename',old,name);command('docker','start',name)
 for row in manifest['files']:
  dest=Path(row['server']);backup=work/'before'/row['archive']
  if backup.exists():shutil.copy2(backup,dest)
  else:dest.unlink(missing_ok=True)
 command('docker','restart','monitor-dashboard-api')
 raise
command('docker','tag','monitor-dashboard:performance-weights-20261031','monitor-dashboard:local')
report={'status':'live','public_url':'https://1any.top/geo_monitor/#performance','historical_results_preserved':True,'tests':16,'files':[{k:r[k] for k in ['source','server','sha256']} for r in manifest['files']]}
(work/'release.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print('LIVE',json.dumps(report,ensure_ascii=False),flush=True)
