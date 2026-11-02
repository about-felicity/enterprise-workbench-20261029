import hashlib,json,os,shutil,subprocess,time,urllib.request
from pathlib import Path
work=Path('/opt/monitor/maintenance/performance-20261031');stage=work/'stage'
manifest=json.loads((stage/'manifest.json').read_text());backup=work/'before'
assert not backup.exists(),'Inspect existing deployment before repeating'
container_stage='/app/maintenance/performance-20261031/stage'
code="""import json,time
import doubao_dashboard_server as server
start=time.monotonic()
value=server._employee_assessment_payload({'month':['2026-10']})
assert len(value['people'])==5 and value['product_count']==15
assert all(len(p['current']['mention']['models'])==4 for p in value['people'])
print(json.dumps({'seconds':round(time.monotonic()-start,3),'people':[{'name':p['name'],'score':p['current']['score'],'traffic':p['current']['scores']['traffic'],'budget':p['current']['scores']['budget'],'mention':p['current']['scores']['mention']} for p in value['people']]},ensure_ascii=False))
"""
result=subprocess.run(['docker','exec','-w',container_stage+'/backend','-e','PYTHONPATH='+container_stage+'/backend:/app','monitor-dashboard-api','python','-B','-c',code],capture_output=True,text=True,timeout=90)
print('LIVE_DATA_TEST',result.stdout,result.stderr,flush=True)
assert result.returncode==0,'Live-data integration failed; production untouched'
backup.mkdir()
backend=[r for r in manifest['files'] if r['archive'].startswith('backend/')]
for row in manifest['files']:
 live=Path(row['server'])
 if row['before']:assert hashlib.sha256(live.read_bytes()).hexdigest()==row['before']
 else:assert not live.exists()
 if live.exists():
  dest=backup/row['archive'];dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(live,dest)
try:
 for row in backend:
  live=Path(row['server']);temp=live.with_suffix(live.suffix+'.performance.tmp');shutil.copy2(stage/row['archive'],temp);temp.chmod(0o644);os.replace(temp,live)
 subprocess.run(['docker','restart','monitor-dashboard-api'],check=True,capture_output=True,text=True,timeout=30)
 opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
 for attempt in range(25):
  try:
   with opener.open('http://127.0.0.1:8765/api/performance?month=2026-10',timeout=30) as response:value=json.load(response)
   assert value['product_count']==15 and len(value['people'])==5;break
  except Exception:
   if attempt==24:raise
   time.sleep(1)
except Exception:
 for row in backend:
  live=Path(row['server']);saved=backup/row['archive']
  if saved.exists():shutil.copy2(saved,live)
  else:live.unlink(missing_ok=True)
 subprocess.run(['docker','restart','monitor-dashboard-api'],check=True,capture_output=True,timeout=30)
 raise
x=json.loads((work/'container-before.json').read_text())
args=['docker','run','-d','--name','monitor-dashboard-performance-preview','--network','host']
for env in x['Config'].get('Env',[]):
 if not env.startswith('PORT='):args+=['-e',env]
args+=['-e','PORT=3003','monitor-dashboard:performance-20261031']
args += ['3003' if str(arg)=='3000' else str(arg) for arg in x['Config']['Cmd']]
subprocess.run(args,check=True,capture_output=True,text=True,timeout=30)
for attempt in range(25):
 try:
  with opener.open('http://127.0.0.1:3003/',timeout=5) as response:html=response.read().decode()
  assert '企业工作台' in html;break
 except Exception:
  if attempt==24:raise
  time.sleep(1)
(work/'preview.json').write_text(json.dumps({'status':'preview_ready','url':'http://192.168.31.106:3003/#performance','backend_files':backend,'at':time.time()},ensure_ascii=False,indent=2))
print('PREVIEW_READY http://192.168.31.106:3003/#performance',flush=True)
