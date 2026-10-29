import hashlib,json,os,shutil,sqlite3,subprocess,time
from pathlib import Path
D=Path('/opt/monitor/geo-capture/maintenance/20261024-doubao-stall');S=D/'candidate';L=Path('/home/user/redroid-doubao/geo-batch-code')
R=Path('/home/user/redroid-doubao/batches/geo-panel-doubao1-20261024-090002-8e65185c');service='geo-native@'+R.name+'.service'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def cmd(*args):return subprocess.check_output(args,text=True,stderr=subprocess.STDOUT,timeout=45).strip()
manifest=json.loads((D/'manifest.json').read_text());assert json.loads((D/'tests.json').read_text())['success']
assert not (D/'deployed.json').exists()
for n,v in manifest.items():assert sha(L/n)==v['before'] and sha(S/n)==v['after']
health=json.loads((R/'bridge_health.json').read_text());assert health['captured']==52 and health['progress']['ordinal']==53
assert not (R/'maintenance_pause.json').exists(),'Preserve operator pause'
backup=D/'before-deployment';backup.mkdir(exist_ok=True)
cmd('systemctl','stop',service)
try:
 with sqlite3.connect(R/'tasks.sqlite') as src,sqlite3.connect(backup/'tasks.sqlite') as dst:src.backup(dst)
 assert cmd('systemctl','show',service,'-p','ActiveState','--value')=='inactive'
 for n in manifest:shutil.copy2(L/n,backup/n)
 for n in manifest:
  tmp=L/(n+'.stall24.tmp');shutil.copy2(S/n,tmp);tmp.chmod(0o644);os.replace(tmp,L/n)
 result={'at':time.time(),'files':[{'server':str(L/n),'sha256':sha(L/n),'previous_sha256':v['before']} for n,v in manifest.items()],'service':service,'queue_reset':False,'app_restarted':False,'tests':json.loads((D/'tests.json').read_text())}
 (D/'deployed.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));print(json.dumps(result,ensure_ascii=False))
finally:cmd('systemctl','start',service)
