import hashlib,json,os,shutil,subprocess,time,urllib.request
from pathlib import Path
work=Path('/opt/monitor/maintenance/performance-copy-cleanup-20261031');work.mkdir(parents=True,exist_ok=True)
live=Path('/opt/monitor/yuanbao_monitor/dashboard/app/PerformanceCenter.tsx')
assert hashlib.sha256(live.read_bytes()).hexdigest()=='312b4ecd276aa4fc4392c58edacdf8e20c663c114766f3da85111cbd478eeba7','Production source changed'
source=Path('/tmp/performance-center-clean-20261031.tsx');text=source.read_text()
for phrase in ['每一分，都有依据','流量、预算、提及率与价值观，汇总为每个人的月度绩效进展。','卡片显示截至所选日的累计参考绩效。']:
 assert phrase not in text
assert '考核月份' in text and '绩效截止日期' in text and '员工绩效卡片' in text
stage=work/'stage';(stage/'app').mkdir(parents=True,exist_ok=True);shutil.copy2(source,stage/'app/PerformanceCenter.tsx')
shutil.copy2(live,work/'PerformanceCenter-before.tsx')
main=json.loads(subprocess.check_output(['docker','inspect','monitor-dashboard'],text=True))[0]
preview=json.loads(subprocess.check_output(['docker','inspect','monitor-dashboard-performance-preview'],text=True))[0]
assert not main['Mounts'] and main['HostConfig']['NetworkMode']=='host'
(stage/'Dockerfile').write_text('FROM '+main['Image']+'\nCOPY app/PerformanceCenter.tsx /dashboard/app/PerformanceCenter.tsx\nWORKDIR /dashboard\nRUN npm run build\n')
image='monitor-dashboard:performance-clean-20261031'
subprocess.run(['docker','build','-t',image,str(stage)],check=True,timeout=360)
op=urllib.request.build_opener(urllib.request.ProxyHandler({}))
def command(*args):return subprocess.run(args,check=True,capture_output=True,text=True,timeout=35).stdout.strip()
def launch(name,config):
 args=['docker','run','-d','--name',name,'--network','host']
 policy=config['HostConfig']['RestartPolicy']['Name']
 if policy:args+=['--restart',policy]
 for env in config['Config'].get('Env',[]):args+=['-e',env]
 for key,value in (config['Config'].get('Labels') or {}).items():args+=['--label',key+'='+value]
 return command(*args,image,*config['Config']['Cmd'])
def ready(port):
 for attempt in range(25):
  try:
   with op.open('http://127.0.0.1:'+str(port)+'/',timeout=5) as r:html=r.read().decode()
   assert '绩效考核' in html;return
  except Exception:
   if attempt==24:raise
   time.sleep(1)
switched=[]
try:
 for name,port,config in [('monitor-dashboard-performance-preview',3003,preview),('monitor-dashboard',3000,main)]:
  old=name+'-before-copy-clean-20261031'
  assert subprocess.run(['docker','inspect',old],capture_output=True).returncode!=0,'Existing rollback container'
  command('docker','stop','--time','15',name);command('docker','rename',name,old);switched.append((name,old))
  launch(name,config);ready(port)
  check="const fs=require('fs'); const s=fs.readFileSync('/dashboard/app/PerformanceCenter.tsx','utf8'); if(s.includes('每一分，都有依据')||s.includes('assessment-data-note'))process.exit(1); console.log('copy-cleanup-ok')"
  assert 'copy-cleanup-ok' in command('docker','exec',name,'node','-e',check)
 temp=live.with_suffix('.tsx.copy-clean.tmp');shutil.copy2(source,temp);temp.chmod(0o644);shutil.chown(temp,user='user',group='user');os.replace(temp,live)
except Exception:
 for name,old in reversed(switched):
  subprocess.run(['docker','rm','-f',name],capture_output=True,timeout=30)
  command('docker','rename',old,name);command('docker','start',name)
 shutil.copy2(work/'PerformanceCenter-before.tsx',live)
 raise
command('docker','tag',image,'monitor-dashboard:local')
release={'status':'live','public_url':'https://1any.top/geo_monitor/#performance','preview_updated':True,'removed':['标题口号','顶部介绍文字','顶部重复截止时间','卡片上方长提示'],'files':[{'source':'geo-monitor-deploy/dashboard-integration/app/PerformanceCenter.tsx','server':str(live),'sha256':hashlib.sha256(live.read_bytes()).hexdigest()}]}
(work/'release.json').write_text(json.dumps(release,ensure_ascii=False,indent=2));print('RELEASE',json.dumps(release,ensure_ascii=False),flush=True)
