from pathlib import Path
import hashlib,json,zipfile,os,shutil,sqlite3,subprocess,time,sys
import urllib.request
b=Path('/opt/monitor/geo-capture');native=Path('/home/user/redroid-doubao');w=native/'expansion-20261102';backup=w/'before-control-release';dbpath=b/'panel/control.sqlite'
def read(p):return json.loads(p.read_text())
def write(p,buf):
 t=p.with_name(p.name+'.expand-stage')
 t.write_bytes(buf);shutil.copystat(p,t);os.chown(t,p.stat().st_uid,p.stat().st_gid);t.replace(p)
def sha(buf):return hashlib.sha256(buf.replace(b'\r\n',b'\n')).hexdigest()
def svc(op):subprocess.run(['systemctl',op,'geo-daily-control','geo-monitor-status'],check=True,timeout=55)
def panel():return json.load(urllib.request.urlopen('http://127.0.0.1:8803/api/panel',timeout=35))
z=zipfile.ZipFile('/tmp/doubao-strict-lanes-20261102.zip');m=json.loads(z.read('manifest.json'))
updates={}
for n,v in m.items():
 p=Path(v['target']);assert sha(p.read_bytes())==v['base'] and sha(z.read(n))==v['sha'],n
 compile(z.read(n),str(p),'exec');updates[p]=z.read(n)
jobs=[]
for n in [3,4]:
 cfg=read(w/f'strict{n}.json');r=native/'batches'/cfg['batch'];h=read(r/'bridge_health.json');assert h['status']=='complete' and h['geo_processed']==h['captured']==1
 rec=read(next((r/'receipts').glob('*.json')));assert rec['source_device']==f'doubao-hpe14-account{n}' and rec['analysis']['source_capture_complete']
 jobs.append((cfg,r,f'geo-expand-strict{n}-20261102.service'))
before=panel();old=[x['id'] for x in before['models']];assert len(old)==7
backup=backup.with_name('before-control-release-2');backup.mkdir();svc('stop')
saved={};added=False
try:
 f=read(b/'fleet.json');plan=read(b/'daily_plan.json');policy=read(b/'native_memory_policy.json')
 assert old==['doubao1','doubao2','deepseek','wenxin_card','baidu_ai','yuanbao','deepseek2'] and len(f['collectors'])==7 and all(x['current']['batch'] in lane['health'] for x,lane in zip(before['models'],f['collectors']))
 with sqlite3.connect(dbpath) as db:
  with sqlite3.connect(backup/'control.sqlite') as dest:db.backup(dest)
  settings=db.execute("select value from settings where model='doubao2'").fetchone()[0];params=json.loads(settings)
  for cfg,r,unit in jobs:
   model=cfg['model'];assert model not in plan['models']
   db.execute('insert into jobs values(?,?,?,?,?,?,0)',(cfg['batch'],model,unit,str(r/'bridge_health.json'),json.dumps(cfg,ensure_ascii=False),r.stat().st_mtime))
   db.execute('insert into settings values(?,?,1,?)',(model,settings,cfg['batch']))
   plan['models'].append(model);plan['rounds'][model]=params['rounds']
   policy['models'].append(model)
   f['collectors'].append({'name':'豆包 '+model[-1],'service':unit,'health':str(r/'bridge_health.json'),'planned':1})
 added=True
 for name,obj in [('fleet.json',f),('daily_plan.json',plan),('native_memory_policy.json',policy)]:updates[b/name]=json.dumps(obj,ensure_ascii=False,indent=2).encode()
 for p,buf in updates.items():
  dest=backup/p.name;assert not dest.exists();shutil.copy2(p,dest);saved[p]=dest;write(p,buf)
 svc('start')
 for i in range(6):
  try:v=panel();break
  except OSError:time.sleep(1)
 assert [x['id'] for x in v['models']]==old+['doubao3','doubao4']
 for x in v['models'][-2:]:
  assert x['current']['processed']==1 and x['settings']==params
  print(x['name'],x['daily']['target'],x['current']['state'],x['readiness'].get('ready'))
 print('next',v['schedule']['next_run'])
except BaseException:
 svc('stop')
 for p,dest in saved.items():write(p,dest.read_bytes())
 if added:
  with sqlite3.connect(dbpath) as db:
   for cfg,r,unit in jobs:
    db.execute('delete from settings where model=? and current_batch=?',(cfg['model'],cfg['batch']));db.execute('delete from jobs where batch=?',(cfg['batch'],))
 svc('start');raise

