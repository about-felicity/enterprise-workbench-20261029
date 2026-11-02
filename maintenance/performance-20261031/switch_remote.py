"""Promote the already-built preview to the user's existing public workbench."""
import hashlib,json,os,shutil,subprocess,time,urllib.request
from pathlib import Path
work=Path('/opt/monitor/maintenance/performance-20261031');stage=work/'stage'
manifest=json.loads((stage/'manifest.json').read_text())
expected=json.loads((work/'container-before.json').read_text())
current=json.loads(subprocess.check_output(['docker','inspect','monitor-dashboard'],text=True))[0]
assert current['Image']==expected['Image'],'Production image changed since preview'
assert not current['Mounts'] and current['HostConfig']['NetworkMode']=='host'
assert json.loads((work/'verification.json').read_text())['status']=='preview_ready'
frontend=[r for r in manifest['files'] if r['archive'].startswith('app/')]
for row in frontend:
 path=Path(row['server'])
 if row['before']:assert hashlib.sha256(path.read_bytes()).hexdigest()==row['before'],'Production source changed: '+str(path)
 else:assert not path.exists()
 assert hashlib.sha256((stage/row['archive']).read_bytes()).hexdigest()==row['sha256']
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def get(url,timeout=40):
 start=time.monotonic()
 with op.open(url,timeout=timeout) as response:body=response.read();status=response.status;final_url=response.url
 return body,{'status':status,'seconds':round(time.monotonic()-start,3),'bytes':len(body),'final_url':final_url}
html,_=get('http://127.0.0.1:3003/',10);assert '绩效考核' in html.decode()
body,_=get('http://127.0.0.1:8765/api/performance?month=2026-10');assert len(json.loads(body)['people'])==5
old='monitor-dashboard-before-performance-20261031'
assert subprocess.run(['docker','inspect',old],capture_output=True).returncode!=0,'Existing rollback container must be reviewed'
def command(*args):return subprocess.run(args,check=True,capture_output=True,text=True,timeout=35).stdout.strip()
def launch():
 args=['docker','run','-d','--name','monitor-dashboard','--network','host','--restart',current['HostConfig']['RestartPolicy']['Name']]
 for env in current['Config'].get('Env',[]):args+=['-e',env]
 for key,value in (current['Config'].get('Labels') or {}).items():args+=['--label',key+'='+value]
 args+=['monitor-dashboard:performance-20261031',*current['Config']['Cmd']]
 return command(*args)
command('docker','stop','--time','15','monitor-dashboard');command('docker','rename','monitor-dashboard',old)
try:
 launch()
 for attempt in range(25):
  try:
   html,lan=get('http://127.0.0.1:3000/',5);assert '绩效考核' in html.decode();break
  except Exception:
   if attempt==24:raise
   time.sleep(1)
 public_html,public=get('https://1any.top/geo_monitor/',25)
 if '/geo_monitor/login' in public['final_url']:
  assert '员工登录' in public_html.decode(),'Unexpected public redirect'
  from urllib.error import HTTPError
  try:get('https://1any.top/geo_monitor/api/performance?month=2026-10',25)
  except HTTPError as error:
   assert error.code==401
   api={'status':401,'login_required':True,'unauthenticated_data_exposure':False}
  else:raise AssertionError('Public performance endpoint must preserve existing login guard')
  # Validate the exact API behind that guard through the existing local service.
  body,local_api=get('http://127.0.0.1:8765/api/performance?month=2026-10',40)
  payload=json.loads(body);assert len(payload['people'])==5 and payload['product_count']==15
  api['upstream_validation']=local_api
 else:
  assert '绩效考核' in public_html.decode(),'Public workbench still serves old frontend'
  body,api=get('https://1any.top/geo_monitor/api/performance?month=2026-10',45)
  payload=json.loads(body)
  assert len(payload['people'])==5 and payload['product_count']==15
 for row in frontend:
  dest=Path(row['server']);temp=dest.with_suffix(dest.suffix+'.performance.tmp');shutil.copy2(stage/row['archive'],temp);temp.chmod(0o644);shutil.chown(temp,user='user',group='user');os.replace(temp,dest)
except Exception:
 subprocess.run(['docker','rm','-f','monitor-dashboard'],capture_output=True,timeout=30)
 command('docker','rename',old,'monitor-dashboard');command('docker','start','monitor-dashboard')
 for row in frontend:
  dest=Path(row['server']);saved=work/'before'/row['archive']
  if saved.exists():shutil.copy2(saved,dest)
  else:dest.unlink(missing_ok=True)
 raise
command('docker','tag','monitor-dashboard:performance-20261031','monitor-dashboard:local')
report={'status':'live','public_url':'https://1any.top/geo_monitor/#performance','lan':lan,'public_html':public,'public_api':api,'people':5,'products':15,'rollback_container':old,'files':[{k:r[k] for k in ['source','server','sha256']} for r in manifest['files']]}
(work/'release.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print('LIVE',json.dumps(report,ensure_ascii=False),flush=True)
